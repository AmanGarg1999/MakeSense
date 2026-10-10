"""Persistence for LL-08 interest signals, profile, drift, offers, future
paths, learning-mode selections and project curricula.

Dependency-injected with an asyncpg-style conn/pool (fetch/fetchrow/execute),
so every function is testable without a live database. Schema:
server/migrations/008_interest_drift_and_paths.sql.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.interest_config import load_config


async def store_signals(conn, user_id: int, signals: list[dict[str, Any]]) -> int:
    n = 0
    for s in signals:
        await conn.execute("""
            INSERT INTO interest_signals (user_id, ts, kind, domain, track_id, weight, source, meta)
            VALUES ($1, COALESCE($2, NOW()), $3, $4, $5, $6, $7, $8)
        """, user_id, s.get("ts"), s.get("kind", "session"), s["domain"],
            s.get("track_id"), float(s.get("weight", 1.0)),
            s.get("source"), json.dumps(s.get("meta", {})))
        n += 1
    return n


async def load_signals(conn, user_id: int, since_ts: Optional[Any] = None,
                       limit: int = 2000) -> list[dict[str, Any]]:
    if since_ts is not None:
        rows = await conn.fetch("""
            SELECT id, EXTRACT(EPOCH FROM ts) AS ts, kind, domain, track_id, weight, source, meta
            FROM interest_signals WHERE user_id = $1 AND ts >= $2
            ORDER BY ts DESC LIMIT $3
        """, user_id, since_ts, limit)
    else:
        rows = await conn.fetch("""
            SELECT id, EXTRACT(EPOCH FROM ts) AS ts, kind, domain, track_id, weight, source, meta
            FROM interest_signals WHERE user_id = $1
            ORDER BY ts DESC LIMIT $2
        """, user_id, limit)
    out = []
    for r in rows:
        d = dict(r)
        d["ts"] = float(d["ts"])
        if isinstance(d.get("meta"), str):
            d["meta"] = json.loads(d["meta"] or "{}")
        out.append(d)
    return out


async def upsert_profile(conn, user_id: int, profile: dict[str, Any]) -> None:
    for dom, i in profile.items():
        await conn.execute("""
            INSERT INTO interest_profile
                (user_id, domain, weight, share, confidence, signal_count, sources, latest_ts, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, to_timestamp($8), NOW())
            ON CONFLICT (user_id, domain) DO UPDATE SET
                weight = EXCLUDED.weight, share = EXCLUDED.share,
                confidence = EXCLUDED.confidence, signal_count = EXCLUDED.signal_count,
                sources = EXCLUDED.sources, latest_ts = EXCLUDED.latest_ts,
                updated_at = NOW()
        """, user_id, dom, i["weight"], i["share"], i["confidence"],
            i["signal_count"], json.dumps(i["sources"]), i.get("latest_ts"))


async def store_drift_events(conn, user_id: int, events: list[dict[str, Any]]) -> None:
    for e in events:
        await conn.execute("""
            INSERT INTO drift_events
                (user_id, domain, direction, baseline_share, recent_share, delta,
                 confidence, is_goal_track, evidence)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, user_id, e["domain"], e["direction"], e["baseline_share"],
            e["recent_share"], e["delta"], e["confidence"], e["is_goal_track"],
            json.dumps(e.get("evidence", {})))


async def store_quest_offers(conn, user_id: int, offers: list[dict[str, Any]],
                             cfg: Optional[dict] = None) -> None:
    cfg = cfg or load_config()
    days = cfg["drift"]["offer_cooldown_days"]
    for o in offers:
        await conn.execute("""
            INSERT INTO quest_offers
                (user_id, domain, offer_text, confidence, delta, evidence, cooldown_until)
            VALUES ($1, $2, $3, $4, $5, $6, NOW() + ($7 || ' days')::interval)
        """, user_id, o["domain"], o["offer_text"], o["confidence"], o["delta"],
            json.dumps(o.get("evidence", {})), str(days))


async def list_open_quest_offers(conn, user_id: int) -> list[dict[str, Any]]:
    rows = await conn.fetch("""
        SELECT id, domain, offer_text, confidence, delta, evidence, status, created_at, cooldown_until
        FROM quest_offers WHERE user_id = $1 AND status = 'open'
        ORDER BY created_at DESC
    """, user_id)
    out = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("evidence"), str):
            d["evidence"] = json.loads(d["evidence"] or "{}")
        out.append(d)
    return out


async def store_future_paths(conn, user_id: int, suggestions: list[dict[str, Any]]) -> None:
    for s in suggestions:
        await conn.execute("""
            INSERT INTO future_path_suggestions
                (user_id, kind, from_track_id, suggested_skill, suggested_level,
                 title, why_now, priority, evidence)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, user_id, s["kind"], s.get("from_track_id"), s["suggested_skill"],
            s.get("suggested_level"), s["title"], s["why_now"], s["priority"],
            json.dumps(s.get("evidence", {})))


async def upsert_mode_selection(conn, user_id: int, track_id: Optional[str],
                                sel: dict[str, Any], endpoint: str) -> None:
    await conn.execute("""
        INSERT INTO learning_mode_selection
            (user_id, track_id, skill_tag, mode, decided_by, reason, verification_endpoint, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        ON CONFLICT (user_id, track_id) DO UPDATE SET
            mode = EXCLUDED.mode, decided_by = EXCLUDED.decided_by,
            reason = EXCLUDED.reason, verification_endpoint = EXCLUDED.verification_endpoint,
            updated_at = NOW()
    """, user_id, track_id, sel["skill_tag"], sel["mode"], sel["decided_by"],
        sel["reason"], endpoint)


async def store_project_curriculum(conn, user_id: int, track_id: Optional[str],
                                   skill_tag: str, artifact: dict[str, Any],
                                   plan: dict[str, Any]) -> None:
    await conn.execute("""
        INSERT INTO project_curricula (user_id, track_id, skill_tag, artifact, plan)
        VALUES ($1, $2, $3, $4, $5)
    """, user_id, track_id, skill_tag, json.dumps(artifact), json.dumps(plan))
