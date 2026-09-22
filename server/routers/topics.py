"""Topic submission and management API."""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from server.database import fetch, fetchrow, execute

router = APIRouter()


class TopicSubmission(BaseModel):
    """Incoming survey submission."""
    name: Optional[str] = "Anonymous"
    email: Optional[str] = None
    topics: list[str] = Field(..., min_items=1)
    categories: Optional[list[str]] = None
    website_url: Optional[str] = None
    source: Optional[str] = "web"

    class Config:
        extra = "allow"


class TopicResponse(BaseModel):
    id: str
    name: str
    email_hash: str
    raw_topics: list[str]
    categories: Optional[list[str]]
    status: str
    created_at: str
    lessons: Optional[list[dict]] = None


@router.post("/submit", response_model=dict)
async def submit_topics(submission: TopicSubmission):
    """Submit learning topics. Returns topic ID for tracking."""
    # Check honeypot
    if submission.website_url and submission.website_url.strip():
        return {
            "id": f"topic_{uuid.uuid4().hex[:12]}",
            "status": "pending",
            "email_hash": "",
            "message": "Submission received."
        }

    name = (submission.name or "").strip() or "Anonymous"
    raw_email = (submission.email or "").strip()
    if raw_email:
        email = raw_email
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
    else:
        # Default identifier for anonymous submissions
        email_hash = hashlib.sha256(f"anon_{name}_{uuid.uuid4().hex[:6]}".encode()).hexdigest()
        email = f"{email_hash[:10]}@makesense.local"

    topic_id = f"topic_{uuid.uuid4().hex[:12]}"
    
    # 1-to-1 ordered classification per topic
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
    try:
        from categorize import classify_topic
    except ImportError:
        def classify_topic(t: str) -> str:
            return "General"

    categories = []
    for i, t in enumerate(submission.topics):
        if submission.categories and i < len(submission.categories) and submission.categories[i]:
            categories.append(submission.categories[i])
        else:
            categories.append(classify_topic(t))
    
    # Find or create user
    user = await fetchrow(
        "SELECT id FROM users WHERE email = $1", email
    )
    user_id = user["id"] if user else None
    
    if not user_id:
        user_id_result = await fetchrow(
            """INSERT INTO users (email, name, created_at) 
               VALUES ($1, $2, NOW()) 
               RETURNING id""",
            email, name
        )
        user_id = user_id_result["id"] if user_id_result else None
    
    await execute(
        """INSERT INTO topics (id, user_id, name, email, email_hash, raw_topics, categories, status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')""",
        topic_id, user_id, name, email, email_hash,
        submission.topics, categories or []
    )
    
    return {
        "id": topic_id,
        "status": "pending",
        "email_hash": email_hash,
        "message": f"Submitted {len(submission.topics)} topics. Use the email_hash to access your library."
    }


@router.get("/topics")
async def list_topics(
    user: Optional[str] = Query(None, description="Email SHA-256 hash to filter by user"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200)
):
    """List submitted topics, optionally filtered by user hash or status."""
    conditions = []
    params = []
    param_idx = 1
    
    if user:
        conditions.append(f"t.email_hash = ${param_idx}")
        params.append(user)
        param_idx += 1
    
    if status:
        conditions.append(f"t.status = ${param_idx}")
        params.append(status)
        param_idx += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    params.append(limit)
    
    rows = await fetch(
        f"""SELECT t.id, t.name, t.email_hash, t.raw_topics, t.categories, t.status, 
                   t.created_at::text,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', l.id, 'title', l.title, 'summary', l.summary,
                               'difficulty', l.difficulty, 'status', l.status,
                               'skill_tags', l.skill_tags,
                               'estimated_time_minutes', l.estimated_time_minutes
                           )
                       ) FILTER (WHERE l.id IS NOT NULL), '[]'::json
                   ) as lessons
            FROM topics t
            LEFT JOIN lessons l ON l.topic_id = t.id
            {where_clause}
            GROUP BY t.id
            ORDER BY t.created_at DESC
            LIMIT ${param_idx}""",
        *params
    )
    
    return [{"id": r["id"], "name": r["name"], "email_hash": r["email_hash"],
             "raw_topics": r["raw_topics"], "categories": r["categories"],
             "status": r["status"], "created_at": r["created_at"],
             "lessons": json.loads(r["lessons"]) if isinstance(r["lessons"], str) else (r["lessons"] or [])} for r in rows]


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Get a single topic with its generated lessons."""
    row = await fetchrow(
        """SELECT id, name, email_hash, raw_topics, categories, status, created_at::text
           FROM topics WHERE id = $1""",
        topic_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    lessons = await fetch(
        """SELECT id, title, summary, difficulty, status, skill_tags, 
                  estimated_time_minutes, feedback_up, feedback_down, view_count,
                  created_at::text
           FROM lessons WHERE topic_id = $1 ORDER BY created_at""",
        topic_id
    )
    
    return {
        **dict(row),
        "lessons": [dict(l) for l in lessons]
    }
