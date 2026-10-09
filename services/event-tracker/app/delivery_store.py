"""Persistence for LL-04 delivery telemetry + flip decisions.

Uses an asyncpg pool (server database or the event-tracker's optional DB).
Every function is dependency-injected with a conn/pool that has fetch/fetchrow/
execute so the module is testable without a live database.
Schema: server/migrations/007_delivery_telemetry.sql (keys off LL-02
skill_tracks/skill_ladders).
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.delivery_engine import evaluate_flip_rule
from app.dial_config import load_config


async def store_segment(conn, seg: dict[str, Any]) -> None:
    """Insert one delivery_segments row."""
    await conn.execute("""
        INSERT INTO delivery_segments (
            user_id, track_id, skill_tag, session_id, segment_index,
            segment_kind, delivery_mode, mode_class, decided_by,
            dwell_seconds, paused_seconds, abandoned, retrieval_outcome,
            energy_level, ladder_level
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
        )
    """,
        seg["user_id"], seg.get("track_id"), seg["skill_tag"], seg["session_id"],
        seg.get("segment_index", 0), seg["segment_kind"], seg["delivery_mode"],
        seg["mode_class"], seg.get("decided_by", "track_default"),
        int(seg.get("dwell_seconds", 0)), int(seg.get("paused_seconds", 0)),
        bool(seg.get("abandoned", False)), seg.get("retrieval_outcome"),
        seg.get("energy_level"), seg.get("ladder_level"),
    )


async def recent_skill_segments(conn, skill_tag: str, user_id: int,
                                cfg: Optional[dict] = None) -> list[dict[str, Any]]:
    cfg = cfg or load_config()
    lookback = cfg["flip_rule"]["lookback_sessions"]
    rows = await conn.fetch("""
        SELECT id, session_id, mode_class, delivery_mode, abandoned,
               retrieval_outcome, created_at
        FROM delivery_segments
        WHERE skill_tag = $1 AND user_id = $2
        ORDER BY created_at DESC
        LIMIT 500
    """, skill_tag, user_id)
    out = [dict(r) for r in rows]
    # bound by lookback window of distinct sessions (most recent N sessions)
    seen: list[str] = []
    trimmed = []
    for r in out:
        if r["session_id"] not in seen:
            if len(seen) >= lookback:
                break
            seen.append(r["session_id"])
        trimmed.append(r)
    return trimmed


async def active_escalation(conn, skill_tag: str, user_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow("""
        SELECT id, reason, evidence, escalate_for_sessions, sessions_consumed
        FROM delivery_mode_escalations
        WHERE skill_tag = $1 AND user_id = $2 AND active = TRUE
        ORDER BY started_at DESC LIMIT 1
    """, skill_tag, user_id)
    if not row:
        return None
    d = dict(row)
    d["evidence"] = d["evidence"] if isinstance(d["evidence"], dict) else json.loads(d["evidence"] or "{}")
    return d


async def consume_escalation_session(conn, escalation_id: int, cfg: Optional[dict] = None) -> bool:
    """Called once per session that ran under an escalation. Returns True if the
    escalation has now expired (holds for flip_rule.escalation_sessions)."""
    cfg = cfg or load_config()
    n = cfg["flip_rule"]["escalation_sessions"]
    row = await conn.fetchrow(
        "UPDATE delivery_mode_escalations SET sessions_consumed = sessions_consumed + 1 "
        "WHERE id = $1 RETURNING sessions_consumed, escalate_for_sessions",
        escalation_id)
    if not row:
        return False
    if row["sessions_consumed"] >= row["escalate_for_sessions"]:
        await conn.execute(
            "UPDATE delivery_mode_escalations SET active = FALSE, expired_at = NOW() WHERE id = $1",
            escalation_id)
        return True
    return False


async def run_flip_check(conn, skill_tag: str, user_id: int,
                         cfg: Optional[dict] = None) -> dict[str, Any]:
    """Evaluate the adaptive flip rule from stored telemetry and, when it fires,
    log the decision + evidence into delivery_mode_escalations.

    Returns the FlipDecision as a dict (should_flip, reason, evidence).
    """
    cfg = cfg or load_config()
    segments = await recent_skill_segments(conn, skill_tag, user_id, cfg)
    decision = evaluate_flip_rule(skill_tag, segments, cfg)

    existing = await active_escalation(conn, skill_tag, user_id)

    if decision.should_flip:
        # don't stack a second escalation on top of an active one; refresh evidence only
        if existing:
            await conn.execute(
                "UPDATE delivery_mode_escalations SET evidence = $1 WHERE id = $2",
                json.dumps({**decision.evidence, "refreshed_from": existing["id"]}),
                existing["id"])
        else:
            track = await conn.fetchrow(
                "SELECT id FROM skill_tracks WHERE skill_tag = $1 AND user_id = $2 "
                "AND status = 'active' ORDER BY last_activity_at DESC LIMIT 1",
                skill_tag, user_id)
            await conn.execute("""
                INSERT INTO delivery_mode_escalations
                    (user_id, track_id, skill_tag, reason, evidence, escalate_for_sessions)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, user_id,
                track["id"] if track else None,
                skill_tag, decision.reason,
                json.dumps(decision.evidence),
                cfg["flip_rule"]["escalation_sessions"])
    return {
        "skill_tag": decision.skill_tag,
        "should_flip": decision.should_flip,
        "reason": decision.reason,
        "evidence": decision.evidence,
    }


async def log_bridge(conn, user_id: int, track_id: Optional[str], skill_tag: str,
                     bridge: dict[str, str], source_state: dict[str, Any]) -> None:
    await conn.execute("""
        INSERT INTO companion_bridges (user_id, track_id, skill_tag, bridge_text, motivation, source_state)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, user_id, track_id, skill_tag, bridge["text"], bridge["motivation"],
        json.dumps(source_state, default=str))
