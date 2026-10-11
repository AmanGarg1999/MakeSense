# packages/assessment — LL-05 Skill Verification Engine

Implements the verification loop from `docs/learning-loop-vision.md` §2.7 using the
research grounding in `docs/research/skill-verification.md` (LL-01):

| Module | Responsibility |
|---|---|
| `evidence.py` | Evidence intake for all submission types (code-that-executes, audio/video, photo of physical work, project repo, in-app performance capture, explanation). Schema-level enforcement: a rung whose evidence type is **performance** cannot pass on explain-only (`schemas/evidence_submission.json`). Multimodal capture (camera OCR / handwriting / ASR) is injected via `capture.py` adapters (mk-019). |
| `rubric.py` + `schemas/rubric.json` | Analytic rubric schema (criteria / levels / anchors) + prompt-versioned model-assisted scorer with per-criterion rationale, confidence, and evidence citations. Human-escalation band around the pass threshold. |
| `probes.py` | Transfer-test generation (novel-context applications) and oral-defense (explain-your-artifact, perturbation) probes — anti-impostor-completion per LL-01 §3. |
| `registry.py` + `server/migrations/008_verification_registry.sql` | Append-only verification registry: skill, level, evidence refs, rubric scores, verifier, timestamps, expiry, re-check history. DB triggers + API both reject UPDATE/DELETE. Feeds the LL-06 recap schedule. |
| `expiry.py` | Mastery-decay clock per LL-01 §9 (per-family first/steady intervals, SM-2-style ×2.5 expansion with family ceiling/floor) → `current` / `stale` / `expired`; expired rungs produce re-verify task payloads for the loop. |
| `verifier.py` | End-to-end orchestration: intake → integrity check → score → verdict → registry append, incl. the LL-01 §3.3 escalation ladder (artifact → defense → in-session re-creation → provisional flag). |

## Integrity rules encoded

1. **No pass from explain-only** when the rung's evidence types are performance-grade —
   enforced twice: in the JSON Schema (`if/then` on `rung_evidence_types` →
   `evidence_required: true`) and in `verifier.grade_submission`.
2. AI-detector output is never a verdict — it only raises the escalation rung (§3.1).
3. Lapse downgrades to `provisional`, never deletes (append-only history).

## Scoring model

`verifier.py` takes a `ModelClient` (`complete(system, user) -> str`). Defaults to the
repo's OpenAI-compatible endpoint via env:
`ASSESS_LLM_BASE_URL` (default `http://100.72.85.102:18300/v1`), `ASSESS_LLM_MODEL`
(default `qwen3.8-flash-next`). Tests inject a fake client; the live acceptance run
(`scripts/assess_sample_run.py`) uses the real model.
