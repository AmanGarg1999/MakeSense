"""
Learning Pathways API Routes (LL-09a)

CRUD for multi-level learning pathways + curriculum, level metadata, and
transcript entries. Built on server/migrations/009_learning_pathways.sql.

Canonical level vocabulary: micro | certificate | undergrad | masters | phd | mba
(kept in sync with level_metadata seed rows; server/pathway_service.py
PATHWAY_LEVELS is the Python source of truth).

Coach Engine note: import `get_active_pathway` from server.pathway_service
rather than calling HTTP against these routes.
"""

import logging
import uuid as uuid_mod
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from server.pathway_service import PATHWAY_LEVELS, get_active_pathway

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pathways", tags=["Learning Pathways"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


def get_user_id(request: Request) -> int:
    """Resolve the calling user from the X-User-ID header (app has no auth layer)."""
    return int(request.headers.get("X-User-ID", 1))


# ============================================================================
# Pydantic Models
# ============================================================================

class CurriculumItem(BaseModel):
    content_pack_id: str = Field(..., min_length=1, max_length=100)
    sequence: int = Field(..., ge=0)
    required: bool = True
    credits: float = Field(default=0.0, ge=0)


class PathwayCreateRequest(BaseModel):
    level: str = Field(..., pattern="^(" + "|".join(PATHWAY_LEVELS) + ")$")
    title: Optional[str] = Field(None, max_length=200)
    target_completion: Optional[date] = None
    curriculum: List[CurriculumItem] = Field(default_factory=list)


class PathwayUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, pattern="^(active|paused|completed|archived)$")
    target_completion: Optional[date] = None


class CurriculumReplaceRequest(BaseModel):
    items: List[CurriculumItem]


class TranscriptEntryRequest(BaseModel):
    content_pack_id: str = Field(..., min_length=1, max_length=100)
    mastery_score: float = Field(..., ge=0, le=1)
    completed_at: Optional[datetime] = None
    credential_issued: bool = False
    credential_type: Optional[str] = Field(None, max_length=50)


# ============================================================================
# Row serialisation helpers
# ============================================================================

def _parse_pathway_id(pathway_id: str) -> str:
    """Validate the UUID early so bad ids 422 instead of hitting the DB."""
    try:
        return str(uuid_mod.UUID(pathway_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")


def _pathway_dict(row: asyncpg.Record) -> Dict[str, Any]:
    d = dict(row)
    if d.get("id") is not None:
        d["id"] = str(d["id"])
    return d


async def _load_pathway(conn, pathway_id: str, user_id: int) -> Dict[str, Any]:
    pathway_id = _parse_pathway_id(pathway_id)
    row = await conn.fetchrow(
        """
        SELECT id, user_id, level, title, status, started_at,
               target_completion, completed_at, created_at, updated_at
        FROM learning_pathways WHERE id = $1::uuid AND user_id = $2
        """,
        pathway_id, user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pathway not found")
    return _pathway_dict(row)


async def _load_curriculum(conn, pathway_id: str) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, content_pack_id, sequence, required, credits::float8 AS credits
        FROM pathway_curriculum WHERE pathway_id = $1::uuid ORDER BY sequence
        """,
        pathway_id,
    )
    return [dict(r) for r in rows]


# ============================================================================
# Pathway CRUD
# ============================================================================

@router.post("", response_model=Dict[str, Any])
async def create_pathway(
    req: PathwayCreateRequest,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Create a pathway (optionally with an ordered curriculum in one call)."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO learning_pathways (user_id, level, title, target_completion)
                VALUES ($1, $2, $3, $4)
                RETURNING id, user_id, level, title, status, started_at,
                          target_completion, completed_at, created_at, updated_at
                """,
                user_id, req.level, req.title, req.target_completion,
            )
            pathway = _pathway_dict(row)
            for i, item in enumerate(req.curriculum):
                seq = item.sequence if item.sequence is not None else i
                await conn.execute(
                    """
                    INSERT INTO pathway_curriculum
                        (pathway_id, content_pack_id, sequence, required, credits)
                    VALUES ($1::uuid, $2, $3, $4, $5)
                    """,
                    pathway["id"], item.content_pack_id, seq, item.required, item.credits,
                )
    pathway["curriculum"] = await _load_curriculum_from_pool(pool, pathway["id"])
    return pathway


async def _load_curriculum_from_pool(pool, pathway_id):
    async with pool.acquire() as conn:
        return await _load_curriculum(conn, pathway_id)


@router.get("", response_model=List[Dict[str, Any]])
async def list_pathways(
    level: Optional[str] = Query(None, pattern="^(" + "|".join(PATHWAY_LEVELS) + ")$"),
    status: Optional[str] = Query(None, pattern="^(active|paused|completed|archived)$"),
    all_users: bool = Query(False, description="Include other users' pathways (level directory view)"),
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """List pathways, filterable by level. Scoped to the caller unless all_users."""
    conds, args = [], []
    if not all_users:
        args.append(user_id)
        conds.append(f"user_id = ${len(args)}")
    if level:
        args.append(level)
        conds.append(f"level = ${len(args)}")
    if status:
        args.append(status)
        conds.append(f"status = ${len(args)}")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, user_id, level, title, status, started_at,
                   target_completion, completed_at
            FROM learning_pathways {where}
            ORDER BY started_at DESC
            """,
            *args,
        )
    return [_pathway_dict(r) for r in rows]


@router.get("/active", response_model=Optional[Dict[str, Any]])
async def active_pathway(
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """The caller's current active pathway with curriculum + level metadata
    (same shape the Coach Engine gets from server.pathway_service.get_active_pathway)."""
    return await get_active_pathway(pool, user_id)


@router.get("/levels", response_model=List[Dict[str, Any]])
async def list_level_metadata(pool: asyncpg.Pool = Depends(get_db)):
    """Canonical level vocabulary with program characteristics (LL-09b/c/d contract)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM level_metadata ORDER BY typical_duration_weeks")
    return [dict(r) for r in rows]


@router.get("/{pathway_id}", response_model=Dict[str, Any])
async def get_pathway(
    pathway_id: str,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    try:
        async with pool.acquire() as conn:
            pathway = await _load_pathway(conn, pathway_id, user_id)
            pathway["curriculum"] = await _load_curriculum(conn, pathway_id)
            meta = await conn.fetchrow("SELECT * FROM level_metadata WHERE level = $1", pathway["level"])
    except asyncpg.exceptions.InvalidTextRepresentationError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")
    pathway["level_metadata"] = dict(meta) if meta else None
    return pathway


@router.patch("/{pathway_id}", response_model=Dict[str, Any])
async def update_pathway(
    pathway_id: str,
    req: PathwayUpdateRequest,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    sets, args = [], []
    if req.title is not None:
        args.append(req.title); sets.append(f"title = ${len(args)}")
    if req.status is not None:
        args.append(req.status); sets.append(f"status = ${len(args)}")
        if req.status == "completed":
            sets.append("completed_at = NOW()")
    if req.target_completion is not None:
        args.append(req.target_completion); sets.append(f"target_completion = ${len(args)}")
    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")
    pathway_id = _parse_pathway_id(pathway_id)
    sets.append("updated_at = NOW()")
    args.append(pathway_id); args.append(user_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                f"""
                UPDATE learning_pathways
                SET {', '.join(sets)}
                WHERE id = ${len(args) - 1}::uuid AND user_id = ${len(args)}
                RETURNING id, user_id, level, title, status, started_at,
                          target_completion, completed_at, created_at, updated_at
                """,
                *args,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Pathway not found")
            pathway = _pathway_dict(row)
            pathway["curriculum"] = await _load_curriculum(conn, pathway_id)
    return pathway


@router.delete("/{pathway_id}", response_model=Dict[str, Any])
async def delete_pathway(
    pathway_id: str,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    pathway_id = _parse_pathway_id(pathway_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM learning_pathways WHERE id = $1::uuid AND user_id = $2 RETURNING id",
            pathway_id, user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pathway not found")
    return {"deleted": True, "id": str(row["id"])}


# ============================================================================
# Curriculum
# ============================================================================

@router.put("/{pathway_id}/curriculum", response_model=Dict[str, Any])
async def replace_curriculum(
    pathway_id: str,
    req: CurriculumReplaceRequest,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Replace the whole curriculum list for a pathway (atomic)."""
    try:
        async with pool.acquire() as conn:
            await _load_pathway(conn, pathway_id, user_id)  # 404 if missing/not mine
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM pathway_curriculum WHERE pathway_id = $1::uuid", pathway_id)
                for item in req.items:
                    await conn.execute(
                        """
                        INSERT INTO pathway_curriculum
                            (pathway_id, content_pack_id, sequence, required, credits)
                        VALUES ($1::uuid, $2, $3, $4, $5)
                        """,
                        pathway_id, item.content_pack_id, item.sequence, item.required, item.credits,
                    )
                curriculum = await _load_curriculum(conn, pathway_id)
    except asyncpg.exceptions.InvalidTextRepresentationError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")
    return {"pathway_id": pathway_id, "curriculum": curriculum}


# ============================================================================
# Transcript
# ============================================================================

@router.get("/{pathway_id}/transcript", response_model=List[Dict[str, Any]])
async def get_transcript(
    pathway_id: str,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    async with pool.acquire() as conn:
        await _load_pathway(conn, pathway_id, user_id)
        rows = await conn.fetch(
            """
            SELECT content_pack_id, mastery_score, completed_at,
                   credential_issued, credential_type, recorded_at
            FROM user_transcript WHERE pathway_id = $1::uuid ORDER BY completed_at NULLS LAST
            """,
            pathway_id,
        )
    return [dict(r) for r in rows]


@router.post("/{pathway_id}/transcript", response_model=Dict[str, Any])
async def record_transcript(
    pathway_id: str,
    req: TranscriptEntryRequest,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Upsert a transcript entry for one content pack in this pathway."""
    if req.credential_issued and not req.credential_type:
        raise HTTPException(status_code=422, detail="credential_type required when credential_issued")
    try:
        async with pool.acquire() as conn:
            await _load_pathway(conn, pathway_id, user_id)
            row = await conn.fetchrow(
                """
                INSERT INTO user_transcript
                    (user_id, pathway_id, content_pack_id, mastery_score,
                     completed_at, credential_issued, credential_type)
                VALUES ($1, $2::uuid, $3, $4,
                        COALESCE($5::timestamptz, NOW()), $6, $7)
                ON CONFLICT (user_id, pathway_id, content_pack_id)
                DO UPDATE SET mastery_score = EXCLUDED.mastery_score,
                              completed_at = EXCLUDED.completed_at,
                              credential_issued = EXCLUDED.credential_issued,
                              credential_type = EXCLUDED.credential_type,
                              recorded_at = NOW()
                RETURNING content_pack_id, mastery_score, completed_at,
                          credential_issued, credential_type
                """,
                user_id, pathway_id, req.content_pack_id, req.mastery_score,
                req.completed_at, req.credential_issued, req.credential_type,
            )
        return dict(row)
    except asyncpg.exceptions.InvalidTextRepresentationError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")
