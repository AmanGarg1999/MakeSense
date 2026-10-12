"""Content Pack API Routes (mk-017 extension, LL-09c)

Cloud API for level-aware content packs on top of the LL-09a pathway tables:

  GET  /api/packs?level=undergrad&prereq_satisfied=true
      List packs serving a canonical level; optionally filter to packs whose
      prerequisites the calling user has already satisfied (user_transcript
      mastery >= prerequisite min_mastery).

  POST /api/packs                       (register/assemble a pack manifest)
      Validates the manifest through the mk-016 packager (schema + level
      metadata + license compliance) and checks the prerequisite graph against
      the registry (cycle rejection) before storing.

  POST /api/pathways/{id}/curriculum    (bulk assign packs with sequence)
      Replaces the pathway's curriculum from a list of pack ids; validates
      level compatibility and prerequisite acyclicity across the assigned set.

Manifest storage: server/migrations/010_content_pack_registry.sql.
"""

import json
import logging
import uuid as uuid_mod
from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from server.pathway_service import PATHWAY_LEVELS
from packages.packager import (
    PackValidationError,
    validate_manifest,
    validate_prereq_graph,
    check_pack_licenses,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Content Packs"])


async def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


def get_user_id(request: Request) -> int:
    return int(request.headers.get("X-User-ID", 1))


class CurriculumAssignRequest(BaseModel):
    """Bulk curriculum assignment. sequence omitted => order given (0-based)."""
    items: List[Dict[str, Any]] = Field(..., min_items=1)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _pack_rows_to_manifests(rows) -> List[dict]:
    return [json.loads(r["manifest"]) for r in rows]


async def _registry(conn) -> List[dict]:
    rows = await conn.fetch(
        "SELECT pack_id, version, manifest FROM content_packs ORDER BY pack_id, version DESC")
    return _pack_rows_to_manifests(rows)


async def _user_mastery(conn, user_id: int) -> Dict[str, float]:
    """Best mastery ever recorded for the user per pack (any pathway)."""
    rows = await conn.fetch(
        """
        SELECT content_pack_id, MAX(mastery_score) AS m
        FROM user_transcript WHERE user_id = $1
        GROUP BY content_pack_id
        """,
        user_id,
    )
    return {r["content_pack_id"]: float(r["m"]) for r in rows}


def _prereqs_satisfied(manifest: dict, mastery: Dict[str, float]) -> bool:
    for p in manifest.get("prerequisites", []):
        if mastery.get(p["pack_id"], 0.0) < float(p.get("min_mastery", 0.0)):
            return False
    return True


def _pack_summary(manifest: dict) -> Dict[str, Any]:
    return {
        "pack_id": manifest["pack_id"],
        "version": manifest["version"],
        "title": manifest["title"],
        "schema_version": str(manifest.get("schema_version", "0")),
        "level_target": manifest.get("level_target", ["micro", "certificate"]),
        "prerequisites": manifest.get("prerequisites", []),
        "credit_value": manifest.get("credit_value", 0),
        "estimated_hours": manifest.get("estimated_hours"),
        "assessment_spec": manifest.get("assessment_spec"),
        "learning_outcomes": manifest.get("learning_outcomes", []),
    }


# ---------------------------------------------------------------------------
# GET /api/packs
# ---------------------------------------------------------------------------

@router.get("/packs")
async def list_packs(
    request: Request,
    level: Optional[str] = Query(None, pattern="^(" + "|".join(PATHWAY_LEVELS) + ")$"),
    prereq_satisfied: bool = Query(False),
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """List registered packs, filtered by pathway level and (optionally) by
    whether the calling user has satisfied every prerequisite."""
    async with pool.acquire() as conn:
        manifests = await _registry(conn)
        mastery = await _user_mastery(conn, user_id) if prereq_satisfied else {}

    out = []
    for m in manifests:
        levels = m.get("level_target", ["micro", "certificate"])
        if level and level not in levels:
            continue
        satisfied = _prereqs_satisfied(m, mastery)
        if prereq_satisfied and not satisfied:
            continue
        summary = _pack_summary(m)
        summary["prereqs_satisfied_for_user"] = satisfied
        out.append(summary)
    out.sort(key=lambda d: d["pack_id"])
    return {"count": len(out), "packs": out}


# ---------------------------------------------------------------------------
# POST /api/packs — packager validation gate (mk-016)
# ---------------------------------------------------------------------------

@router.post("/packs")
async def register_pack(
    manifest: Dict[str, Any],
    pool: asyncpg.Pool = Depends(get_db),
):
    """Assemble-time validation + store. Existing packs WITHOUT level fields
    still load (back-compat): treated as level_target=[micro, certificate]."""
    try:
        pm = validate_manifest(manifest)
    except PackValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    problems = check_pack_licenses(manifest)
    if problems:
        raise HTTPException(status_code=422,
                            detail="license compliance failed: " + "; ".join(problems))

    async with pool.acquire() as conn:
        # cycle check across registry + candidate
        registry = await _registry(conn)
        same_id = [m for m in registry if m["pack_id"] != pm.pack_id]
        graphs = [validate_manifest(m) for m in same_id] + [pm]
        cycles = validate_prereq_graph(graphs)
        if cycles:
            raise HTTPException(
                status_code=422,
                detail="prerequisite cycle detected: " + " -> ".join(cycles[0]))

        level_target = pm.level_target
        row = await conn.fetchrow(
            """
            INSERT INTO content_packs
                (pack_id, version, title, schema_version, manifest,
                 level_target, credit_value, estimated_hours)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::text[], $7, $8)
            ON CONFLICT (pack_id, version) DO UPDATE SET
                title = EXCLUDED.title, schema_version = EXCLUDED.schema_version,
                manifest = EXCLUDED.manifest, level_target = EXCLUDED.level_target,
                credit_value = EXCLUDED.credit_value,
                estimated_hours = EXCLUDED.estimated_hours
            RETURNING pack_id, version
            """,
            pm.pack_id, pm.version, pm.title, pm.schema_version,
            json.dumps(manifest), level_target, pm.credit_value, pm.estimated_hours,
        )
    return {"registered": dict(row), "level_target": level_target}


# ---------------------------------------------------------------------------
# POST /api/pathways/{id}/curriculum — bulk assign with sequence
# ---------------------------------------------------------------------------

@router.post("/pathways/{pathway_id}/curriculum")
async def assign_curriculum(
    pathway_id: str,
    req: CurriculumAssignRequest,
    user_id: int = Depends(get_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Bulk-assign packs (with sequence) to a pathway, validating against the
    pack registry: unknown pack -> 422; level mismatch -> 422; prerequisite
    cycles inside the assigned set -> 422."""
    try:
        pid = str(uuid_mod.UUID(pathway_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="pathway_id must be a UUID")

    packs = []
    for i, item in enumerate(req.items):
        packs.append({
            "content_pack_id": item.get("content_pack_id", ""),
            "sequence": int(item.get("sequence", i)),
            "required": bool(item.get("required", True)),
            "credits": float(item.get("credits", 0) or 0),
        })
    seqs = sorted(p["sequence"] for p in packs)
    if seqs != list(range(len(seqs))):
        raise HTTPException(status_code=422,
                            detail="sequence must be 0-based with no gaps or duplicates")

    async with pool.acquire() as conn:
        owner = await conn.fetchrow(
            "SELECT id, level FROM learning_pathways WHERE id = $1::uuid AND user_id = $2",
            pid, user_id)
        if not owner:
            raise HTTPException(status_code=404, detail="Pathway not found")

        registry = {m["pack_id"]: m for m in await _registry(conn)}
        assigned_manifests = []
        for p in packs:
            m = registry.get(p["content_pack_id"])
            if m is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"unknown content pack: {p['content_pack_id']!r} (register via POST /api/packs)")
            levels = m.get("level_target", ["micro", "certificate"])
            if owner["level"] not in levels:
                raise HTTPException(
                    status_code=422,
                    detail=f"pack {m['pack_id']} serves {levels}, not pathway level "
                           f"{owner['level']!r}")
            if not p["credits"]:
                p["credits"] = float(m.get("credit_value", 0) or 0)
            assigned_manifests.append(validate_manifest(m))

        cycles = validate_prereq_graph(assigned_manifests)
        if cycles:
            raise HTTPException(status_code=422,
                                detail="prerequisite cycle in curriculum: " + " -> ".join(cycles[0]))

        async with conn.transaction():
            await conn.execute("DELETE FROM pathway_curriculum WHERE pathway_id = $1::uuid", pid)
            for p in sorted(packs, key=lambda x: x["sequence"]):
                await conn.execute(
                    """
                    INSERT INTO pathway_curriculum
                        (pathway_id, content_pack_id, sequence, required, credits)
                    VALUES ($1::uuid, $2, $3, $4, $5)
                    """,
                    pid, p["content_pack_id"], p["sequence"], p["required"], p["credits"])
            rows = await conn.fetch(
                """
                SELECT content_pack_id, sequence, required, credits::float8 AS credits
                FROM pathway_curriculum WHERE pathway_id = $1::uuid ORDER BY sequence
                """, pid)

    return {"pathway_id": pid, "curriculum": [dict(r) for r in rows]}
