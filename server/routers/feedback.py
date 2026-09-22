"""Feedback API."""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.database import fetch, fetchrow, execute

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackSubmission(BaseModel):
    lesson_id: str
    feedback_type: str  # 'up' or 'down'
    comment: Optional[str] = None
    user_identifier: Optional[str] = None


@router.post("")
async def submit_feedback(feedback: FeedbackSubmission):
    """Submit feedback for a lesson."""
    if feedback.feedback_type not in ('up', 'down'):
        raise HTTPException(status_code=400, detail="Invalid feedback type")
        
    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
    
    # Verify lesson exists
    lesson = await fetchrow("SELECT id FROM lessons WHERE id = $1", feedback.lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    try:
        # We assume a feedback table exists
        await execute(
            """INSERT INTO feedback (id, lesson_id, feedback_type, comment, user_identifier)
               VALUES ($1, $2, $3, $4, $5)""",
            feedback_id, feedback.lesson_id, feedback.feedback_type, 
            feedback.comment, feedback.user_identifier
        )
    except Exception as e:
        # Ignore if table doesn't exist yet, we will just update lesson counts
        print(f"Feedback insert error: {e}")
        
    # Update lesson counts
    if feedback.feedback_type == 'up':
        await execute("UPDATE lessons SET feedback_up = feedback_up + 1 WHERE id = $1", feedback.lesson_id)
    else:
        await execute("UPDATE lessons SET feedback_down = feedback_down + 1 WHERE id = $1", feedback.lesson_id)
        
    return {"message": "Feedback received", "id": feedback_id}


@router.get("/summary/{lesson_id}")
async def get_feedback_summary(lesson_id: str):
    """Get feedback summary for a lesson."""
    lesson = await fetchrow(
        "SELECT feedback_up, feedback_down FROM lessons WHERE id = $1", 
        lesson_id
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    try:
        comments_rows = await fetch(
            "SELECT comment, created_at FROM feedback WHERE lesson_id = $1 AND comment IS NOT NULL ORDER BY created_at DESC LIMIT 20",
            lesson_id
        )
        comments = [dict(r) for r in comments_rows]
    except Exception:
        comments = []
        
    up = lesson['feedback_up'] or 0
    down = lesson['feedback_down'] or 0
    total = up + down
    score = (up / total) * 100 if total > 0 else 0
    
    return {
        "up": up,
        "down": down,
        "score": score,
        "comments": comments
    }


@router.get("/all")
async def get_all_feedback():
    """Returns all feedback for admin dashboard."""
    try:
        rows = await fetch(
            """SELECT f.id, f.feedback_type, f.comment, f.user_identifier, f.created_at::text,
                      l.title as lesson_title, l.topic_id
               FROM feedback f
               JOIN lessons l ON f.lesson_id = l.id
               ORDER BY f.created_at DESC
               LIMIT 100"""
        )
        return [dict(r) for r in rows]
    except Exception:
        return []
