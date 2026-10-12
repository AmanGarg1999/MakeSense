# Contributing to MakeSense

## Ground rules

- **Default branch**: `main`. All work lands there via pull requests; never push
  directly to `main`.
- **Code lives in one monorepo** (see `ARCHITECTURE.md`). Keep changes scoped to
  the subsystem you're touching; shared surfaces (DB migrations, `server/main.py`
  router mounting, `quality_check.py`) are collision hotspots — coordinate first.

## Branching and worktrees

- Branch naming used by this team: `<loop-id>/<task-id>` (e.g.
  `ll-05/t_048aa2b7`) or a short feature slug. One branch = one PR.
- **Worktree rule**: the long-lived shared checkout(s) of this repo are usually
  *dirty* (other agents' uncommitted work in flight). Never work in, reset, or
  stash a shared tree you don't own. Create your own worktree from a freshly
  fetched `origin/main`:

  ```bash
  git fetch origin main
  git worktree add ../<task-slug> -b <your-branch> origin/main
  ```

  Do all edits, commits, and pushes from your own worktree, then
  `git worktree remove` it when the PR merges. Stacked PRs: branch from the
  previous PR's tip and say so in the PR body.

## Migrations

SQL migrations go in `server/migrations/` or `gamification/migrations/` and are
applied alphabetically-by-filename at server startup (`run_migrations()` in
`server/database.py`, tracked in `schema_migrations`). The numbering space is
shared — claim the next free `NNN_` prefix against `origin/main` before naming
your file, and make migrations idempotent or accept they run exactly once.

## Testing

Python (pytest) — from the repo root:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r server/requirements.txt
pytest gamification/tests/ packages/assessment/tests/ scripts/tests/ -v
python3 server/test_imports.py        # import smoke test used by the gate
```

Notes:
- `scripts/tests/` contains a mix of real schema tests (`test_correct_schema.py`
  — the one the quality gate runs) and endpoint-probe scripts that need a live
  LLM/inference endpoint; expect those to skip/fail without one.
- `packages/assessment/tests/` runs hermetically with an injected fake LLM
  client; the live acceptance run is `scripts/assess_sample_run.py`.
- Frontend: `cd frontend && npm install && npm run build` must succeed
  (Vite + Workbox SW). `npm test` is currently a placeholder (Vitest not wired).
- E2E: `npx cypress run` against a running stack (`cypress/e2e/`).
- Event-tracker service has its own tests: `pytest services/event-tracker/tests/`.

Any user-facing behavior change needs a test in the matching suite; bug fixes
need a regression test.

## Quality gates

`quality_check.py` (repo root) is the aggregate gate — it writes
`quality_results.json` and checks: pytest `scripts/tests/test_correct_schema.py`,
server imports, model artifacts, content packs in `packs/dist/`, frontend build,
sync tests, security placeholder, accessibility placeholder, and that
`ARCHITECTURE.md` + `CONTRIBUTING.md` exist at the repo root. Several checks are
known-failing placeholders today (device testing, offline verification,
security audit, accessibility) — see REM-4; do not silence them, fix them.

⚠️ `quality_check.py` currently hardcodes absolute paths under a specific
machine's shared workspace (`/home/huntingvision/workspace_drive/workspaces/MakeSense`).
Running it inside a worktree checks that *other* tree. If you touch it, prefer
deriving paths from `Path(__file__).parent`.

CI (`.github/workflows/`) covers content generation, email/notification and
feedback/survey handling, and weekly analytics — not a PR test gate. So **tests
must pass locally before requesting review**; a green PR diff is your
responsibility, not the runner's.

## Security

- Never commit secrets, API keys, model weights, or pack signing keys
  (`MS_MASTER_KEY` and DGX artifact-store material stay out of git).
  `audit/scan_secrets.py` is the repo scanner — run it before pushing diffs that
  touch config, `.env*`, or `packs/`.
- `.env.example` documents env vars; keep it in sync when adding settings to
  `server/config.py`.

## Content packs

Pack rebuilds follow `packs/build/README.md` (extract → embed → mspack build →
verify/sign). Commit rebuilt artifacts to `packs/dist/` with their `.sha256` and
`.sig.json`, and keep `license.json` accurate (CC-BY-NC-SA-4.0 for NCERT-derived
packs).

## Pull requests

1. `git fetch origin main` and rebase/merge `main` in before opening.
2. PR title: `feat|fix|chore|docs(<area>): <summary>` (repo convention).
3. Body: what changed, how it was verified (commands + results), linked task id.
4. Small PRs review faster; if a change is inherently cross-cutting, call out
   the touched shared files up front.
