"""Stores: the persistent inventories the learning loop maintains.

Vision §3 lists the loop's stores; this module gives them ONE queryable
interface that the coach and dashboard read. Six stores:

  1. items         — knowledge DB item registry (exposes/extends the existing
                     central knowledge DB rows: source URL, license, quote
                     evidence, skill tags, bloom level)
  2. snapshots     — skill graph snapshots (goal-relative ladders per skill)
  3. mastery       — mastery ledger (append-only deltas per user/skill)
  4. verifications — LL-05 verification registry (evidence, rubric score,
                     expiry clock)
  5. recaps        — LL-06 recap schedule (Leitner/SM-2 due items per user)
  6. quests        — quest/batch state (side quests + batch progress)

Contract (non-negotiables encoded here):
  * APPEND-ONLY. There is no update or delete path; a "state change" is a new
    event row. Current state is derived by folding events in seq order.
  * PROVENANCE REQUIRED. Every append carries provenance (who/what produced
    the record: 'scraper:ncert', 'engine:batcher', 'user', 'coach', ...).
    Records without provenance are rejected.
  * Everything keys off the LL-02 schema vocabulary (track_id, skill_tag,
    goal_type, ladder_level) so LL-04/05/06 rows join cleanly.

Backend is SQLite (stdlib) for v1: a single file per store namespace, WAL
mode, safe for offline-first sync to merge in later. The interface is
deliberately backend-agnostic (plain dict rows) so a Postgres adapter can
satisfy the same protocol.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Store registry
# ---------------------------------------------------------------------------

# store name -> columns beyond (seq, id, ts, provenance) that get indexed.
# Values in these columns are stored as JSON in `payload`; the indexed subset
# is duplicated into typed columns for cheap filtering.
_STORE_SPECS: dict[str, dict[str, str]] = {
    "items": {
        "item_id": "TEXT",
        "source_url": "TEXT",
        "license": "TEXT",
        "skill_tag": "TEXT",
        "topic": "TEXT",
        "capture_date": "TEXT",
    },
    "snapshots": {
        "skill_tag": "TEXT",
        "goal_type": "TEXT",
        "ladder_version": "TEXT",
    },
    "mastery": {
        "user_id": "TEXT",
        "track_id": "TEXT",
        "skill_tag": "TEXT",
        "delta": "REAL",
        "cause": "TEXT",
    },
    "verifications": {
        "user_id": "TEXT",
        "track_id": "TEXT",
        "skill_tag": "TEXT",
        "outcome": "TEXT",
        "expires_at": "REAL",
    },
    "recaps": {
        "user_id": "TEXT",
        "track_id": "TEXT",
        "skill_tag": "TEXT",
        "due_at": "REAL",
        "bucket": "INTEGER",
        "status": "TEXT",
    },
    "quests": {
        "user_id": "TEXT",
        "track_id": "TEXT",
        "quest_id": "TEXT",
        "kind": "TEXT",
        "status": "TEXT",
        "expires_at": "REAL",
        "batch_id": "TEXT",
    },
}

STORE_NAMES: tuple[str, ...] = tuple(_STORE_SPECS)

_META_COLUMNS = "seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT, ts REAL, provenance TEXT NOT NULL"


class StoreError(ValueError):
    pass


class Stores:
    """Append-only, provenance-required event stores over a single SQLite file."""

    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    # -- schema --------------------------------------------------------------

    def _init_schema(self) -> None:
        for name, cols in _STORE_SPECS.items():
            col_defs = ", ".join(f"{c} {t}" for c, t in cols.items())
            self._conn.execute(f"CREATE TABLE IF NOT EXISTS store_{name} ({_META_COLUMNS}, {col_defs}, payload TEXT NOT NULL)")
            for c in cols:
                self._conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_{c} ON store_{name} ({c})")
        self._conn.commit()

    # -- write path (append only) ---------------------------------------------

    def append(
        self,
        store: str,
        record: dict[str, Any],
        provenance: Optional[str] = None,
        record_id: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> dict[str, Any]:
        """Append one immutable event. Returns the stored row as a dict.

        Raises StoreError on unknown store, missing provenance, or an
        attempt to pass a row id that already exists (append-only: ids are
        unique; change state by appending a new event, not by re-writing).
        """
        if store not in _STORE_SPECS:
            raise StoreError(f"unknown store '{store}' (have: {', '.join(STORE_NAMES)})")
        if not provenance or not isinstance(provenance, str):
            raise StoreError("every store append requires provenance (e.g. 'engine:batcher', 'scraper:ncert', 'user')")
        spec = _STORE_SPECS[store]
        rid = record_id or record.get("id") or uuid.uuid4().hex
        dup = self._conn.execute(
            f"SELECT 1 FROM store_{store} WHERE id = ? LIMIT 1", (rid,)
        ).fetchone()
        if dup:
            raise StoreError(f"{store}: id '{rid}' already exists — stores are append-only; express changes as new events")
        cols = {c: record.get(c) for c in spec}
        # coerce typed columns
        if store == "mastery":
            cols["delta"] = float(record.get("delta", 0.0))
        if store in ("verifications", "quests"):
            cols["expires_at"] = record.get("expires_at")
        if store == "recaps":
            cols["due_at"] = record.get("due_at")
            cols["bucket"] = record.get("bucket")
        payload = {k: v for k, v in record.items() if k not in spec}
        self._conn.execute(
            f"INSERT INTO store_{store} (id, ts, provenance, {', '.join(spec)}, payload) "
            f"VALUES (?, ?, ?, {', '.join('?' for _ in spec)}, ?)",
            (rid, ts if ts is not None else time.time(), provenance,
             *[_sqlite_safe(v) for v in cols.values()], json.dumps(payload, default=str)),
        )
        self._conn.commit()
        row = dict(record)
        row.update({"id": rid, "ts": ts if ts is not None else time.time(), "provenance": provenance})
        return row

    # -- read path ------------------------------------------------------------

    def count(self, store: str, **filters: Any) -> int:
        self._check(store)
        where, args = self._where(store, filters)
        sql = f"SELECT COUNT(*) AS n FROM store_{store}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        return self._conn.execute(sql, args).fetchone()["n"]

    def history(self, store: str, limit: int = 100, offset: int = 0, **filters: Any) -> list[dict[str, Any]]:
        """Events in append order (seq ascending) matching filters."""
        self._check(store)
        where, args = self._where(store, filters)
        sql = f"SELECT * FROM store_{store}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY seq ASC LIMIT ? OFFSET ?"
        rows = self._conn.execute(sql, (*args, limit, offset)).fetchall()
        return [self._hydrate(store, r) for r in rows]

    def latest(self, store: str, **filters: Any) -> Optional[dict[str, Any]]:
        self._check(store)
        where, args = self._where(store, filters)
        sql = f"SELECT * FROM store_{store}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY seq DESC LIMIT 1"
        row = self._conn.execute(sql, args).fetchone()
        return self._hydrate(store, row) if row else None

    def current_state(self, store: str, key_fields: Iterable[str], **filters: Any) -> dict[str, dict[str, Any]]:
        """Fold append-only events into 'current' state keyed by a tuple of
        fields (e.g. mastery current vector = last event per (user, skill))."""
        self._check(store)
        key_fields = list(key_fields)
        out: dict[str, dict[str, Any]] = {}
        for ev in self.history(store, limit=10**9, **filters):
            key = "|".join(str(ev.get(k)) for k in key_fields)
            out[key] = ev
        return out

    def summary(self) -> dict[str, int]:
        """Counts for all six stores — the dashboard/coach health view."""
        return {name: self.count(name) for name in STORE_NAMES}

    # -- internals --------------------------------------------------------------

    def _check(self, store: str) -> None:
        if store not in _STORE_SPECS:
            raise StoreError(f"unknown store '{store}' (have: {', '.join(STORE_NAMES)})")

    def _where(self, store: str, filters: dict[str, Any]) -> tuple[list[str], list[Any]]:
        spec = _STORE_SPECS[store]
        where: list[str] = []
        args: list[Any] = []
        for k, v in filters.items():
            if k in spec:
                if v is None:
                    where.append(f"{k} IS NULL")
                elif isinstance(v, (list, tuple, set)):
                    vals = list(v)
                    where.append(f"{k} IN ({', '.join('?' for _ in vals)})")
                    args.extend(_sqlite_safe(x) for x in vals)
                else:
                    where.append(f"{k} = ?")
                    args.append(_sqlite_safe(v))
            elif k == "provenance":
                where.append("provenance = ?")
                args.append(v)
            else:
                # non-indexed field: JSON-exact match on payload
                where.append("json_extract(payload, ?) = ?")
                args.extend((f"$.{k}", v))
        return where, args

    def _hydrate(self, store: str, row: sqlite3.Row) -> dict[str, Any]:
        out = {"id": row["id"], "ts": row["ts"], "provenance": row["provenance"], "seq": row["seq"]}
        for c in _STORE_SPECS[store]:
            out[c] = row[c]
        out.update(json.loads(row["payload"] or "{}"))
        return out

    def close(self) -> None:
        self._conn.close()


def _sqlite_safe(v: Any) -> Any:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v
