"""
Learning Pathways service (LL-09a)

Shared helpers for the pathways tables (server/migrations/009_learning_pathways.sql).
The Coach Engine (and any other server module) should read a user's active
pathway through :func:`get_active_pathway` rather than hand-rolling SQL, so the
canonical level vocabulary and payload shape stay in one place.

Canonical level enum (LL-09b/c/d depend on this — do not diverge):
    micro | certificate | undergrad | masters | phd | mba
"""

from typing import Optional, Dict, Any, List

import asyncpg

PATHWAY_LEVELS: List[str] = ["micro", "certificate", "undergrad", "masters", "phd", "mba"]
PATHWAY_STATUSES: List[str] = ["active", "paused", "completed", "archived"]

_LEVEL_CHECK = "level IN ('micro', 'certificate', 'undergrad', 'masters', 'phd', 'mba')"


async def get_active_pathway(pool: asyncpg.Pool, user_id: int) -> Optional[Dict[str, Any]]:
    """Return the user's active learning pathway with curriculum + level
    metadata, or None if they have no active pathway.

    If several pathways are active, the most recently started wins (deterministic).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT p.id, p.user_id, p.level, p.title, p.status,
                   p.started_at, p.target_completion, p.completed_at
            FROM learning_pathways p
            WHERE p.user_id = $1 AND p.status = 'active'
            ORDER BY p.started_at DESC, p.id
            LIMIT 1
            """,
            user_id,
        )
        if not row:
            return None
        pathway = dict(row)

        curriculum = await conn.fetch(
            """
            SELECT c.id, c.content_pack_id, c.sequence, c.required, c.credits
            FROM pathway_curriculum c
            WHERE c.pathway_id = $1
            ORDER BY c.sequence
            """,
            pathway["id"],
        )
        metadata = await conn.fetchrow(
            "SELECT * FROM level_metadata WHERE level = $1", pathway["level"]
        )

    pathway["curriculum"] = [dict(r) for r in curriculum]
    pathway["level_metadata"] = dict(metadata) if metadata else None
    return pathway


async def get_level_metadata(pool: asyncpg.Pool, level: str) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM level_metadata WHERE level = $1", level)
    return dict(row) if row else None
