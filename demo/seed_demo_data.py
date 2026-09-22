#!/usr/bin/env python3
"""
MakeSense Demo Data Seeder

Seeds the database with compelling demo data for demonstration purposes:
- 3 demo users at different levels
- Pre-generated lessons across categories
- Quiz attempt history showing progression
- Skill ratings, achievements, and feedback

Usage:
    python demo/seed_demo_data.py

Requires DATABASE_URL environment variable or .env file.
"""

import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import asyncpg


async def get_connection():
    """Get database connection from environment."""
    # Try loading .env
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://makesense:makesense_dev@localhost:5432/makesense",
    )
    return await asyncpg.connect(db_url)


# ---------------------------------------------------------------------------
# Demo content: pre-built lessons so the demo works WITHOUT a Gemini API key
# ---------------------------------------------------------------------------

DEMO_LESSONS = [
    {
        "topic": "Python Decorators",
        "category": "Programming",
        "difficulty": "intermediate",
        "content": {
            "title": "Mastering Python Decorators",
            "summary": "Learn how Python decorators work under the hood, from simple function wrappers to parameterized class-based decorators.",
            "estimated_time_minutes": 20,
            "sections": [
                {
                    "heading": "What Are Decorators?",
                    "content": "A **decorator** is a function that takes another function as input and returns a new function that usually extends the original's behavior.\n\nIn Python the `@decorator` syntax is syntactic sugar for `func = decorator(func)`.",
                    "key_points": [
                        "Decorators are higher-order functions",
                        "@syntax is shorthand for wrapping",
                        "They enable separation of concerns",
                    ],
                },
                {
                    "heading": "Writing Your First Decorator",
                    "content": "The simplest decorator wraps a function, adds behavior before/after, and returns the wrapper.\n\n```python\ndef timer(func):\n    import time\n    def wrapper(*args, **kwargs):\n        start = time.time()\n        result = func(*args, **kwargs)\n        print(f'{func.__name__} took {time.time()-start:.3f}s')\n        return result\n    return wrapper\n```",
                    "key_points": [
                        "Use *args/**kwargs to pass through arguments",
                        "Always return the result of the wrapped function",
                        "Use functools.wraps to preserve metadata",
                    ],
                },
                {
                    "heading": "Decorators with Arguments",
                    "content": "To create a decorator that accepts its own arguments, add an outer function layer:\n\n```python\ndef repeat(n):\n    def decorator(func):\n        def wrapper(*args, **kwargs):\n            for _ in range(n):\n                result = func(*args, **kwargs)\n            return result\n        return wrapper\n    return decorator\n\n@repeat(3)\ndef greet():\n    print('Hello!')\n```",
                    "key_points": [
                        "Three levels of nesting: factory → decorator → wrapper",
                        "The factory returns the actual decorator",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "Logging Decorator",
                    "code_or_text": "from functools import wraps\n\ndef log_calls(func):\n    @wraps(func)\n    def wrapper(*args, **kwargs):\n        print(f'Calling {func.__name__}({args}, {kwargs})')\n        result = func(*args, **kwargs)\n        print(f'{func.__name__} returned {result}')\n        return result\n    return wrapper\n\n@log_calls\ndef add(a, b):\n    return a + b\n\nadd(2, 3)  # Prints call info + returns 5",
                    "language": "python",
                    "explanation": "This decorator logs every call to the wrapped function, including arguments and return value.",
                }
            ],
            "quiz": [
                {
                    "question": "What does the @decorator syntax in Python actually do?",
                    "type": "mcq",
                    "options": [
                        "It is equivalent to func = decorator(func)",
                        "It creates a new class",
                        "It imports a module",
                        "It defines a generator",
                    ],
                    "correct_answer": "It is equivalent to func = decorator(func)",
                    "explanation": "@decorator is syntactic sugar that passes the function to the decorator and rebinds the name.",
                },
                {
                    "question": "Why should you use functools.wraps in a decorator?",
                    "type": "mcq",
                    "options": [
                        "To preserve the original function's name and docstring",
                        "To make the decorator faster",
                        "To enable async support",
                        "To prevent memory leaks",
                    ],
                    "correct_answer": "To preserve the original function's name and docstring",
                    "explanation": "Without @wraps, the wrapper function replaces metadata like __name__ and __doc__.",
                },
                {
                    "question": "How many levels of function nesting are needed for a parameterized decorator?",
                    "type": "mcq",
                    "options": ["Two", "Three", "Four", "One"],
                    "correct_answer": "Three",
                    "explanation": "Factory (takes params) → Decorator (takes func) → Wrapper (takes *args, **kwargs).",
                },
                {
                    "question": "In your own words, explain why decorators are useful for logging and timing.",
                    "type": "short_answer",
                    "correct_answer": "Decorators allow separating cross-cutting concerns like logging from business logic",
                    "explanation": "They let you add behavior without modifying the original function, following the open/closed principle.",
                },
            ],
            "skill_tags": ["python", "programming"],
            "prerequisites": ["Python functions", "closures"],
        },
    },
    {
        "topic": "Newton's Laws of Motion",
        "category": "Academic",
        "difficulty": "beginner",
        "content": {
            "title": "Newton's Three Laws of Motion",
            "summary": "Understand the fundamental laws that govern how objects move, from inertia to action-reaction pairs.",
            "estimated_time_minutes": 15,
            "sections": [
                {
                    "heading": "First Law: Inertia",
                    "content": "An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by a net external force.\n\nThis is why you lurch forward when a bus brakes suddenly — your body wants to keep moving.",
                    "key_points": [
                        "Objects resist changes in their state of motion",
                        "No net force means no acceleration",
                    ],
                },
                {
                    "heading": "Second Law: F = ma",
                    "content": "The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass.\n\n**F = ma** (Force = mass × acceleration)\n\nThis means pushing a shopping cart (small mass) is easier than pushing a car (large mass) with the same force.",
                    "key_points": [
                        "Force equals mass times acceleration",
                        "Heavier objects need more force for the same acceleration",
                        "The unit of force is the Newton (N)",
                    ],
                },
                {
                    "heading": "Third Law: Action-Reaction",
                    "content": "For every action, there is an equal and opposite reaction.\n\nWhen you push against a wall, the wall pushes back against you with equal force. A rocket works by expelling gas downward — the reaction pushes it upward.",
                    "key_points": [
                        "Forces always come in pairs",
                        "Action and reaction act on different objects",
                        "The forces are equal in magnitude but opposite in direction",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "Calculating Force",
                    "code_or_text": "# A 5 kg object accelerates at 3 m/s²\nmass = 5      # kg\naccel = 3     # m/s²\nforce = mass * accel\nprint(f'Force = {force} N')  # 15 N",
                    "language": "python",
                    "explanation": "Using F = ma to calculate the net force needed to accelerate a 5 kg object at 3 m/s².",
                }
            ],
            "quiz": [
                {
                    "question": "What does Newton's First Law describe?",
                    "type": "mcq",
                    "options": ["Inertia", "Gravity", "Friction", "Energy conservation"],
                    "correct_answer": "Inertia",
                    "explanation": "The First Law states objects maintain their state of motion unless a net force acts on them.",
                },
                {
                    "question": "A 10 kg box is pushed with a force of 50 N. What is its acceleration?",
                    "type": "mcq",
                    "options": ["5 m/s²", "500 m/s²", "0.2 m/s²", "50 m/s²"],
                    "correct_answer": "5 m/s²",
                    "explanation": "F = ma → a = F/m = 50/10 = 5 m/s².",
                },
                {
                    "question": "Explain why a rocket can propel itself in the vacuum of space using Newton's Third Law.",
                    "type": "short_answer",
                    "correct_answer": "The rocket expels gas in one direction, and the reaction force pushes it in the opposite direction",
                    "explanation": "Action-reaction pairs don't need a medium — the expelled gas pushes back on the rocket.",
                },
            ],
            "skill_tags": ["physics", "academic"],
            "prerequisites": [],
        },
    },
    {
        "topic": "Machine Learning Basics",
        "category": "ML/AI",
        "difficulty": "beginner",
        "content": {
            "title": "Introduction to Machine Learning",
            "summary": "Understand what machine learning is, the types of ML (supervised, unsupervised, reinforcement), and see a simple example.",
            "estimated_time_minutes": 18,
            "sections": [
                {
                    "heading": "What is Machine Learning?",
                    "content": "Machine Learning (ML) is a subset of artificial intelligence where systems learn patterns from data instead of being explicitly programmed.\n\nTraditional programming: Input + Rules → Output\nMachine Learning: Input + Output → Rules (the model learns the rules)",
                    "key_points": [
                        "ML learns from data rather than explicit instructions",
                        "Models improve with more/better data",
                        "ML is a subset of AI",
                    ],
                },
                {
                    "heading": "Types of Machine Learning",
                    "content": "**Supervised Learning**: Train on labeled data (input-output pairs). Examples: spam detection, image classification.\n\n**Unsupervised Learning**: Find patterns in unlabeled data. Examples: customer segmentation, anomaly detection.\n\n**Reinforcement Learning**: Learn through trial and error with rewards. Examples: game playing, robotics.",
                    "key_points": [
                        "Supervised = labeled data, predict outputs",
                        "Unsupervised = unlabeled data, find patterns",
                        "Reinforcement = learn from rewards and penalties",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "Simple Linear Regression",
                    "code_or_text": "from sklearn.linear_model import LinearRegression\nimport numpy as np\n\n# Training data: hours studied → exam score\nX = np.array([[1], [2], [3], [4], [5]])\ny = np.array([50, 60, 70, 80, 90])\n\nmodel = LinearRegression()\nmodel.fit(X, y)\n\n# Predict score for 6 hours of study\nprediction = model.predict([[6]])\nprint(f'Predicted score: {prediction[0]:.0f}')  # ~100",
                    "language": "python",
                    "explanation": "A simple supervised learning model that predicts exam scores based on study hours.",
                }
            ],
            "quiz": [
                {
                    "question": "Which type of ML uses labeled training data?",
                    "type": "mcq",
                    "options": [
                        "Supervised Learning",
                        "Unsupervised Learning",
                        "Reinforcement Learning",
                        "Transfer Learning",
                    ],
                    "correct_answer": "Supervised Learning",
                    "explanation": "Supervised learning trains on labeled input-output pairs to learn a mapping function.",
                },
                {
                    "question": "What is the key difference between traditional programming and machine learning?",
                    "type": "short_answer",
                    "correct_answer": "In ML the model learns rules from data, while traditional programming requires manually coding rules",
                    "explanation": "Traditional: Input + Rules → Output. ML: Input + Output → Rules.",
                },
            ],
            "skill_tags": ["ml-ai", "data-science"],
            "prerequisites": ["Basic Python", "Basic statistics"],
        },
    },
]


DEMO_USERS = [
    {"name": "Aman (You)", "email": "aman@demo.makesense", "level_xp": 0},
    {"name": "Priya S.", "email": "priya@demo.makesense", "level_xp": 500},
    {"name": "Rahul K.", "email": "rahul@demo.makesense", "level_xp": 1200},
]


async def seed():
    """Seed the database with demo data."""
    conn = await get_connection()
    print("Connected to database.")

    try:
        # --- Users ---
        user_ids = []
        for u in DEMO_USERS:
            row = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", u["email"]
            )
            if row:
                uid = row["id"]
                print(f"  User '{u['name']}' already exists (id={uid})")
            else:
                uid = await conn.fetchval(
                    """INSERT INTO users (name, email, created_at)
                       VALUES ($1, $2, NOW()) RETURNING id""",
                    u["name"],
                    u["email"],
                )
                print(f"  Created user '{u['name']}' (id={uid})")

                # Set gamification XP if columns exist
                try:
                    await conn.execute(
                        "UPDATE users SET total_xp = $1 WHERE id = $2",
                        u["level_xp"],
                        uid,
                    )
                except Exception:
                    pass  # gamification columns may not exist yet

            user_ids.append(uid)

        demo_user_id = user_ids[0]  # "Aman" is the primary demo user

        # --- Topics & Lessons ---
        for lesson_data in DEMO_LESSONS:
            topic_id = f"topic_{uuid.uuid4().hex[:12]}"
            email_hash = hashlib.sha256(
                DEMO_USERS[0]["email"].encode()
            ).hexdigest()

            # Check if topic already seeded
            existing = await conn.fetchrow(
                "SELECT id FROM topics WHERE raw_topics @> $1::text[]",
                [lesson_data["topic"]],
            )
            if existing:
                print(f"  Topic '{lesson_data['topic']}' already seeded")
                continue

            await conn.execute(
                """INSERT INTO topics (id, user_id, name, email, email_hash, raw_topics, categories, status)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, 'completed')""",
                topic_id,
                demo_user_id,
                DEMO_USERS[0]["name"],
                DEMO_USERS[0]["email"],
                email_hash,
                [lesson_data["topic"]],
                [lesson_data["category"]],
            )

            lesson_id = f"lesson_{uuid.uuid4().hex[:12]}"
            content = lesson_data["content"]

            await conn.execute(
                """INSERT INTO lessons (id, topic_id, title, summary, content, difficulty,
                   estimated_time_minutes, skill_tags, prerequisites, status)
                   VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, 'generated')""",
                lesson_id,
                topic_id,
                content["title"],
                content["summary"],
                json.dumps(content),
                lesson_data["difficulty"],
                content.get("estimated_time_minutes", 15),
                content.get("skill_tags", []),
                content.get("prerequisites", []),
            )
            print(f"  Seeded lesson: {content['title']} (id={lesson_id})")

        # --- Feedback ---
        lessons = await conn.fetch("SELECT id, title FROM lessons LIMIT 10")
        for i, lesson in enumerate(lessons):
            fb_id = f"fb_demo_{uuid.uuid4().hex[:8]}"
            try:
                await conn.execute(
                    """INSERT INTO feedback (id, user_id, lesson_id, feedback_type, comment, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT DO NOTHING""",
                    fb_id,
                    user_ids[i % len(user_ids)],
                    lesson["id"],
                    "up" if i % 3 != 2 else "down",
                    f"Great lesson on {lesson['title']}!" if i % 2 == 0 else None,
                    datetime.now() - timedelta(days=i),
                )
            except Exception:
                pass

        print("\n✅ Demo data seeded successfully!")
        print(f"\n📋 Demo user email: {DEMO_USERS[0]['email']}")
        email_hash = hashlib.sha256(
            DEMO_USERS[0]["email"].encode()
        ).hexdigest()
        print(f"📋 Library URL: http://localhost:8000/library.html?user={email_hash}")
        print(f"📋 Dashboard: http://localhost:8000/app/")
        print(f"📋 API docs: http://localhost:8000/docs")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
