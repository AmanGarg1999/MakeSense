"""Learning Path API with AI Mentorship and Progressive 3D Skill Tree Unlocking."""

import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.database import fetch, fetchrow, execute, get_pool
from server.path_generator import curate_learning_path, evaluate_and_evolve_path, generate_pathway_options
from server.content_generator import generate_lesson
from server.config import settings
from gamification.engine import GamificationEngine

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
try:
    from categorize import classify_topic
except ImportError:
    def classify_topic(t: str) -> str:
        return "General"

router = APIRouter()


class PathCurateRequest(BaseModel):
    name: Optional[str] = "Learner"
    email: Optional[str] = None
    topic: str
    category: Optional[str] = None
    goal: Optional[str] = "life_skill"
    baseline: Optional[str] = "beginner"
    modality: Optional[str] = "hands_on"
    pace: Optional[str] = "focus"
    pain_points: Optional[str] = None
    track_type: Optional[str] = "fast_track"
    mentor_persona: Optional[str] = "Encouraging Guide"


class NodeCompleteRequest(BaseModel):
    quiz_score: int = Field(..., ge=0, le=100)


@router.post("/preview-options", response_model=List[Dict[str, Any]])
async def preview_pathway_options(req: PathCurateRequest):
    """Generates 3 distinct tailored educational pathway options for the learner to compare."""
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    category = req.category or classify_topic(topic)
    profile = {
        "name": req.name or "Learner",
        "email": req.email,
        "goal": req.goal,
        "baseline": req.baseline,
        "modality": req.modality,
        "pace": req.pace,
        "pain_points": req.pain_points
    }
    return generate_pathway_options(topic, category, profile)


@router.post("/curate", response_model=Dict[str, Any])
async def create_curated_path(req: PathCurateRequest):
    """Diagnoses user profile and curates an adaptive learning path with mentor guidance."""
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    category = req.category or classify_topic(topic)
    profile = {
        "name": req.name or "Learner",
        "email": req.email,
        "goal": req.goal,
        "baseline": req.baseline,
        "modality": req.modality,
        "pace": req.pace,
        "pain_points": req.pain_points,
        "track_type": req.track_type or "fast_track"
    }

    path_data = curate_learning_path(topic, category, profile, track_type=req.track_type or "fast_track", mentor_persona=req.mentor_persona)
    path_id = f"path_{uuid.uuid4().hex[:12]}"

    import hashlib
    raw_email = (req.email or "").strip()
    if raw_email:
        email = raw_email
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
    else:
        email_hash = hashlib.sha256(f"anon_{req.name}_{uuid.uuid4().hex[:6]}".encode()).hexdigest()
        email = f"{email_hash[:10]}@makesense.local"

    # Ensure topic record exists for foreign key references and library views
    await execute(
        """INSERT INTO topics (id, name, email, email_hash, raw_topics, categories, status)
           VALUES ($1, $2, $3, $4, $5, $6, 'completed')
           ON CONFLICT (id) DO NOTHING""",
        path_id, req.name or "Learner", email, email_hash, [topic], [category]
    )

    # Just-in-time generate the lesson content for Node 0 (the root milestone)
    root_node = path_data["nodes"][0]
    root_lesson = await generate_lesson(root_node["title"], category, req.baseline)
    root_lesson_id = f"lesson_{uuid.uuid4().hex[:12]}"

    await execute(
        """INSERT INTO lessons (id, topic_id, title, summary, difficulty, 
                   estimated_time_minutes, content, skill_tags, status)
           VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, 'generated')""",
        root_lesson_id, path_id, root_node["title"],
        root_lesson.get("summary", ""), root_node["difficulty"],
        root_node["estimated_time_minutes"], json.dumps(root_lesson),
        root_lesson.get("skill_tags", [])
    )
    root_node["lesson_id"] = root_lesson_id

    # Persist Learning Path
    metadata = {"mentor_persona": req.mentor_persona}
    await execute(
        """INSERT INTO learning_paths (id, title, topic, category, user_profile, mentor_notes, status, completion_rate, metadata)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6, 'in_progress', 0, $7::jsonb)""",
        path_id, path_data["title"], topic, category,
        json.dumps(profile), path_data["mentor_notes"], json.dumps(metadata)
    )

    # Persist Nodes
    for node in path_data["nodes"]:
        await execute(
            """INSERT INTO path_nodes (id, path_id, title, description, mentor_rationale, status, 
                       estimated_time_minutes, difficulty, prerequisites, coordinates, order_index, lesson_id, metadata)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11, $12, $13::jsonb)""",
            node["id"], path_id, node["title"], node["description"],
            node["mentor_rationale"], node["status"], node["estimated_time_minutes"],
            node["difficulty"], json.dumps(node["prerequisites"]),
            json.dumps(node["coordinates"]), node["order_index"],
            node.get("lesson_id"), json.dumps(node.get("metadata", {}))
        )

    return {
        "id": path_id,
        "title": path_data["title"],
        "topic": topic,
        "category": category,
        "mentor_notes": path_data["mentor_notes"],
        "user_profile": profile,
        "completion_rate": 0,
        "nodes": path_data["nodes"]
    }


@router.get("", response_model=List[Dict[str, Any]])
async def list_learning_paths():
    """Lists recent curated learning paths."""
    rows = await fetch("SELECT * FROM learning_paths ORDER BY created_at DESC LIMIT 20")
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "title": r["title"],
            "topic": r["topic"],
            "category": r["category"],
            "mentor_notes": r["mentor_notes"],
            "completion_rate": r["completion_rate"],
            "status": r["status"],
            "created_at": str(r["created_at"])
        })
    return results


@router.get("/{path_id}", response_model=Dict[str, Any])
async def get_learning_path(path_id: str):
    """Retrieves learning path graph and all milestones."""
    path_row = await fetchrow("SELECT * FROM learning_paths WHERE id = $1", path_id)
    if not path_row:
        raise HTTPException(status_code=404, detail="Learning path not found")

    node_rows = await fetch(
        "SELECT * FROM path_nodes WHERE path_id = $1 ORDER BY order_index ASC", path_id
    )

    nodes = []
    for nr in node_rows:
        nodes.append({
            "id": nr["id"],
            "title": nr["title"],
            "description": nr["description"],
            "mentor_rationale": nr["mentor_rationale"],
            "status": nr["status"],
            "estimated_time_minutes": nr["estimated_time_minutes"],
            "difficulty": nr["difficulty"],
            "prerequisites": json.loads(nr["prerequisites"]) if isinstance(nr["prerequisites"], str) else (nr["prerequisites"] or []),
            "coordinates": json.loads(nr["coordinates"]) if isinstance(nr["coordinates"], str) else (nr["coordinates"] or {"x": 0, "y": 0, "z": 0}),
            "order_index": nr["order_index"],
            "lesson_id": nr["lesson_id"],
            "quiz_score": nr["quiz_score"],
            "metadata": json.loads(nr["metadata"]) if nr.get("metadata") and isinstance(nr["metadata"], str) else (nr.get("metadata") or {})
        })

    return {
        "id": path_row["id"],
        "title": path_row["title"],
        "topic": path_row["topic"],
        "category": path_row["category"],
        "mentor_notes": path_row["mentor_notes"],
        "user_profile": json.loads(path_row["user_profile"]) if isinstance(path_row["user_profile"], str) else path_row["user_profile"],
        "completion_rate": path_row["completion_rate"],
        "status": path_row["status"],
        "created_at": str(path_row["created_at"]),
        "nodes": nodes
    }


@router.post("/{path_id}/nodes/{node_id}/unlock", response_model=Dict[str, Any])
async def unlock_and_generate_node_lesson(path_id: str, node_id: str):
    """Just-in-time generation of lesson content when a user enters an unlocked node."""
    node_row = await fetchrow(
        "SELECT * FROM path_nodes WHERE id = $1 AND path_id = $2", node_id, path_id
    )
    if not node_row:
        raise HTTPException(status_code=404, detail="Node not found")

    path_row = await fetchrow("SELECT * FROM learning_paths WHERE id = $1", path_id)
    category = path_row["category"] if path_row else "General"

    lesson_id = node_row["lesson_id"]
    if not lesson_id:
        lesson_id = f"lesson_{uuid.uuid4().hex[:12]}"
        lesson_data = await generate_lesson(node_row["title"], category, node_row["difficulty"])
        await execute(
            """INSERT INTO lessons (id, topic_id, title, summary, difficulty, 
                       estimated_time_minutes, content, skill_tags, status)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, 'generated')""",
            lesson_id, path_id, node_row["title"],
            lesson_data.get("summary", ""), node_row["difficulty"],
            node_row["estimated_time_minutes"], json.dumps(lesson_data),
            lesson_data.get("skill_tags", [])
        )
        await execute("UPDATE path_nodes SET lesson_id = $1 WHERE id = $2", lesson_id, node_id)

    return {"lesson_id": lesson_id, "node_id": node_id, "status": "ready"}


@router.post("/{path_id}/nodes/{node_id}/complete", response_model=Dict[str, Any])
async def complete_node_and_evolve_path(path_id: str, node_id: str, req: NodeCompleteRequest):
    """Evaluates quiz score, marks node completed, and dynamically evolves the skill tree."""
    node_rows = await fetch("SELECT * FROM path_nodes WHERE path_id = $1", path_id)
    if not node_rows:
        raise HTTPException(status_code=404, detail="Nodes not found for path")

    nodes = []
    for nr in node_rows:
        nodes.append({
            "id": nr["id"],
            "title": nr["title"],
            "description": nr["description"],
            "mentor_rationale": nr["mentor_rationale"],
            "status": nr["status"],
            "estimated_time_minutes": nr["estimated_time_minutes"],
            "difficulty": nr["difficulty"],
            "prerequisites": json.loads(nr["prerequisites"]) if isinstance(nr["prerequisites"], str) else (nr["prerequisites"] or []),
            "coordinates": json.loads(nr["coordinates"]) if isinstance(nr["coordinates"], str) else (nr["coordinates"] or {"x": 0, "y": 0, "z": 0}),
            "order_index": nr["order_index"],
            "lesson_id": nr["lesson_id"],
            "quiz_score": nr["quiz_score"],
            "metadata": json.loads(nr["metadata"]) if nr.get("metadata") and isinstance(nr["metadata"], str) else (nr.get("metadata") or {})
        })

    evolved = evaluate_and_evolve_path(nodes, node_id, req.quiz_score)

    # Sync back to database
    for n in evolved["nodes"]:
        existing = any(nr["id"] == n["id"] for nr in node_rows)
        if existing:
            await execute(
                """UPDATE path_nodes 
                   SET status = $1, quiz_score = $2 
                   WHERE id = $3 AND path_id = $4""",
                n["status"], n.get("quiz_score"), n["id"], path_id
            )
        else:
            # Newly added remedial reinforcement node
            await execute(
                """INSERT INTO path_nodes (id, path_id, title, description, mentor_rationale, status, 
                           estimated_time_minutes, difficulty, prerequisites, coordinates, order_index)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11)""",
                n["id"], path_id, n["title"], n["description"],
                n["mentor_rationale"], n["status"], n["estimated_time_minutes"],
                n["difficulty"], json.dumps(n["prerequisites"]),
                json.dumps(n["coordinates"]), n["order_index"]
            )

    # Update path completion rate
    await execute(
        "UPDATE learning_paths SET completion_rate = $1, updated_at = NOW() WHERE id = $2",
        evolved["completion_rate"], path_id
    )

    # Check for treasure node
    target_node = next((n for n in nodes if n["id"] == node_id), None)
    if target_node and target_node.get("metadata", {}).get("is_treasure"):
        email = await fetchval("SELECT email FROM topics WHERE id = $1", path_id)
        if email:
            user_id = await fetchval("SELECT id FROM users WHERE email = $1", email)
            if user_id:
                db_pool = await get_pool()
                async with db_pool.acquire() as conn:
                    engine = GamificationEngine(settings.database_url)
                    await engine._award_points(
                        conn=conn,
                        user_id=user_id,
                        points=100,
                        source_type="treasure_node_bonus",
                        source_id=None,
                        description="Found a treasure node!"
                    )

    return {
        "success": True,
        "completion_rate": evolved["completion_rate"],
        "unlocked_nodes": evolved["unlocked_nodes"],
        "remedial_added": evolved["remedial_added"],
        "nodes": evolved["nodes"]
    }
