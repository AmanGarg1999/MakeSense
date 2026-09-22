# 🧠 MakeSense

**An adaptive AI-mentored learning platform with 3D skill tree visualization and gamification.**

Tell MakeSense what you want to learn → AI Mentor profiles your needs & proposes 3 tailored pathways → Explore your living 3D Constellation (Three.js) → Learn with just-in-time generated lessons → Verify skills with quizzes → The skill tree dynamically expands and injects remedial reinforcement as you progress.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) [Google Gemini API key](https://makersuite.google.com/app/apikey) for AI-generated content

### 1. Clone & Configure

```bash
git clone https://github.com/AmanGarg1999/MakeSense.git
cd MakeSense
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY (optional — works without it using templates)
```

### 2. Start the Platform

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** database on port 5432
- **FastAPI** server on port 8000 (serves both API and frontend)

### 3. Open in Browser

| Page | URL | Description |
|------|-----|-------------|
| **Home** | [localhost:8000](http://localhost:8000) | Submit learning topics |
| **Library** | [localhost:8000/library](http://localhost:8000/library.html) | Access your generated lessons |
| **Dashboard** | [localhost:8000/app](http://localhost:8000/app/) | Gamification dashboard (XP, skills, leaderboard) |
| **Admin** | [localhost:8000/admin](http://localhost:8000/admin-dashboard.html) | Feedback analytics |
| **API Docs** | [localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation |

### 4. Seed Demo Data (Optional)

```bash
python demo/seed_demo_data.py
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Browser (Client)                         │
│  Survey Form │ Content Library │ Live Studio │ Dashboard     │
└──────────┬───────────┬──────────────┬──────────────┬─────────┘
           │           │              │              │
           ▼           ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Server (localhost:8090)                 │
│                                                              │
│  /api/submit          → Topic submission & auto-classify     │
│  /api/generate/stream → Real-time SSE on-device generation   │
│  /api/lessons         → Structured lesson content + quizzes  │
│  /api/quiz/submit     → Server-side grading + XP awards      │
│  /api/users           → Gamification profiles & leaderboard  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │               RunAnywhere AI Engine                 │     │
│  │  - On-Device Local LLM (Llama 3.2 / Qwen 2.5)       │     │
│  │  - Zero Cloud Costs, Full Offline Privacy           │     │
│  │  - Real-time token streaming via Server-Sent Events │     │
│  │  - Cloud Gemini & Educational Fallback Adapters     │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         PostgreSQL 16 (Users, Lessons, Skills,      │     │
│  │         Achievements, Quiz Attempts, Feedback)      │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## The Learning Loop

1. **Discover** → Submit topics you want to learn about
2. **Generate** → AI creates a structured lesson (explanation + examples + quiz)
3. **Learn** → Read the interactive lesson with code examples
4. **Practice** → Take the embedded quiz, get instant feedback
5. **Progress** → Earn XP, level up, see your skill ratings improve
6. **Review** → Dashboard shows streaks, skills, and leaderboard ranking

## Project Structure

```
MakeSense/
├── server/                    # FastAPI backend
│   ├── main.py                # App entry point, static file serving
│   ├── config.py              # Environment configuration
│   ├── database.py            # asyncpg pool + migration runner
│   ├── content_generator.py   # AI content generation (Gemini/template)
│   ├── routers/
│   │   ├── topics.py          # Topic submission API
│   │   ├── content.py         # Lesson generation & retrieval
│   │   ├── quiz.py            # Quiz submission & scoring
│   │   └── feedback.py        # User feedback API
│   ├── migrations/
│   │   └── 003_topics_and_lessons.sql
│   └── prompts/
│       └── lesson_prompt.py   # LLM prompt templates
├── gamification/              # XP, levels, skills, achievements
│   ├── engine.py              # Points & leveling engine
│   ├── skills.py              # Bayesian skill rating system
│   ├── api.py                 # Gamification REST API
│   ├── migrations/
│   │   ├── 000_base_users.sql
│   │   ├── 001_gamification_schema.sql
│   │   └── 002_seed_data.sql
│   └── config/
│       └── points_rules.yaml  # XP reward configuration
├── frontend/                  # React 19 + Vite SPA
│   ├── src/
│   │   ├── App.jsx            # Router (Dashboard, Lesson, Quiz)
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx  # XP, skills, leaderboard
│   │   │   ├── LessonViewer.jsx
│   │   │   └── QuizPage.jsx
│   │   ├── components/
│   │   │   ├── LevelBadge.jsx
│   │   │   ├── XPProgressBar.jsx
│   │   │   ├── SkillTagsCloud.jsx
│   │   │   └── PointsHistoryChart.jsx
│   │   └── hooks/
│   │       └── useApi.js
│   └── package.json
├── index.html                 # Survey form (landing page)
├── app.js                     # Form submission logic
├── library.html               # User content library
├── styles.css                 # Global CSS design system
├── scripts/
│   ├── generate-content.py    # CLI content generation
│   └── categorize.py          # Topic classification
├── docker-compose.yml         # One-command dev environment
├── Dockerfile
└── .env.example
```

## API Reference

### Topics
- `POST /api/submit` — Submit learning topics `{name, email, topics[]}`
- `GET /api/topics` — List topics (filter by `?user=<sha256_hash>`)
- `GET /api/topics/{id}` — Get topic with generated lessons

### Content
- `POST /api/generate/{topic_id}` — Trigger AI content generation
- `GET /api/lessons/{id}` — Get full lesson content
- `GET /api/lessons/{id}/quiz` — Get quiz questions

### Quiz & Feedback
- `POST /api/quiz/submit` — Submit answers, get scoring + XP
- `POST /api/feedback` — Submit thumbs up/down rating
- `GET /api/feedback/all` — Admin: all feedback data

### Learning Paths & 3D Constellations
- `POST /api/paths/preview-options` — Compare 3 tailored educational pathways (Fast-Track, Architect, Project Builder)
- `POST /api/paths/curate` — Curate and launch 3D learning path DAG with mentor guidance
- `GET /api/paths` — List recent learning paths with completion rates
- `GET /api/paths/{id}` — Retrieve 3D graph, milestone nodes, spatial coordinates & status
- `POST /api/paths/{id}/nodes/{node_id}/unlock` — Just-in-time generation of lesson content when entering a node
- `POST /api/paths/{id}/nodes/{node_id}/complete` — Evaluate quiz score, unlock downstream branches, and inject remedial nodes on friction (<70%)

### Gamification
- `GET /api/users/{id}/profile` — User level, XP, points breakdown
- `GET /api/users/{id}/skills` — Skill proficiency ratings
- `GET /api/users/{id}/points` — Points history
- `GET /api/leaderboard` — Weekly/monthly rankings

## Development

### Local Development (without Docker)

```bash
# Start PostgreSQL locally
# Set DATABASE_URL in .env

# Install Python dependencies
pip install -r server/requirements.txt

# Run the server
uvicorn server.main:app --reload --port 8000

# (Optional) Build React frontend
cd frontend && npm install && npm run build
```

### Running Tests

```bash
pip install pytest pytest-asyncio
python -m pytest gamification/tests/ -v
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML/CSS/JS (static pages) + React 19 + Vite (SPA) |
| Backend | Python 3.11, FastAPI, asyncpg |
| Database | PostgreSQL 16 |
| AI | Google Gemini API (with template fallback) |
| Gamification | Custom Bayesian skill engine, XP leveling |
| Deployment | Docker Compose |

## License

MIT License — feel free to use and modify.