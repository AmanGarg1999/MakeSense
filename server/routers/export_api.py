"""
Transcript export API routes (LL-09d)

Builds the canonical transcript document (ll09d.transcript — same shape the
frontend's buildTranscriptDocument produces from the LL-09a API payloads) and
renders it as JSON or PDF.

Endpoints:
  GET /api/export/transcript/<pathway_id>.json   -> transcript document
  GET /api/export/transcript/<pathway_id>.pdf    -> transcript PDF (A4)
  GET /api/export/transcript/active.(json|pdf)   -> caller's active pathway

Level gating is on the document, not the route: micro badge pathways export
too (credits/GPA render as nulls); the UI only offers the button for degree
pathways per LL-09a level_metadata.
"""

import logging
import uuid
from typing import Any, Dict

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ll09d.transcript import build_transcript_document
from ll09d.pdf import render_transcript_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["Transcript Export (LL-09d)"])


async def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


def get_user_id(request: Request) -> int:
    return int(request.headers.get("X-User-ID", 1))


async def _load_doc(pool, pathway_id: str, user_id: int) -> Dict[str, Any]:
    """Pathway + curriculum + transcript + level row -> canonical document."""
    try:
        uuid.UUID(str(pathway_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, level, title, status, started_at,
                   target_completion, completed_at
            FROM learning_pathways WHERE id = $1::uuid AND user_id = $2
            """,
            pathway_id, user_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Pathway not found")
        pathway = dict(row)
        pathway["id"] = str(pathway["id"])
        pathway["curriculum"] = [dict(r) for r in await conn.fetch(
            """
            SELECT content_pack_id, sequence, required, credits::float8 AS credits
            FROM pathway_curriculum WHERE pathway_id = $1::uuid ORDER BY sequence
            """,
            pathway_id,
        )]
        entries = await conn.fetch(
            """
            SELECT content_pack_id, mastery_score, completed_at,
                   credential_issued, credential_type
            FROM user_transcript WHERE pathway_id = $1::uuid
            ORDER BY completed_at NULLS LAST
            """,
            pathway_id,
        )
        meta = await conn.fetchrow(
            "SELECT * FROM level_metadata WHERE level = $1", pathway["level"])
    return build_transcript_document(
        pathway,
        transcript=[dict(e) for e in entries],
        level_row=dict(meta) if meta else None,
    )


async def _active_pathway_id(pool, user_id: int):
    from server.pathway_service import get_active_pathway
    pathway = await get_active_pathway(pool, user_id)
    if not pathway:
        raise HTTPException(status_code=404, detail="No active pathway")
    return str(pathway["id"])


@router.get("/transcript/active.json")
async def export_active_json(
    pool: asyncpg.Pool = Depends(get_db), user_id: int = Depends(get_user_id),
):
    return JSONResponse(await _load_doc(pool, await _active_pathway_id(pool, user_id), user_id))


@router.get("/transcript/active.pdf")
async def export_active_pdf(
    pool: asyncpg.Pool = Depends(get_db), user_id: int = Depends(get_user_id),
):
    doc = await _load_doc(pool, await _active_pathway_id(pool, user_id), user_id)
    return _pdf_response(doc)


@router.get("/transcript/{pathway_id}.json")
async def export_json(
    pathway_id: str,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    try:
        doc = await _load_doc(pool, pathway_id, user_id)
    except asyncpg.exceptions.InvalidTextRepresentationError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")
    return JSONResponse(doc)


@router.get("/transcript/{pathway_id}.pdf")
async def export_pdf(
    pathway_id: str,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: int = Depends(get_user_id),
):
    try:
        doc = await _load_doc(pool, pathway_id, user_id)
    except asyncpg.exceptions.InvalidTextRepresentationError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")
    return _pdf_response(doc)


def _pdf_response(doc):
    try:
        data = render_transcript_pdf(doc)
    except Exception as exc:  # pragma: no cover — renderer bugs surface as 500
        logger.exception("transcript PDF render failed")
        raise HTTPException(status_code=500, detail=f"PDF render failed: {exc}")
    level = doc["pathway"]["level"]
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="transcript-{level}-{doc["pathway"]["id"]}.pdf"'},
    )
