"""Quiz submission and scoring API."""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from server.database import fetchrow, execute

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])


class Answer(BaseModel):
    question_index: int
    answer: str


class QuizSubmission(BaseModel):
    lesson_id: str
    user_id: int
    answers: List[Answer]


@router.post("/submit")
async def submit_quiz(submission: QuizSubmission, request: Request):
    """Submit quiz answers and calculate score."""
    row = await fetchrow("SELECT content FROM lessons WHERE id = $1", submission.lesson_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    content = row['content']
    if isinstance(content, str):
        content = json.loads(content)
        
    quiz_data = content.get('quiz', []) if isinstance(content, dict) else []
        
    results = []
    correct_count = 0
    total = len(quiz_data)
    
    # Check answers
    answers_dict = {a.question_index: a.answer for a in submission.answers}
    
    for i, question in enumerate(quiz_data):
        user_answer = answers_dict.get(i)
        is_correct = False
        
        if user_answer is not None:
            # Simple string match for MCQ
            if question.get('type', 'mcq') == 'mcq':
                is_correct = user_answer.strip().lower() == question.get('correct_answer', '').strip().lower()
            else:
                # Basic check for short answer for now (in production use LLM)
                is_correct = user_answer.strip().lower() == question.get('correct_answer', '').strip().lower()
                
        if is_correct:
            correct_count += 1
            
        results.append({
            "question_index": i,
            "question": question.get("question"),
            "user_answer": user_answer,
            "correct_answer": question.get("correct_answer"),
            "is_correct": is_correct,
            "explanation": question.get("explanation")
        })
        
    score = (correct_count / total) * 100 if total > 0 else 0
    
    # Calculate XP
    xp_earned = (correct_count * 10)
    if correct_count == total and total > 0:
        xp_earned += 50  # Perfect score bonus
        
    # Store attempt (assuming a quiz_attempts table exists or similar, just simple execute for now)
    try:
        await execute(
            """INSERT INTO quiz_attempts (lesson_id, user_id, score, total_questions, correct_answers, xp_earned)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            submission.lesson_id, submission.user_id, score, total, correct_count, xp_earned
        )
    except Exception as e:
        logger.warning(f"Failed to record quiz attempt: {e}")
        
    # Award gamification points
    try:
        pool = request.app.state.db_pool if hasattr(request.app.state, 'db_pool') else None
        if pool:
            from gamification.engine import GamificationEngine
            engine = GamificationEngine("")
            engine.pool = pool  # Inject existing pool
            await engine._award_points(
                pool, 
                submission.user_id, 
                xp_earned, 
                'question_answer_correct' if correct_count > 0 else 'lesson_completion',
                description=f"Quiz for lesson {submission.lesson_id}"
            )
    except Exception as e:
        logger.error(f"Gamification error: {e}")
        
    streak_result = {}
    new_achievements = []

    # Update streak
    try:
        if pool:
            from server.routers.streaks import update_streak_for_user
            streak_result = await update_streak_for_user(submission.user_id, pool)
    except Exception as e:
        logger.warning(f"Streak update failed: {e}")

    # Evaluate achievements
    try:
        if pool:
            from server.routers.achievements import evaluate_user_achievements
            new_achievements = await evaluate_user_achievements(submission.user_id, pool)
    except Exception as e:
        logger.warning(f"Achievement evaluation failed: {e}")
        
    # Enqueue questions into Spaced Repetition deck
    try:
        if pool:
            for q in results:
                if q.get("question") and q.get("correct_answer"):
                    await execute(
                        """
                        INSERT INTO spaced_repetition_items (user_id, lesson_id, question, correct_answer, explanation)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (user_id, lesson_id, question) DO NOTHING
                        """,
                        submission.user_id, submission.lesson_id, q["question"], q["correct_answer"], q.get("explanation")
                    )
    except Exception as e:
        logger.error(f"Failed to enqueue spaced repetition items: {e}")

    return {
        "score": score,
        "total": total,
        "correct": correct_count,
        "xp_earned": xp_earned,
        "results": results,
        "streak_result": streak_result,
        "new_achievements": new_achievements
    }
