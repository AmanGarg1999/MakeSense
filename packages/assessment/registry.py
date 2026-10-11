"""Append-only verification registry (LL-05 §4).

One row per verification event: skill, level, evidence refs, rubric scores, verifier,
timestamps, expiry date, re-check linkage. Rows are NEVER updated or deleted —
current status of a rung is derived from its latest event (see expiry.py).
Feeds the LL-06 recap schedule.

Append-only is enforced twice:
  - at the storage layer (SQLite trigger rejects UPDATE/DELETE; Postgres migration
    server/migrations/008_verification_registry.sql mirrors it), and
  - in this module (no update/delete API is exposed; Registry attempts to mutate
    raise RegistryError).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Lifecycle states per LL-01 §7:
# unverified -> provisional -> verified -> reinforced -> (lapse) -> provisional -> re-verify
VERDICTS = {"verified", "provisional", "reinforced", "rejected"}
EVIDENCE_CLASSES = {"E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"}
# Escalation rungs per LL-01 §3.3 (logged, never a verdict on their own)
ESCALATION_RUNGS = {"artifact", "defense", "in_session", "provisional_flag"}


class RegistryError(RuntimeError):
    pass


def new_event_id() -> str:
    return "ver_" + uuid.uuid4().hex[:16]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS verification_registry (
    event_id        TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    skill_tag       TEXT NOT NULL,
    level_index     INTEGER NOT NULL,
    track_id        TEXT,
    verdict         TEXT NOT NULL CHECK (verdict IN ('verified','provisional','reinforced','rejected')),
    primary_evidence TEXT CHECK (primary_evidence IN ('E1','E2','E3','E4','E5','E6','E7','E8')),
    corroborating   TEXT NOT NULL DEFAULT '[]',   -- JSON list of evidence classes
    evidence_refs   TEXT NOT NULL DEFAULT '[]',   -- JSON list of artifact refs cited
    submission_id   TEXT,
    rubric_ref      TEXT,                          -- rubric_id@version
    prompt_version  TEXT,
    scoring         TEXT,                          -- JSON scoring_result (nullable)
    verifier        TEXT NOT NULL,                 -- JSON {kind, model?, human_id?}
    escalation_rung TEXT,                          -- which rung of the LL-01 §3.3 ladder was reached
    verified_at     TEXT NOT NULL,
    expires_at      TEXT,                          -- decay-clock due date (set by expiry.py)
    recheck_of      TEXT,                          -- event_id this re-verifies (null for first pass)
    supersedes      TEXT,                          -- event_id whose rung this extends/replaces
    notes           TEXT,
    recorded_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_registry_rung
    ON verification_registry (user_id, skill_tag, level_index, verified_at);

-- Append-only enforcement (SQLite side; Postgres migration mirrors this).
CREATE TRIGGER IF NOT EXISTS registry_no_update BEFORE UPDATE ON verification_registry
BEGIN
    SELECT RAISE(ABORT, 'verification_registry is append-only: UPDATE forbidden');
END;
CREATE TRIGGER IF NOT EXISTS registry_no_delete BEFORE DELETE ON verification_registry
BEGIN
    SELECT RAISE(ABORT, 'verification_registry is append-only: DELETE forbidden');
END;
"""


@dataclass
class RegistryEvent:
    event_id: str
    user_id: str
    skill_tag: str
    level_index: int
    verdict: str
    verified_at: str
    recorded_at: str
    track_id: Optional[str] = None
    primary_evidence: Optional[str] = None
    corroborating: Optional[list] = None
    evidence_refs: Optional[list] = None
    submission_id: Optional[str] = None
    rubric_ref: Optional[str] = None
    prompt_version: Optional[str] = None
    scoring: Optional[dict] = None
    verifier: Optional[dict] = None
    escalation_rung: Optional[str] = None
    expires_at: Optional[str] = None
    recheck_of: Optional[str] = None
    supersedes: Optional[str] = None
    notes: Optional[str] = None

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class VerificationRegistry:
    """Thin store over the append-only table."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def append(
        self,
        *,
        user_id: Any,
        skill_tag: str,
        level_index: int,
        verdict: str,
        verifier: dict,
        primary_evidence: Optional[str] = None,
        corroborating: Optional[list[str]] = None,
        evidence_refs: Optional[list[str]] = None,
        submission_id: Optional[str] = None,
        rubric_ref: Optional[str] = None,
        prompt_version: Optional[str] = None,
        scoring: Optional[dict] = None,
        escalation_rung: Optional[str] = None,
        verified_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        recheck_of: Optional[str] = None,
        supersedes: Optional[str] = None,
        track_id: Optional[str] = None,
        notes: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> RegistryEvent:
        if verdict not in VERDICTS:
            raise RegistryError(f"verdict must be one of {sorted(VERDICTS)}")
        if primary_evidence is not None and primary_evidence not in EVIDENCE_CLASSES:
            raise RegistryError(f"primary_evidence must be one of {sorted(EVIDENCE_CLASSES)}")
        if escalation_rung is not None and escalation_rung not in ESCALATION_RUNGS:
            raise RegistryError(f"escalation_rung must be one of {sorted(ESCALATION_RUNGS)}")
        if verifier.get("kind") not in {"model", "human", "hybrid", "deterministic"}:
            raise RegistryError("verifier.kind must be model|human|hybrid|deterministic")
        ev = RegistryEvent(
            event_id=event_id or new_event_id(),
            user_id=str(user_id), skill_tag=skill_tag, level_index=int(level_index),
            verdict=verdict, verified_at=verified_at or _utcnow(), recorded_at=_utcnow(),
            track_id=track_id, primary_evidence=primary_evidence,
            corroborating=corroborating or [], evidence_refs=evidence_refs or [],
            submission_id=submission_id, rubric_ref=rubric_ref,
            prompt_version=prompt_version, scoring=scoring, verifier=verifier,
            escalation_rung=escalation_rung, expires_at=expires_at,
            recheck_of=recheck_of, supersedes=supersedes, notes=notes,
        )
        self._conn.execute(
            """INSERT INTO verification_registry (
                 event_id, user_id, skill_tag, level_index, track_id, verdict,
                 primary_evidence, corroborating, evidence_refs, submission_id,
                 rubric_ref, prompt_version, scoring, verifier, escalation_rung,
                 verified_at, expires_at, recheck_of, supersedes, notes, recorded_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ev.event_id, ev.user_id, ev.skill_tag, ev.level_index, ev.track_id,
             ev.verdict, ev.primary_evidence, json.dumps(ev.corroborating),
             json.dumps(ev.evidence_refs), ev.submission_id, ev.rubric_ref,
             ev.prompt_version, json.dumps(ev.scoring) if ev.scoring else None,
             json.dumps(ev.verifier), ev.escalation_rung, ev.verified_at,
             ev.expires_at, ev.recheck_of, ev.supersedes, ev.notes, ev.recorded_at),
        )
        self._conn.commit()
        return ev

    def _row_to_event(self, row: sqlite3.Row) -> RegistryEvent:
        d = dict(row)
        d["corroborating"] = json.loads(d["corroborating"] or "[]")
        d["evidence_refs"] = json.loads(d["evidence_refs"] or "[]")
        d["scoring"] = json.loads(d["scoring"]) if d["scoring"] else None
        d["verifier"] = json.loads(d["verifier"])
        return RegistryEvent(**d)

    def latest(self, user_id: Any, skill_tag: str, level_index: int) -> Optional[RegistryEvent]:
        """Current verification event for a rung (None = unverified)."""
        cur = self._conn.execute(
            """SELECT * FROM verification_registry
               WHERE user_id=? AND skill_tag=? AND level_index=?
               ORDER BY verified_at DESC, recorded_at DESC LIMIT 1""",
            (str(user_id), skill_tag, int(level_index)),
        )
        row = cur.fetchone()
        return self._row_to_event(row) if row else None

    def history(self, user_id: Any, skill_tag: str,
                level_index: Optional[int] = None) -> list[RegistryEvent]:
        q = "SELECT * FROM verification_registry WHERE user_id=? AND skill_tag=?"
        args: list[Any] = [str(user_id), skill_tag]
        if level_index is not None:
            q += " AND level_index=?"
            args.append(int(level_index))
        q += " ORDER BY verified_at ASC, recorded_at ASC"
        return [self._row_to_event(r) for r in self._conn.execute(q, args)]

    def due_events(self, as_of: str) -> list[RegistryEvent]:
        """Latest event per rung whose expiry has passed as_of — raw feed for the
        expiry engine / LL-06 recap scheduler (which computes current/stale/expired)."""
        cur = self._conn.execute(
            """SELECT * FROM verification_registry v
               WHERE expires_at IS NOT NULL AND expires_at <= ?
                 AND event_id = (
                     SELECT event_id FROM verification_registry
                     WHERE user_id=v.user_id AND skill_tag=v.skill_tag AND level_index=v.level_index
                     ORDER BY verified_at DESC, recorded_at DESC LIMIT 1)
               ORDER BY expires_at ASC""",
            (as_of,),
        )
        return [self._row_to_event(r) for r in cur.fetchall()]

    def all_latest(self) -> list[RegistryEvent]:
        cur = self._conn.execute(
            """SELECT * FROM verification_registry v
               WHERE event_id = (
                     SELECT event_id FROM verification_registry
                     WHERE user_id=v.user_id AND skill_tag=v.skill_tag AND level_index=v.level_index
                     ORDER BY verified_at DESC, recorded_at DESC LIMIT 1)""")
        return [self._row_to_event(r) for r in cur.fetchall()]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM verification_registry").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
