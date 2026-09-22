"""Content generation and lesson API."""
import uuid
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.database import fetch, fetchrow, execute
from server.content_generator import generate_lesson, generate_lesson_stream

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
try:
    from categorize import classify_topic
except ImportError:
    def classify_topic(t: str) -> str:
        return "General"

router = APIRouter()


async def process_topic_generation(topic_id: str):
    """Background task to generate content for a topic."""
    row = await fetchrow("SELECT raw_topics, categories FROM topics WHERE id = $1", topic_id)
    if not row:
        return
    
    raw_topics = row['raw_topics']
    categories = row['categories'] or []
    
    for i, t in enumerate(raw_topics):
        lesson_id = f"lesson_{uuid.uuid4().hex[:12]}"
        # Correctly resolve category per individual topic
        if i < len(categories) and categories[i]:
            category = categories[i]
        else:
            category = classify_topic(t)
        
        # Generate lesson
        lesson_data = await generate_lesson(t, category, "beginner")
        
        # Insert lesson
        await execute(
            """INSERT INTO lessons (id, topic_id, title, summary, difficulty, 
                       estimated_time_minutes, content, skill_tags, status)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, 'generated')""",
            lesson_id, topic_id, lesson_data.get('title', f"Lesson on {t}"), 
            lesson_data.get('summary', ""), lesson_data.get('difficulty', "beginner"),
            lesson_data.get('estimated_time_minutes', 15), 
            json.dumps(lesson_data),
            lesson_data.get('skill_tags', [])
        )
        
    await execute("UPDATE topics SET status = 'completed' WHERE id = $1", topic_id)


@router.post("/generate/{topic_id}")
async def generate_topic_content(topic_id: str, background_tasks: BackgroundTasks):
    """Triggers generation for a topic."""
    row = await fetchrow("SELECT status FROM topics WHERE id = $1", topic_id)
    if not row:
        raise HTTPException(status_code=404, detail="Topic not found")
        
    if row['status'] != 'pending':
        return {"message": f"Topic generation already {row['status']}"}
        
    await execute("UPDATE topics SET status = 'processing' WHERE id = $1", topic_id)
    background_tasks.add_task(process_topic_generation, topic_id)
    
    return {"message": "Generation started", "status": "processing"}


@router.get("/generate/{topic_id}/stream")
async def stream_topic_generation(topic_id: str):
    """Real-time streaming lesson generation endpoint (Server-Sent Events).
    Emits token events as on-device AI generates content, then persists the completed lesson."""
    row = await fetchrow("SELECT raw_topics, categories, status FROM topics WHERE id = $1", topic_id)
    if not row:
        raise HTTPException(status_code=404, detail="Topic not found")

    raw_topics = row['raw_topics']
    categories = row['categories'] or []
    target_topic = raw_topics[0] if raw_topics else "General Concepts"
    category = categories[0] if categories and categories[0] else classify_topic(target_topic)

    await execute("UPDATE topics SET status = 'processing' WHERE id = $1", topic_id)

    async def event_publisher():
        final_lesson = None
        async for chunk in generate_lesson_stream(target_topic, category, "beginner"):
            yield chunk
            if '"event": "complete"' in chunk:
                try:
                    payload = json.loads(chunk.split("data: ", 1)[1].strip())
                    final_lesson = payload.get("lesson")
                except Exception:
                    pass

        if final_lesson:
            lesson_id = f"lesson_{uuid.uuid4().hex[:12]}"
            await execute(
                """INSERT INTO lessons (id, topic_id, title, summary, difficulty, 
                           estimated_time_minutes, content, skill_tags, status)
                   VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, 'generated')""",
                lesson_id, topic_id, final_lesson.get('title', f"Lesson on {target_topic}"), 
                final_lesson.get('summary', ""), final_lesson.get('difficulty', "beginner"),
                final_lesson.get('estimated_time_minutes', 15), 
                json.dumps(final_lesson),
                final_lesson.get('skill_tags', [])
            )
            await execute("UPDATE topics SET status = 'completed' WHERE id = $1", topic_id)
            yield f'data: {json.dumps({"event": "persisted", "lesson_id": lesson_id, "topic_id": topic_id})}\n\n'

    return StreamingResponse(
        event_publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/lessons/{lesson_id}")
async def get_lesson(lesson_id: str):
    """Get full lesson content including quiz."""
    row = await fetchrow(
        """SELECT id, topic_id, title, summary, difficulty, estimated_time_minutes,
                  content, skill_tags, status, view_count,
                  feedback_up, feedback_down, created_at::text
           FROM lessons WHERE id = $1""",
        lesson_id
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    # Increment view_count
    await execute("UPDATE lessons SET view_count = view_count + 1 WHERE id = $1", lesson_id)
    
    lesson = dict(row)
    if isinstance(lesson.get('content'), str):
        lesson['content'] = json.loads(lesson['content'])
        
    return lesson


@router.get("/lessons/{lesson_id}/quiz")
async def get_lesson_quiz(lesson_id: str):
    """Get just the quiz questions (without answers for client-side)."""
    row = await fetchrow("SELECT title, content FROM lessons WHERE id = $1", lesson_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    content = row['content']
    if isinstance(content, str):
        content = json.loads(content)
        
    quiz_data = content.get('quiz', []) if isinstance(content, dict) else []
    client_quiz = []
    for q in quiz_data:
        client_q = {k: v for k, v in q.items() if k not in ['correct_answer', 'explanation']}
        client_quiz.append(client_q)
        
    return {
        "lesson_title": row['title'],
        "questions": client_quiz
    }
