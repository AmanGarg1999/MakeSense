# MakeSense — Architecture

Describes the repository as it exists on `main`. Every path mentioned here is
verified against the tree. Where a component is *planned* (vision docs) but not
yet in the tree, it is marked as such so nobody hunts for code that isn't there.

## Product shape

MakeSense is an adaptive AI-mentored learning platform: a learner states a goal,
the AI Mentor profiles them and proposes learning pathways, lessons are generated
just-in-time, skills are verified via quizzes and evidence-based assessment, and
a 3D skill-tree (Three.js constellation) visualizes progress. Gamification
(XP, streaks, achievements, spaced review) wraps the whole loop.

High-level product rationale lives in:
- `README.md` — quick start and feature overview
- `docs/learning-loop-vision.md` — the learning-loop product vision
- `docs/learning-path-architecture.md` — 3D skill-tree, graph topology, and core DB schema
- `docs/research/skill-verification.md` — LL-01 verification research grounding
- `docs/user-flow.md`, `docs/launch-plan.md` — user flow and launch planning

## Repository layout (monorepo, single git tree)

```
server/            FastAPI backend (primary application)
frontend/          Vite + React 19 PWA (the web app)
gamification/      Python gamification engine (routers, XP rules, jobs)
packages/          Python/JS packages
  assessment/        LL-05 skill verification engine
  browser-extension/ Chrome extension (manifest v3)
packs/             Content-pack pipeline
  build/             NCERT -> mspack build scripts
  dist/              Signed, encrypted .mspx pack artifacts
services/
  event-tracker/   Standalone FastAPI telemetry service (Redis + Prometheus)
data/              JSON data files (topics/feedback/analytics; legacy static serving)
schemas/           JSON Schemas for feedback/topic submissions
scripts/           Operational + generation scripts, pytest suite in scripts/tests/
server/migrations/ SQL migrations (PostgreSQL)
docs/              Vision, research, acceptance docs
demo/              Seed data script (demo/seed_demo_data.py)
cypress/           E2E browser tests (cypress/e2e/gamification.cy.js)
n8n/               n8n workflow deployment compose files
templates/         HTML email/content templates
generated-content/ Sample generated lessons (md/html/pdf)
src/               Legacy vanilla-JS admin/feedback pages (pre-React)
.github/workflows/ CI: content generation, email notification, feedback/survey handlers, weekly analytics
quality_check.py   Aggregated quality-gate runner (see "Quality gates" in CONTRIBUTING.md)
Dockerfile         python:3.11-slim image running the FastAPI server
docker-compose.yml db (postgres:16-alpine) + api
```

There is currently **no** `apps/mobile` (Expo) or `packages/ai-core|sync|curriculum|cloud-api`
in the tree. A React-Native/Expo app and a Yjs/WatermelonDB offline-sync layer are
discussed as future work in `docs/learning-loop-vision.md` (e.g. its WatermelonDB
reference in the parallel-tracks table) but are **not implemented** anywhere in this
repo yet. Do not reference them as existing code.

## Backend — `server/`

- **Entry point**: `server/main.py` — FastAPI app (`MakeSense API`, v1.0.0).
  Lifespan hook initializes the asyncpg pool and runs migrations.
- **Routers** (mounted under `/api` in `server/main.py`):
  `topics.py`, `content.py`, `quiz.py`, `feedback.py`, `paths.py` (learning paths,
  prefix `/api/paths`), `streaks.py`, `achievements.py`, `reviews.py` — plus the
  gamification router from `gamification/api.py` (best-effort import).
- **Config**: `server/config.py` (pydantic-settings, `.env` via `.env.example`).
  Key settings: `database_url` (PostgreSQL), `llm_provider`
  (`runanywhere` default → `runanywhere_endpoint`, an OpenAI-compatible local
  endpoint; `gemini_api_key` for Google Gemini), `cors_origins`, `secret_key`.
- **DB access**: `server/database.py` — asyncpg pool; `run_migrations()` applies
  `.sql` files from **both** `gamification/migrations/` and `server/migrations/`,
  sorted by filename, tracked in a `schema_migrations` table. Migration number
  space is shared between the two directories.
- **Generation engines**: `server/content_generator.py` (lesson generation via
  RunAnywhere SDK endpoint / Gemini API / template fallback) and
  `server/path_generator.py`; LLM prompt assets in `server/prompts/`.

### Inference / model serving

The repo has no bundled model weights or inference-loader package. Model
inference is delegated to an **external OpenAI-compatible endpoint** configured
by `llm_provider`/`runanywhere_endpoint` (`server/config.py`) and, for the
assessment engine, `ASSESS_LLM_BASE_URL`/`ASSESS_LLM_MODEL` (default is a
Tailscale IP, `packages/assessment/README.md`). The fleet convention is that
large artifacts (models, pack signing keys) live in the DGX artifact store and
are reached over the tailnet — they are deliberately **not** committed here.
`scripts/tests/test_inference.py` and `scripts/llm_probe.py` exercise those
endpoints; they are not an on-device loader implementation.

## Frontend — `frontend/`

Vite + React 19 SPA/PWA (`frontend/package.json`):
- Pages: `frontend/src/pages/` — `Dashboard.jsx`, `LearningPathView.jsx`,
  `LessonViewer.jsx`, `QuizPage.jsx`, `ReviewDeck.jsx`.
- Components: `frontend/src/components/` — including `LearningPathTree3D.jsx`
  (Three.js constellation), `MentorProfilingModal.jsx`, XP/gamification widgets.
- `frontend/src/hooks/useApi.js` — API client.
- PWA: `frontend/public/manifest.json`, `frontend/public/sw-template.js`
  (Workbox; `npm run generate-sw`), dev server on :5173.
- Built assets (`frontend/dist`) are served by the FastAPI app when present
  (mounts for `/assets`, `/icons`, PWA root files in `server/main.py`).
- Storybook config in `frontend/.storybook`.

Legacy non-React admin pages live at repo root (`index.html`, `library.html`,
`admin-dashboard.html`, `app.js`) and in `src/` (`admin.js`, `feedback.js`).
They are served statically / kept for compatibility, not the primary UI.

## Sync / offline story

**No Yjs CRDT and no WatermelonDB implementation exists in this repo yet.**
Today's "offline" surface is the browser PWA service worker (Workbox cache)
built from `frontend/public/sw-template.js`, plus the SQLite-free server
database path. Offline-sync validation in `quality_check.py` looks for
`scripts/tests/test_offline_scenarios.py`, which does not exist on `main` —
so that gate fails until the sync subsystem (planned per
`docs/learning-loop-vision.md`) lands. When a real sync layer is added, document
it here.

## Content packs — `packs/`

Encrypted curriculum artifacts ("mspack" schema v0 envelope: AES-256-GCM,
HKDF-SHA256; a dev key is used unless `MS_MASTER_KEY` is set):
- Build pipeline (see `packs/build/README.md`):
  `packs/build/extract_build_src.py` (NCERT PDF → `pack-src/` manifest + JSON
  content) → `packs/build/embed.py` (all-MiniLM-L6-v2, 384-dim normalized
  embeddings → `index/embeddings.npz`) → `mspack build` →
  `packs/build/sign_validate.py` (schema validation + sha256 signature +
  license metadata).
- Artifacts and signatures ship in `packs/dist/`
  (e.g. `cbse-class9-10-math-science-1.0.0.mspx`, `.sha256`, `.sig.json`,
  `license.json`, `manifest.verify.json`; CC-BY-NC-SA-4.0).
The `mspack` CLI itself is external tooling (DGX/fleet side), not in this repo.

## Gamification — `gamification/`

Self-contained Python package merged into the main API:
- `gamification/engine.py`, `gamification/skills.py`, `gamification/api.py`
  (router, `/api` prefix), config in `gamification/config/points_rules.yaml`.
- Migrations: `gamification/migrations/` (base users, schema, seed).
- Scheduled job: `gamification/jobs/nightly_skill_update.py`.
- Tests: `gamification/tests/` and `gamification/test_*.py`.

## Assessment engine — `packages/assessment/`

LL-05 skill verification (see its `README.md` for the module map):
`evidence.py`, `rubric.py` + `schemas/`, `probes.py`, `registry.py`
(append-only verification registry backed by
`server/migrations/008_verification_registry.sql`), `expiry.py` (mastery-decay
clock), `verifier.py` (orchestration), `capture.py` (multimodal adapters),
`llm_client.py`. Integrity rules: performance-grade rungs cannot pass on
explain-only evidence; AI-detector output never is a verdict.

## Event tracking — `services/event-tracker/`

Independent FastAPI service with Redis buffering and Prometheus metrics
(`services/event-tracker/app/main.py`, own `Dockerfile` and `tests/`). Not part
of the root docker-compose; deploy separately.

## Automation — `.github/workflows/`, `n8n/`, root monitors

Workflows: `content-generator.yml` (regenerates content on `data/topics.json`
changes), `email-notification.yml`, `feedback-handler.yml`, `survey-handler.yml`,
`weekly-analytics.yml`. `n8n/` holds compose files for n8n deployments. Root
`simple_monitor.py` / `monitor_cycle.py` and `scripts/` kanban monitors are
operational helpers (see `MONITORING_PROTOCOL.md`); `audit/scan_secrets.py` is
the secret-scanning entry point.

## Data & persistence

- PostgreSQL 16 (docker-compose service `db`, volume `pgdata`). Core tables and
  3D node schema are documented in `docs/learning-path-architecture.md`;
  incremental schema lives in the two migration directories above.
- JSON files under `data/` are legacy static/serving fixtures, also the trigger
  path for the content-generation workflow.

## Running locally

```bash
cp .env.example .env          # optionally set GEMINI_API_KEY
docker compose up --build     # postgres on 5432, API on 8000 (serves frontend too)
# or frontend dev:
cd frontend && npm install && npm run dev   # Vite on :5173
```
