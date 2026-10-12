# LL-06 acceptance — spaced recap/review subsystem + on-demand rewind

Date: 2026-10-12 (UTC). Branch: `ll-06/t_d1d62ba2`.

## What was built

| Piece | File(s) |
|---|---|
| Leitner/SM-2 spaced recap scheduler, seeded from mastery ledger + LL-05 verification expiry, per-family growth tuned by observed recall success, append-only state in the LL-07 `recaps` stream | `ll06/scheduler.py` |
| "Take me back through X" — retrieval-first rewind digest (questions before answers) from knowledge DB + what the user did/missed, with citations | `ll06/digest.py` |
| Recap outcomes: mastery-ledger update, verification-currency extend/reset, stuck/gap routing into LL-04 delivery (flip active mode / re-teach prerequisite — never repeat-the-card) | `ll06/outcomes.py` |
| API surface `/api/recap/{user}/due|submit|rewind` | `server/routers/recap.py`, wired in `server/main.py` |
| Due-item surfacing: dashboard RecapCard (low-effort wins, XP framing) + /recap session page (queue + rewind box) | `frontend/src/components/RecapCard.jsx`, `frontend/src/pages/RecapSession.jsx`, routes in `App.jsx`/`Dashboard.jsx` |

## Acceptance evidence

- Scheduler unit tests (interval growth/reset math, seeding, expiry override, warm-restart idempotency, rehydration): `tests/test_ll06_recap.py` — 22 tests.
- API surfacing through the real router + file-backed store: `tests/test_ll06_api.py` — 4 tests (due shape, submit clears due window + updates currency, 404 on unknown skill, rewind digest shape).
- Full suite: **42 passed** (`python -m pytest tests/ -q`).
- JSX front-end files parse (esbuild); routes registered in `App.jsx`/`Dashboard.jsx`.
- Generated recap digest for a seeded user (guitar track, 3 skills, 1 lapse gap, 3 knowledge-DB citations): `recap_digest.json`; the due/upcoming schedule fed to the home surface: `schedule.json`.
  - Regenerate: `python scripts/demo_ll06.py`.
- Stuck/gap signal: the seeded lapse surfaces as a `gap_requestion` routed `ll04_active_mode` in the digest (see `sections[].gaps[].route`) and as `delivery_route` in submit results.

## Fixes landed during this run (found by the demo, locked by regression tests)

1. Seed precedence compared `seq` across different store tables — per-table counters, so a mastery row could mask a verified rung's expiry clock. Now source-based: any verification event seeds from the LL-05 expiry of its latest row (`test_verification_expiry_wins_even_with_newer_mastery_event`).
2. Rewind query matching ignored tracks whose skill tags are abbreviated (`g:strum` under track `guitar-hobby`). Matching now also consults the event's `track_id` — no loose namespace-prefix heuristic (`test_rewind_query_matches_via_track_membership`).
