from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from server.database import fetch, fetchrow, execute
from gamification.engine import GamificationEngine

router = APIRouter()

class ReviewItem(BaseModel):
    question: str
    correct_answer: str
    explanation: Optional[str] = None

class EnqueueRequest(BaseModel):
    user_id: int
    lesson_id: str
    questions: List[ReviewItem]

class SubmitReviewRequest(BaseModel):
    quality: int

@router.post("/reviews/enqueue")
async def enqueue_reviews(request: Request, payload: EnqueueRequest):
    for q in payload.questions:
        await execute(
            """
            INSERT INTO spaced_repetition_items (user_id, lesson_id, question, correct_answer, explanation)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, lesson_id, question) DO NOTHING
            """,
            payload.user_id, payload.lesson_id, q.question, q.correct_answer, q.explanation
        )
    return {"message": f"Enqueued questions."}

@router.get("/reviews/{user_id}/due")
async def get_due_reviews(request: Request, user_id: int):
    items = await fetch(
        """
        SELECT * FROM spaced_repetition_items
        WHERE user_id = $1 AND next_review_date <= CURRENT_DATE
        """,
        user_id
    )
    return {"due_items": [dict(i) for i in items]}

@router.post("/reviews/{item_id}/submit")
async def submit_review(request: Request, item_id: int, payload: SubmitReviewRequest):
    if not 0 <= payload.quality <= 5:
        raise HTTPException(status_code=400, detail="Quality must be between 0 and 5.")

    item = await fetchrow(
        "SELECT * FROM spaced_repetition_items WHERE id = $1",
        item_id
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    interval_days = item["interval_days"]
    ease_factor = item["ease_factor"]
    
    if payload.quality >= 3:
        if interval_days == 0:
            new_interval = 1
        elif interval_days == 1:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)
    else:
        new_interval = 0

    new_ease = ease_factor + (0.1 - (5 - payload.quality) * (0.08 + (5 - payload.quality) * 0.02))
    new_ease = max(1.3, new_ease)
    
    await execute(
        """
        UPDATE spaced_repetition_items
        SET interval_days = $1::int, ease_factor = $2::real, next_review_date = CURRENT_DATE + $1::int * INTERVAL '1 day'
        WHERE id = $3
        """,
        new_interval, new_ease, item_id
    )

    user_id = item["user_id"]
    pool = request.app.state.pool if hasattr(request.app.state, 'pool') else request.app.state.db_pool
    await execute("SELECT award_engagement_points($1, $2, 'review_completion', NULL, NULL, 'Spaced repetition review completed')", user_id, 10)

    return {
        "id": item_id,
        "new_interval": new_interval,
        "new_ease": new_ease
    }
