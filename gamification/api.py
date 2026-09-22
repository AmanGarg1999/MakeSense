"""
Gamification API Routes

FastAPI routes for gamification system:
- User gamification profile
- Leaderboards (periodic)
- User points history
- User skills
"""

import json
from typing import Optional, Dict, List, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
import asyncpg
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["gamification"])


def _parse_metadata(val: Any) -> dict:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Get database pool from app state."""
    return request.app.state.db_pool


# ============================================================================
# Pydantic Models
# ============================================================================

class UserProfile(BaseModel):
    level: int
    total_xp: int
    xp_to_next_level: int
    engagement_points_breakdown: Dict[str, int]


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    level_name: str
    current_level: int
    points: int  # points earned in the period


class EngagementPointEntry(BaseModel):
    id: int
    points: int
    source_type: str
    source_id: Optional[int]
    source_metadata: dict
    description: Optional[str]
    created_at: str


class UserSkillRating(BaseModel):
    skill_tag: str
    proficiency_score: int
    evidence_count: int
    confidence: float
    last_updated: str


# ============================================================================
# Helper Functions
# ============================================================================

async def get_current_user_id(request: Request) -> int:
    """
    Extract user ID from request.
    In production, this would come from JWT token, session, etc.
    """
    # Placeholder - replace with actual auth
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")


# ============================================================================
# Routes
# ============================================================================

@router.get("/users/{id}/profile", response_model=UserProfile)
async def get_user_profile(
    id: int,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get user gamification profile."""
    async with pool.acquire() as conn:
        # Get user basic info
        user = await conn.fetchrow(
            "SELECT current_level, total_xp FROM users WHERE id = $1",
            id
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_level = user['current_level']
        total_xp = user['total_xp']

        # Get level info to get xp_to_next_level and level_name
        level_info = await conn.fetchrow(
            "SELECT xp_to_next, level_name FROM user_levels WHERE level_id = $1",
            current_level
        )
        if not level_info:
            # Fallback if level not found (should not happen)
            xp_to_next_level = 0
            level_name = "Unknown"
        else:
            xp_to_next_level = level_info['xp_to_next']
            level_name = level_info['level_name']

        # Get engagement points breakdown by source_type
        breakdown_rows = await conn.fetch(
            """
            SELECT source_type, SUM(points) as total_points
            FROM engagement_points
            WHERE user_id = $1
            GROUP BY source_type
            """,
            id
        )
        engagement_points_breakdown = {
            row['source_type']: row['total_points']
            for row in breakdown_rows
        }

        return UserProfile(
            level=current_level,
            total_xp=total_xp,
            xp_to_next_level=xp_to_next_level,
            engagement_points_breakdown=engagement_points_breakdown
        )


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    period: str = Query("all", pattern="^(week|month|all)$"),
    limit: int = Query(50, ge=1, le=50),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get leaderboard for a given period."""
    # Determine the period start time
    if period == "week":
        period_start = "CURRENT_DATE - INTERVAL '7 days'"
    elif period == "month":
        period_start = "CURRENT_DATE - INTERVAL '1 month'"
    else:  # all
        period_start = "NULL"  # no filter

    # Build the query
    if period == "all":
        query = """
            SELECT
                u.id AS user_id,
                u.current_level,
                ul.level_name,
                COALESCE(SUM(ep.points), 0) AS points,
                ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(ep.points), 0) DESC) AS rank
            FROM users u
            JOIN user_levels ul ON u.current_level = ul.level_id
            LEFT JOIN engagement_points ep ON u.id = ep.user_id
            GROUP BY u.id, u.current_level, ul.level_name
            ORDER BY points DESC
            LIMIT $1
        """
    else:
        query = f"""
            SELECT
                u.id AS user_id,
                u.current_level,
                ul.level_name,
                COALESCE(SUM(ep.points), 0) AS points,
                ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(ep.points), 0) DESC) AS rank
            FROM users u
            JOIN user_levels ul ON u.current_level = ul.level_id
            LEFT JOIN engagement_points ep ON u.id = ep.user_id
                AND ep.created_at >= {period_start}
            GROUP BY u.id, u.current_level, ul.level_name
            ORDER BY points DESC
            LIMIT $1
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit)
        return [
            LeaderboardEntry(
                rank=row['rank'],
                user_id=row['user_id'],
                level_name=row['level_name'],
                current_level=row['current_level'],
                points=row['points']
            )
            for row in rows
        ]


@router.get("/users/{id}/points", response_model=List[EngagementPointEntry])
async def get_user_points(
    id: int,
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get engagement points history for a user."""
    async with pool.acquire() as conn:
        if source_type:
            rows = await conn.fetch(
                """
                SELECT * FROM engagement_points
                WHERE user_id = $1 AND source_type = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                id, source_type, limit, offset
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM engagement_points
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                id, limit, offset
            )

        return [
            EngagementPointEntry(
                id=row['id'],
                points=row['points'],
                source_type=row['source_type'],
                source_id=row['source_id'],
                source_metadata=_parse_metadata(row['source_metadata']),
                description=row['description'],
                created_at=str(row['created_at'])
            )
            for row in rows
        ]


@router.get("/users/{id}/skills", response_model=List[UserSkillRating])
async def get_user_skills(
    id: int,
    min_evidence: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get all skill ratings for a user."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT skill_tag, proficiency_score, evidence_count, confidence, last_updated
            FROM user_skill_ratings
            WHERE user_id = $1 AND evidence_count >= $2
            ORDER BY proficiency_score DESC, evidence_count DESC
            LIMIT $3
            """,
            id, min_evidence, limit
        )

        return [
            UserSkillRating(
                skill_tag=row['skill_tag'],
                proficiency_score=row['proficiency_score'],
                evidence_count=row['evidence_count'],
                confidence=row['confidence'],
                last_updated=str(row['last_updated'])
            )
            for row in rows
        ]