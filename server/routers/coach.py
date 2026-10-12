"""
Coach Engine pedagogy API Routes (LL-09b)

Exposes the level-aware Coach Engine over HTTP and resolves a user's level
from their active pathway (LL-09a's get_active_pathway). Thin surface: the
behavior lives in ll09b/coach_engine.py; this router just loads the user's
active pathway, sets the level, and runs the requested state through
coach_action().

Endpoints:
  GET  /api/coach/levels                 — canonical levels + pedagogy summary
  POST /api/coach/action                 — coach action for explicit user + state
  GET  /api/coach/challenge-params       — additive LL-07 challenge hints for user
"""

import logging
from typing import Any, Dict, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from server.pathway_service import PATHWAY_LEVELS, get_active_pathway
from ll09b.coach_engine import CoachEngine
from ll09b.level_config import LEVEL_CONFIGS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coach", tags=["Coach Engine (LL-09b)"])


async def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


def get_user_id(request: Request) -> int:
    return int(request.headers.get("X-User-ID", 1))


class CoachActionRequest(BaseModel):
    state: Dict[str, Any] = Field(default_factory=dict)
    level: Optional[str] = Field(
        None,
        pattern="^(" + "|".join(PATHWAY_LEVELS) + ")$",
        description="Override level; default: user's active pathway level",
    )


async def _engine_for(pool, user_id: int, level_override: Optional[str]) -> CoachEngine:
    """Build an engine set to the user's effective level.

    Level resolution order: explicit override -> active pathway level -> micro.
    A user with no active pathway still gets a working coach (micro default),
    matching the on-device cold-start behavior.
    """
    level = level_override
    if level is None:
        pathway = await get_active_pathway(pool, user_id)
        level = pathway["level"] if pathway else "micro"
    engine = CoachEngine(pool=pool, user_id=user_id)
    await engine.set_learning_level_async(level)
    return engine


@router.get("/levels")
async def list_levels():
    """Canonical levels with the pedagogy summary the Coach Engine applies."""
    return [
        {
            "level": lvl,
            "label": cfg["label"],
            "cycle": cfg["cycle"],
            "feedback": cfg["feedback"],
            "long_term_tracking": cfg["long_term_tracking"],
            "radar_granularity": cfg["radar_granularity"],
            "recap_multiplier": cfg["recap_multiplier"],
            "instruments": cfg["instruments"],
        }
        for lvl, cfg in LEVEL_CONFIGS.items()
    ]


@router.post("/action")
async def coach_action(
    req: CoachActionRequest,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Run the level-aware coach for the calling user's active pathway."""
    engine = await _engine_for(pool, user_id, req.level)
    action = engine.coach_action(req.state)
    payload = action.to_dict()
    payload["challenge_params"] = engine.challenge_request(req.state)
    return payload


@router.get("/challenge-params")
async def challenge_params(
    pool: asyncpg.Pool = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    """Additive hint surface for the LL-07 adaptive challenge generator."""
    engine = await _engine_for(pool, user_id, None)
    return engine.challenge_request({})
