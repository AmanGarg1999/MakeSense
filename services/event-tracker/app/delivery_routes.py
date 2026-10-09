"""LL-04 HTTP surface: delivery-mode decisions + session telemetry ingestion.

Mounted on the event-tracker app at /api/delivery/*. DB access goes through
get_db() which resolves an asyncpg pool lazily from DATABASE_URL; endpoints
that only need pure logic (classify/decide/bridges) work without a DB.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.delivery_engine import (classify_segment, resolve_mode,
                                 generate_bridge, mode_is_active)
from app import delivery_store
from app.dial_config import load_config

router = APIRouter(prefix="/api/delivery", tags=["Delivery Dial (LL-04)"])

_pool = None


async def get_db():
    """Lazy asyncpg pool; tests monkeypatch delivery_store functions directly."""
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL",
                             "postgresql://makesense:***@localhost:5432/makesense")
        try:
            import asyncpg
            _pool = await asyncpg.create_pool(dsn=dsn)
        except Exception as e:  # pragma: no cover - infra failure path
            raise HTTPException(status_code=503, detail=f"DB unavailable: {e}")
    return _pool


class SegmentIn(BaseModel):
    """Descriptor of a segment the player is about to show (decide) or just
    played (ingest). `delivery_mode` is what was actually served; when absent,
    the server resolves the recommended mode."""
    user_id: int
    track_id: Optional[str] = None
    skill_tag: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    segment_index: int = 0
    kind_hint: Optional[str] = None
    title: str = ""
    content_type: str = ""
    tags: list[str] = []
    prior_visits: int = 0
    energy: Optional[int] = None
    ladder_level: Optional[int] = None
    goal_type: str = "hobby"
    delivery_mode: Optional[str] = None
    decided_by: Optional[str] = None
    retrieval_outcome: Optional[str] = None
    dwell_seconds: int = 0
    paused_seconds: int = 0
    abandoned: bool = False


class SegmentDecisionOut(BaseModel):
    segment_kind: str
    mode: str
    mode_class: str
    decided_by: str
    reason: str


def _classify(seg: SegmentIn, cfg) -> str:
    return classify_segment(
        {"kind": seg.kind_hint, "title": seg.title,
         "content_type": seg.content_type, "tags": seg.tags},
        cfg, prior_visits=seg.prior_visits)


async def _escalation_for(seg: SegmentIn) -> Optional[dict]:
    if not (seg.track_id or os.environ.get("DATABASE_URL")):
        return None
    try:
        pool = await get_db()
        async with pool.acquire() as conn:
            return await delivery_store.active_escalation(conn, seg.skill_tag, seg.user_id)
    except HTTPException:
        return None


@router.post("/segments/decide", response_model=SegmentDecisionOut)
async def decide_segment(seg: SegmentIn):
    """Classify the segment and resolve the delivery mode (no writes)."""
    cfg = load_config()
    kind = _classify(seg, cfg)
    escalation = await _escalation_for(seg)
    track = {"goal_type": seg.goal_type, "current_ladder_rung": seg.ladder_level}
    decision = resolve_mode(track, kind, cfg,
                            active_escalation=escalation, energy=seg.energy)
    return SegmentDecisionOut(segment_kind=kind, mode=decision.mode,
                              mode_class=decision.mode_class,
                              decided_by=decision.decided_by,
                              reason=decision.reason)


@router.post("/segments")
async def record_segment(seg: SegmentIn):
    """Ingest one played segment (mode + engagement + retrieval outcome) and
    run the adaptive flip rule for its skill. Returns the decision + flip check."""
    cfg = load_config()
    kind = _classify(seg, cfg)
    escalation = await _escalation_for(seg)
    mode = seg.delivery_mode
    if not mode:
        track = {"goal_type": seg.goal_type}
        mode = resolve_mode(track, kind, cfg, active_escalation=escalation,
                            energy=seg.energy).mode
    mode_class = "active" if mode_is_active(mode, cfg) else "passive"
    row = {
        "user_id": seg.user_id, "track_id": seg.track_id, "skill_tag": seg.skill_tag,
        "session_id": seg.session_id, "segment_index": seg.segment_index,
        "segment_kind": kind, "delivery_mode": mode, "mode_class": mode_class,
        "decided_by": seg.decided_by or (escalation and "escalation" or "track_default"),
        "dwell_seconds": seg.dwell_seconds, "paused_seconds": seg.paused_seconds,
        "abandoned": seg.abandoned, "retrieval_outcome": seg.retrieval_outcome,
        "energy_level": seg.energy, "ladder_level": seg.ladder_level,
    }
    pool = await get_db()
    async with pool.acquire() as conn:
        await delivery_store.store_segment(conn, row)
        flip = await delivery_store.run_flip_check(conn, seg.skill_tag, seg.user_id, cfg)
    return {"status": "stored", "segment": row, "flip_check": flip}


class BridgeIn(BaseModel):
    track_state: dict[str, Any]
    mastery_vector: dict[str, Any]
    ladder: dict[str, Any]
    next_goal: Optional[str] = None
    log: bool = False
    user_id: Optional[int] = None
    track_id: Optional[str] = None


@router.post("/bridges")
async def make_bridge(req: BridgeIn):
    """Generate one companion bridge from actual ladder/mastery state."""
    cfg = load_config()
    bridge = generate_bridge(req.track_state, req.mastery_vector, req.ladder,
                             cfg, next_goal=req.next_goal)
    if bridge is None:
        return {"bridge": None, "note": "no state to speak from; companion stays silent"}
    if req.log and req.user_id:
        pool = await get_db()
        async with pool.acquire() as conn:
            await delivery_store.log_bridge(
                conn, req.user_id, req.track_id,
                req.track_state.get("skill_tag", ""), bridge,
                {"track_state": req.track_state,
                 "mastery_vector": req.mastery_vector,
                 "ladder_rungs": len(req.ladder.get("rungs", []))})
    return {"bridge": bridge}


@router.get("/escalations/{user_id}/{skill_tag}")
async def get_escalation(user_id: int, skill_tag: str):
    pool = await get_db()
    async with pool.acquire() as conn:
        esc = await delivery_store.active_escalation(conn, skill_tag, user_id)
    return {"escalation": esc}


class TelemetryIn(BaseModel):
    """Session-level telemetry summary → written as delivery_segments rows
    by the player via POST /segments; this endpoint batches them."""
    segments: list[SegmentIn]


@router.post("/telemetry/batch")
async def record_batch(req: TelemetryIn):
    results = []
    for seg in req.segments:
        results.append(await record_segment(seg))
    return {"count": len(results), "results": results}
