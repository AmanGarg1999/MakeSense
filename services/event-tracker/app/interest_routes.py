"""LL-08 HTTP surface: interest signals, drift routing, quest offers, future
paths, learning-mode selection and project-together curricula.

Mounted on the event-tracker app at /api/interest/*. Endpoints that only need
pure logic (drift on a supplied signal list, mode selection, future paths,
project curriculum) work without a database; persistence is opt-in.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import interest_store
from app.content_citations import load_pack_index
from app.future_paths import propose_future_paths
from app.interest_config import load_config, load_kg
from app.interest_drift import route_interests
from app.learning_modes import (modes_for_skill, select_learning_mode,
                                derive_project_curriculum, verification_endpoint)

router = APIRouter(prefix="/api/interest", tags=["Interest Drift (LL-08)"])

_pool = None


async def get_db():
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


# ---------------------------------------------------------------------------
# signals + profile
# ---------------------------------------------------------------------------


class SignalIn(BaseModel):
    ts: Optional[Any] = None
    kind: str = "session"
    domain: str = Field(..., min_length=1)
    track_id: Optional[str] = None
    weight: Optional[float] = None
    source: Optional[str] = None
    meta: dict[str, Any] = {}


class SignalsIn(BaseModel):
    user_id: int
    signals: list[SignalIn]
    evaluate: bool = False
    goal_tracks: list[dict[str, Any]] = []


@router.post("/signals")
async def ingest_signals(req: SignalsIn):
    cfg = load_config()
    pool = await get_db()
    async with pool.acquire() as conn:
        n = await interest_store.store_signals(
            conn, req.user_id, [s.model_dump(exclude_none=True) for s in req.signals])
        out: dict[str, Any] = {"status": "stored", "count": n}
        if req.evaluate:
            sigs = await interest_store.load_signals(conn, req.user_id)
            report = route_interests(sigs, req.goal_tracks, cfg)
            await _persist_report(conn, req.user_id, report, cfg)
            out["drift"] = report.as_dict()
    return out


@router.get("/profile/{user_id}")
async def get_profile(user_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        sigs = await interest_store.load_signals(conn, user_id)
    report = route_interests(sigs, [])
    return {"profile": {d: i.as_dict() for d, i in report.profile.items()}}


# ---------------------------------------------------------------------------
# drift routing
# ---------------------------------------------------------------------------


class DriftIn(BaseModel):
    user_id: Optional[int] = None
    signals: list[SignalIn] = []
    goal_tracks: list[dict[str, Any]] = []
    active_track_domains: Optional[list[str]] = None
    persist: bool = False


@router.post("/drift/evaluate")
async def drift_evaluate(req: DriftIn):
    cfg = load_config()
    pool = None
    if req.user_id and (req.persist or not req.signals):
        pool = await get_db()
    async with (pool.acquire() if pool else _nullctx()) as conn:
        signals = [s.model_dump(exclude_none=True) for s in req.signals]
        if not signals and req.user_id:
            signals = await interest_store.load_signals(conn, req.user_id)
        report = route_interests(
            signals, req.goal_tracks, cfg,
            active_track_domains=set(req.active_track_domains) if req.active_track_domains else None)
        if req.persist and req.user_id:
            await _persist_report(conn, req.user_id, report, cfg)
    return report.as_dict()


@router.get("/quest-offers/{user_id}")
async def get_quest_offers(user_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        offers = await interest_store.list_open_quest_offers(conn, user_id)
    return {"offers": offers}


# ---------------------------------------------------------------------------
# future paths
# ---------------------------------------------------------------------------


class FuturePathsIn(BaseModel):
    user_id: Optional[int] = None
    tracks: list[dict[str, Any]]
    limit: Optional[int] = None
    persist: bool = False


@router.post("/future-paths")
async def future_paths(req: FuturePathsIn):
    cfg = load_config()
    suggestions = [s.as_dict() for s in propose_future_paths(req.tracks, load_kg(), cfg, req.limit)]
    if req.persist and req.user_id:
        pool = await get_db()
        async with pool.acquire() as conn:
            await interest_store.store_future_paths(conn, req.user_id, suggestions)
    return {"suggestions": suggestions}


# ---------------------------------------------------------------------------
# learning modes
# ---------------------------------------------------------------------------


class ModeIn(BaseModel):
    user_id: Optional[int] = None
    track: dict[str, Any]
    override: Optional[str] = None
    learner_level: Optional[str] = None
    persist: bool = False


@router.post("/learning-mode")
async def choose_learning_mode(req: ModeIn):
    cfg = load_config()
    sel = select_learning_mode(req.track, cfg, override=req.override,
                               learner_level=req.learner_level)
    endpoint = verification_endpoint(sel.mode, sel.skill_tag, cfg)
    if req.persist and req.user_id:
        pool = await get_db()
        async with pool.acquire() as conn:
            await interest_store.upsert_mode_selection(
                conn, req.user_id, req.track.get("track_id"), sel.as_dict(), endpoint["endpoint"])
    return {"selection": sel.as_dict(), "verification": endpoint}


@router.get("/learning-modes/{skill_tag}")
async def list_learning_modes(skill_tag: str):
    return {"skill_tag": skill_tag, "doors": modes_for_skill(skill_tag),
            "verification_endpoint": verification_endpoint("guided", skill_tag)["endpoint"]}


# ---------------------------------------------------------------------------
# project-together curriculum
# ---------------------------------------------------------------------------


class CurriculumIn(BaseModel):
    user_id: Optional[int] = None
    track_id: Optional[str] = None
    artifact: dict[str, Any]
    persist: bool = False


@router.post("/project-curriculum")
async def project_curriculum(req: CurriculumIn):
    cfg = load_config()
    plan = derive_project_curriculum(req.artifact, load_kg(), load_pack_index(), cfg)
    if req.persist and req.user_id:
        pool = await get_db()
        async with pool.acquire() as conn:
            await interest_store.store_project_curriculum(
                conn, req.user_id, req.track_id, req.artifact.get("skill_tag", ""),
                req.artifact, plan)
    return plan


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def _persist_report(conn, user_id: int, report, cfg) -> None:
    await interest_store.upsert_profile(
        conn, user_id, {d: i.as_dict() for d, i in report.profile.items()})
    await interest_store.store_drift_events(
        conn, user_id, [e.as_dict() for e in report.drift_events])
    if report.quest_offers:
        await interest_store.store_quest_offers(
            conn, user_id, [o.as_dict() for o in report.quest_offers], cfg)


class _nullctx:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False
