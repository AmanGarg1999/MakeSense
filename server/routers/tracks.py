"""
Skill Track API Routes

FastAPI routes for multi-skill-track management:
- Track CRUD (create, read, update, delete)
- Cross-track dashboard
- Ladder instantiation and queries
- Pacing suggestions
- Verification checkpoints
"""

import json
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
import asyncpg
import logging

from server.skill_ladder_service import SkillLadderService, SkillLadder, SkillLadderRung, SkillTrack

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tracks", tags=["Skill Tracks"])


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_ladder_service(request: Request) -> SkillLadderService:
    """Get skill ladder service from app state."""
    return request.app.state.ladder_service


def get_user_id(request: Request) -> int:
    """Resolve the calling user from the X-User-ID header (app has no auth layer)."""
    return int(request.headers.get("X-User-ID", 1))


# ============================================================================
# Pydantic Models
# ============================================================================

class TrackCreateRequest(BaseModel):
    skill_graph_ref: str
    skill_tag: str
    goal_level: str = Field(default="novice", pattern="^(novice|competent|proficient|expert)$")
    goal_type: str = Field(default="hobby", pattern="^(hobby|job-ready|expert)$")


class TrackUpdateRequest(BaseModel):
    mastery_vector: Optional[Dict[str, Any]] = None
    batch_schedule: Optional[Dict[str, Any]] = None
    coach_narrative: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|done|archived)$")
    progress_pct: Optional[float] = Field(None, ge=0, le=100)
    current_ladder_rung: Optional[int] = Field(None, ge=0, le=3)


class SessionRecordRequest(BaseModel):
    session_type: str = Field(..., pattern="^(learning|practice|verification|recap|diagnostic)$")
    duration_seconds: int = Field(..., ge=0)
    nodes_completed: int = Field(default=0, ge=0)
    mastery_deltas: Optional[Dict[str, float]] = None
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    focus_quality: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class VerificationEvidenceRequest(BaseModel):
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    rubric_scores: Dict[str, Any] = Field(default_factory=dict)
    verifier: str = Field(default="model", pattern="^(model|human|peer)$")


class PacingSuggestionActionRequest(BaseModel):
    action: str = Field(..., pattern="^(accept|dismiss)$")


# ============================================================================
# Track CRUD Routes
# ============================================================================

@router.post("", response_model=Dict[str, Any])
async def create_track(
    req: TrackCreateRequest,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Create a new skill track for the user."""
    try:
        track = await service.create_track(
            user_id=user_id,
            skill_graph_ref=req.skill_graph_ref,
            skill_tag=req.skill_tag,
            goal_level=req.goal_level,
            goal_type=req.goal_type
        )
        if not track:
            raise HTTPException(status_code=400, detail="Failed to create track - ladder may not exist")
        
        # Create initial verification checkpoint
        await service.create_verification_checkpoint(track.id, user_id, 0)
        
        return {
            "id": track.id,
            "skill_graph_ref": track.skill_graph_ref,
            "skill_tag": track.skill_tag,
            "goal_level": track.goal_level,
            "goal_type": track.goal_type,
            "status": track.status,
            "progress_pct": track.progress_pct,
            "current_ladder_rung": track.current_ladder_rung,
            "mastery_vector": track.mastery_vector,
            "batch_schedule": track.batch_schedule,
            "coach_narrative": track.coach_narrative,
            "started_at": track.started_at.isoformat() if track.started_at else None,
            "last_activity_at": track.last_activity_at.isoformat() if track.last_activity_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating track: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[Dict[str, Any]])
async def list_user_tracks(
    status: Optional[str] = Query(None, pattern="^(active|paused|done|archived)$"),
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """List all tracks for the current user."""
    tracks = await service.get_user_tracks(user_id, status)
    return [
        {
            "id": t.id,
            "skill_graph_ref": t.skill_graph_ref,
            "skill_tag": t.skill_tag,
            "goal_level": t.goal_level,
            "goal_type": t.goal_type,
            "status": t.status,
            "progress_pct": t.progress_pct,
            "current_ladder_rung": t.current_ladder_rung,
            "mastery_vector": t.mastery_vector,
            "batch_schedule": t.batch_schedule,
            "coach_narrative": t.coach_narrative,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "paused_at": t.paused_at.isoformat() if t.paused_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "last_activity_at": t.last_activity_at.isoformat() if t.last_activity_at else None
        }
        for t in tracks
    ]


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_cross_track_dashboard(
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Get the cross-track dashboard with all tracks and pacing suggestions."""
    return await service.get_cross_track_dashboard(user_id)


@router.get("/{track_id}", response_model=Dict[str, Any])
async def get_track(
    track_id: str,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Get a specific track by ID."""
    track = await service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    if track.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this track")
    
    # Get current ladder rung details
    ladder_rung = await service.get_ladder_rung(track.skill_tag, track.goal_type, track.current_ladder_rung)
    next_rung = await service.get_ladder_rung(track.skill_tag, track.goal_type, track.current_ladder_rung + 1)
    
    # Get verification checkpoints
    async with service.pool.acquire() as conn:
        checkpoints = await conn.fetch("""
            SELECT * FROM track_verification_checkpoints
            WHERE track_id = $1
            ORDER BY level_index
        """, track_id)
    
    return {
        "id": track.id,
        "skill_graph_ref": track.skill_graph_ref,
        "skill_tag": track.skill_tag,
        "goal_level": track.goal_level,
        "goal_type": track.goal_type,
        "status": track.status,
        "progress_pct": track.progress_pct,
        "current_ladder_rung": track.current_ladder_rung,
        "mastery_vector": track.mastery_vector,
        "batch_schedule": track.batch_schedule,
        "coach_narrative": track.coach_narrative,
        "started_at": track.started_at.isoformat() if track.started_at else None,
        "paused_at": track.paused_at.isoformat() if track.paused_at else None,
        "completed_at": track.completed_at.isoformat() if track.completed_at else None,
        "last_activity_at": track.last_activity_at.isoformat() if track.last_activity_at else None,
        "current_rung": {
            "level_index": ladder_rung.level_index,
            "level_name": ladder_rung.level_name,
            "sub_skills": ladder_rung.sub_skills,
            "evidence_types": ladder_rung.evidence_types,
            "xp_reward": ladder_rung.xp_reward
        } if ladder_rung else None,
        "next_rung": {
            "level_index": next_rung.level_index,
            "level_name": next_rung.level_name,
            "sub_skills": next_rung.sub_skills,
            "evidence_types": next_rung.evidence_types,
            "xp_reward": next_rung.xp_reward
        } if next_rung else None,
        "verification_checkpoints": [
            {
                "level_index": cp['level_index'],
                "status": cp['status'],
                "evidence_refs": cp['evidence_refs'],
                "rubric_scores": cp['rubric_scores'],
                "verifier": cp['verifier'],
                "verified_at": cp['verified_at'].isoformat() if cp['verified_at'] else None,
                "expires_at": cp['expires_at'].isoformat() if cp['expires_at'] else None,
                "recheck_count": cp['recheck_count']
            }
            for cp in checkpoints
        ]
    }


@router.patch("/{track_id}", response_model=Dict[str, Any])
async def update_track(
    track_id: str,
    req: TrackUpdateRequest,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Update a track's fields."""
    track = await service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    if track.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this track")
    
    updated = await service.update_track(
        track_id,
        mastery_vector=req.mastery_vector,
        batch_schedule=req.batch_schedule,
        coach_narrative=req.coach_narrative,
        status=req.status,
        progress_pct=req.progress_pct,
        current_ladder_rung=req.current_ladder_rung
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Track not found after update")
    
    return {
        "id": updated.id,
        "skill_tag": updated.skill_tag,
        "status": updated.status,
        "progress_pct": updated.progress_pct,
        "current_ladder_rung": updated.current_ladder_rung,
        "mastery_vector": updated.mastery_vector,
        "batch_schedule": updated.batch_schedule,
        "coach_narrative": updated.coach_narrative,
        "last_activity_at": updated.last_activity_at.isoformat() if updated.last_activity_at else None
    }


@router.delete("/{track_id}", response_model=Dict[str, Any])
async def delete_track(
    track_id: str,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Archive a track (soft delete)."""
    track = await service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    if track.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this track")
    
    updated = await service.update_track(track_id, status='archived')
    if not updated:
        raise HTTPException(status_code=404, detail="Track not found")
    
    return {"success": True, "message": "Track archived"}


# ============================================================================
# Skill Ladder Routes
# ============================================================================

@router.get("/ladders/available", response_model=List[Dict[str, Any]])
async def list_available_ladders(
    skill_tag: Optional[str] = Query(None),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """List all available ladder configurations."""
    return await service.list_available_ladders(skill_tag)


@router.get("/ladders/{skill_tag}/{goal_type}", response_model=Dict[str, Any])
async def get_ladder(
    skill_tag: str,
    goal_type: str,
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Get the complete ladder for a skill + goal type."""
    ladder = await service.get_ladder(skill_tag, goal_type)
    if not ladder:
        raise HTTPException(status_code=404, detail=f"No ladder found for {skill_tag} / {goal_type}")
    
    return {
        "skill_tag": ladder.skill_tag,
        "goal_type": ladder.goal_type,
        "rungs": [
            {
                "level_index": rung.level_index,
                "level_name": rung.level_name,
                "sub_skills": rung.sub_skills,
                "prerequisites": rung.prerequisites,
                "evidence_types": rung.evidence_types,
                "xp_reward": rung.xp_reward
            }
            for rung in ladder.rungs
        ]
    }


@router.post("/ladders/{skill_tag}/{goal_type}/instantiate", response_model=Dict[str, Any])
async def instantiate_ladder(
    skill_tag: str,
    goal_type: str,
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Instantiate a ladder for a new track - returns mastery vector template and batch schedule."""
    try:
        return await service.instantiate_ladder_for_track(skill_tag, goal_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Session Recording
# ============================================================================

@router.post("/{track_id}/sessions", response_model=Dict[str, Any])
async def record_session(
    track_id: str,
    req: SessionRecordRequest,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Record a learning session for pacing analytics."""
    track = await service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    if track.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized for this track")
    
    return await service.record_session(
        track_id=track_id,
        user_id=user_id,
        session_type=req.session_type,
        duration_seconds=req.duration_seconds,
        nodes_completed=req.nodes_completed,
        mastery_deltas=req.mastery_deltas,
        energy_level=req.energy_level,
        focus_quality=req.focus_quality,
        notes=req.notes
    )


# ============================================================================
# Pacing Suggestions
# ============================================================================

@router.post("/pacing/generate", response_model=List[Dict[str, Any]])
async def generate_pacing_suggestions(
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Generate companion-mediated pacing suggestions."""
    return await service.generate_pacing_suggestions(user_id)


@router.post("/pacing/{suggestion_id}/action", response_model=Dict[str, Any])
async def act_on_pacing_suggestion(
    suggestion_id: int,
    req: PacingSuggestionActionRequest,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Accept or dismiss a pacing suggestion."""
    async with service.pool.acquire() as conn:
        suggestion = await conn.fetchrow("""
            SELECT * FROM track_pacing_suggestions
            WHERE id = $1 AND user_id = $2
        """, suggestion_id, user_id)
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        new_status = 'accepted' if req.action == 'accept' else 'dismissed'
        await conn.execute("""
            UPDATE track_pacing_suggestions
            SET status = $1, resolved_at = NOW()
            WHERE id = $2
        """, new_status, suggestion_id)
        
        return {"success": True, "status": new_status}


# ============================================================================
# Verification Checkpoints
# ============================================================================

@router.post("/{track_id}/verify/{level_index}", response_model=Dict[str, Any])
async def submit_verification(
    track_id: str,
    level_index: int,
    req: VerificationEvidenceRequest,
    user_id: int = Depends(get_user_id),
    service: SkillLadderService = Depends(get_ladder_service)
):
    """Submit evidence for a verification checkpoint."""
    track = await service.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    if track.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized for this track")
    
    if level_index != track.current_ladder_rung:
        raise HTTPException(status_code=400, detail=f"Can only verify current rung ({track.current_ladder_rung})")
    
    return await service.submit_verification_evidence(
        track_id=track_id,
        level_index=level_index,
        evidence=req.evidence,
        rubric_scores=req.rubric_scores,
        verifier=req.verifier
    )