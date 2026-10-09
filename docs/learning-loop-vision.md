# MakeSense Learning Loop — Product Vision & Architecture (v1)

**Owner:** huntingvision · **Drafted by:** dwight (Chief of Staff) · **Date:** 2026-10-09
**Status:** Approved direction — implementation split into LL-01..LL-08 on the `makense` Kanban board.

---

## 1. Core idea

MakeSense is not a content library — it is a **learning companion** that runs a continuous
loop for every skill a user is pursuing, **several skills in parallel**, until each stated
goal/level is reached. The loop:

```
        ┌────────────────────────────────────────────────────┐
        │                                                    │
  DISCOVER → MAP → GATHER → PERSONALIZE → DELIVER → VERIFY   │
        │                                          │         │
        └────────────── ADAPT ◄────────────────────┘         │
                       (feedback every step feeds the next)  │
                                                             │
                    RETAIN (spaced recap) ────────────────────┘
```

## 2. The eight loop stages

### 2.1 Silent onboarding (engage without interrogating)
- Ask **the minimum viable questions**: what they want to learn + their goal level
  (hobby / job-ready / expert). Everything else is **inferred, not asked**:
  - diagnostic micro-activities at the start of a topic ("try this, don't worry about being wrong")
  - skill-graph inference from what they ask, skip, get right, dwell on
  - existing skills detected through portfolio/import (mk-030) or one-tap GitHub/LinkedIn link
- Rule of thumb encoded in the coach: **if the system can infer it, never ask it.**
- Questions appear contextually *inside* the learning flow, not as a form wall.

### 2.2 Parallel skill tracks
- A user can run N tracks (e.g. "Guitar – intermediate" + "Python – beginner") at once.
- Each track = its own skill graph, mastery vector, batch schedule, and coach narrative.
- A cross-track dashboard shows all journeys; the companion arbitrates pacing so the user
  isn't overwhelmed (suggests focus weeks, interleaves when energy is low).

### 2.3 Skill mapping & levels
- Every topic expands into a **categorized skill ladder**: levels (novice→competent→
  proficient→expert), each with named sub-skills, prerequisites (from the competency KG,
  mk-008) and observable "can do" statements.
- Levels are **goal-relative**: "learn photography for Instagram" ≠ "learn photography
  for wedding work" → different ladders from the same skill graph.

### 2.4 Content discovery & tagging (anti-hallucination contract)
- Continuously gather from the existing pipeline: NCERT/DIKSHA/Khan/NPTEL/OCW/OpenStax/
  Wikipedia/arXiv scrapers + web search + video→transcript.
- Every item is **stored in the central knowledge DB** (already built for Personal
  Finance/Guitar packs) with: source URL, capture date, license, extraction method,
  verbatim-span/quote evidence, Bloom level, skill tags.
- **Claim-level citations**: generated learning material must trace to tagged source
  items; unsupported claims are dropped. Unverified facts flagged, never silently asserted.
- Skills are **extracted** from content (what does mastering this item enable?) and linked
  into the skill graph — content and skills index each other bidirectionally.

### 2.5 Personalized formulation
- Per user: level + prior mastery + reading level + language + device constraints +
  interests feed the prompt templates (MVP-02b) to reformulate tagged content into
  *their* explanation, examples, and practice set. Same underlying verified facts,
  different wrapping. Interests from other active tracks become example domains
  (teach recursion with their guitar-fretboard analogy).

### 2.6 Active vs passive delivery (the engagement dial)
- **Passive:** read/watch/explain — for intake-heavy stretches and low-energy windows.
- **Active:** predict-before-reveal, retrieval prompts, mini-tasks, "teach it back",
  project steps — for consolidation.
- The loop **checks in on the mode it chose**: if passive segments correlate with drop-off
  or failed later retrieval, it flips to active for that skill. Learner-activity-level
  research (Kulik's synthesis, Dunlosky's desirable-difficulty tiers) supports active
  retrieval >> passive re-reading for retention — the default is active with passive as
  a deliberate scaffold.
- The companion narrates the journey ("you're 3 sessions from being able to…") —
  motivation science: competence + autonomy + relatedness framing.

### 2.7 Verification (the hard research problem — LL-01)
- **A practical skill cannot be verified by a theoretical explanation.** Ladder endpoints
  are *performances*, not quizzes:
  - *doing tasks* in a simulated or real environment (code that runs, a recording, a photo,
    a built object, a conversation)
  - evidence upload with structured **rubric scoring** (checklist + anchors, human- or
    model-assisted)
  - **oral defense** variants: explain-why-your-artifact-works (guards against impostor
    completions)
  - **transfer tests**: apply in a novel context, not the practiced one
  - **staggered re-verification**: mastery expires — verified skills get a decay clock;
    recap sessions and spot re-checks keep verification *up to date*
- LL-01 (research card) produces the evidence taxonomy + per-skill-domain verification
  catalog before LL-04 (implementation) freezes its schema.

### 2.8 Progress, gaps, feedback
- Continuous: mastery deltas, stuck detection (2 failed attempts → change strategy, not
  repeat), improvement narratives (mk-027 skill radar), what-they-learnt vs what-they-lack
  in plain language. Feedback loop (thumbs + error patterns) feeds prompt improvement
  already wired in MVP-13.

## 3. Structure for engagement (packaging the loop)

- **Skill batches:** topics chunked into coherent weekly-ish batches (existing pack format).
- **Levels:** visible ladder progress per track.
- **Side quests:** optional enrichments off the main path (a tool, a tangent topic, a
  micro-project) — completion feeds mastery but never gates the main line. This is where
  **constantly-changing interests** get absorbed: interests are captured from behavior and
  offered as side quests rather than derailing the goal.
- **Stores:** the persistent inventories the loop maintains — knowledge DB, skill graph,
  mastery ledger, verification registry, recap schedule. All append-only with provenance.
- **Recap/review:** user-initiated ("take me back through X") + interval-driven
  (spaced-repetition schedule generated from the mastery ledger; Leitner/SM-2 style
  buckets, tuned per skill decay rate from verification results).

## 4. Modes of learning the same thing
One skill, many doors (interest-driven routing to the same verification endpoint):
- **Guided learning** — step-by-step coach path (default for novices)
- **Project-together** — build a real artifact side-by-side; curriculum derived backwards
  from the project (default for intermediate/employable goals)
- **Explore & explain** — content-first with coach interruptions
- **Drill & verify** — retrieval-heavy mode before verification checkpoints

## 5. Mapping to existing system
| Loop stage | Reuses | Gap to build |
|---|---|---|
| Silent onboarding | survey pipeline, mk-030 portfolio | inference-first onboarding flow (LL-03) |
| Parallel tracks | WatermelonDB schema, packs | multi-track state + cross-track dashboard (LL-02) |
| Skill mapping | competency KG (mk-008) | goal-relative ladders, "can-do" DB (LL-02) |
| Gather & tag | 8 scrapers, knowledge DB, licensing | skill-extraction indexer (LL-02/05) |
| Personalize | prompts (MVP-02b), feedback loop | learner-profile conditioning (LL-03) |
| Delivery dial | course player, PWA | mode controller + session telemetry (LL-04) |
| Verification | assessment (mk-021/22), OCR/camera | rubric+artifact verification engine (LL-04/05) |
| Recap | coach insights | spaced-recap scheduler (LL-06) |
| Side quests/stores | gamification (mk-028) | quest engine + registry stores (LL-07) |
| Future paths | career engine (mk-031) | interest-drift router (LL-08) |

## 6. Non-negotiables
1. Never ask what can be inferred.
2. Never state a fact without a traceable, tagged source.
3. Never mark a practical skill verified from explanation alone.
4. Verification has an expiry; the loop re-checks.
5. The main path is the user's stated goal; drifting interests become side quests, never derailment.
6. Companion voice: encouraging, specific, honest about gaps — no generic praise.
