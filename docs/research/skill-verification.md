# LL-01 — Practical Skill Verification & Mastery Re-Verification

**Research card for the Learning Loop.** Answers the question: *how do you verify that someone
genuinely possesses a PRACTICAL skill when theoretical explanation is insufficient?*
Companion to `docs/learning-loop-vision.md` §2.7. This document gates LL-05 (verification engine):
its evidence taxonomy (§1), established frameworks (§2), anti-cheating patterns (§3),
decay/re-verification model (§4), rubric design rules (§5), lifecycle states (§7) and the
per-domain catalog (§8–9) define what the engine's schema must support.

Date: 2026-10-09 · Author: gemini (research profile) · Status: v1 for LL-05 schema freeze

---

## 0. Executive summary

1. **The strongest single predictor of skilled behavior is a sample of the behavior itself.**
   Decades of personnel-selection research on *work samples* show direct performance simulations
   predict later job performance as well as or better than tests of knowledge, and better than most
   judgment-based methods (Robertson & Downs 1989 meta-analysis; §2.1). MakeSense ladder endpoints
   should therefore be *performances in a representative environment*, never quizzes.
2. **A verification is an argument, not a score.** Modern validity theory (Kane's interpretive
   argument; Messick's construct validity; van der Vleuten's programmatic assessment) says a claim
   like "user can do X" is justified by *multiple evidence lines converging* — artifact, context,
   process, defense, transfer — each with known failure modes (§2.6, §3). The engine should store
   evidence *lines*, not a single verdict.
3. **Every artifact-only channel is now cheat-able by AI; process evidence and defense-in-context
   are the counterweights.** Detecting AI-authored submissions by detector tools is unreliable in
   both directions (§3.1); the robust patterns are in-session creation, edit-history/process
   forensics, viva-voce-over-artifact, and transfer probes to novel contexts (§3.2).
4. **Verification expires.** Spaced-repetition and retrieval-practice research gives a directly
   usable model for decay and re-check scheduling (Cepeda et al.'s temporal spacing function;
   Bjork's desirable difficulties; SM-2/Leitner as engineering substrates). Recommend: every
   verified skill carries a decay clock tuned per domain (§8–9 catalog), with re-checks that are
   themselves *performances*, not recognition quizzes.
5. **Rubrics must be analytic with anchor exemplars, and model-assisted scoring needs a
   human-escalation band.** Analytic rubrics out-reliabilty holistic ones; automated scoring agrees
   with humans well enough for low-stakes screening but must escalate near boundaries (§5).

---

## 1. Evidence taxonomy — what "proof of skill" can look like

Ranked roughly by strength-per-cost for a self-directed learner app. Each class names its
canonical research grounding.

| # | Evidence class | What it is | Strength | Main weakness | Grounding |
|---|---|---|---|---|---|
| E1 | **Artifact (product)** | Code that runs, recording, photo set, built object, written piece, budget/portfolio file | High face validity; inspectable; durable | AI-generated / bought / copy-pasted artifacts are indistinguishable by product alone | authenticity literature (Wiggins; Quinlan et al. 2024) |
| E2 | **Performance-in-environment** | Doing the task in (or near) the context where it counts: live coding session, playing for an audience, shooting in bad light, real conversation with a native speaker | Highest predictive validity across the selection-psychology literature | Expensive to arrange; hard to observe asynchronously | work sampling (Robertson & Downs 1989), OSATS in surgery (Bodle et al. 2008), workplace assessment (Schuwirth & van der Vleuten 2020) |
| E3 | **Simulation** | Constrained replica: sandboxed IDE with unit tests, flight-trainer-style drill, simulated client call | Repeatable, auto-scoreable, comparable across users | Transfer gap: sim skill ≠ field skill without fidelity + debrief | simulation meta-analyses (Gordon et al. 2016; Cheng et al. 2014) |
| E4 | **Oral defense / viva over artifact** | Learner explains *why their* artifact works, fielding follow-ups and perturbation questions ("break it deliberately and fix it live") | Directly attacks impostor completions; cheap; strong signal of ownership | Anxious speakers under-signaled; rehearsed defenses possible | viva voce research (Stamp & Wright 1990), self-explanation effect (Chi/VanLehn lineage) |
| E5 | **Process evidence** | Keystroke/commit history, edit timelines, camera-verified build session, DAW project files with revision tracks, RAW+JPEG pairs | Very hard to fabricate after the fact; shows *how* skill was deployed | Privacy-sensitive; tooling overhead; can be gamed by scripted generation with plausible history | code-authenticity & plagiarism work (Phillips lineage; Duric et al. 2012; Bashir 2025) |
| E6 | **Project observation** | Longitudinal: mentor/peer/automated watching of multi-session projects (checklists à la Montessori/OSATS stations) | Captures planning, debugging, iteration — the parts artifacts hide | Rater burden; inter-rater drift | rater & work-sampling design (Kane 1994), Montessori observation (Marshall 2017) |
| E7 | **Peer review** | Community or cohort assessment of work; also producing reviews of others' work | Scales cheaply; reviewing builds metacognition | Bias, leniency, collusion; modest reliability | peer-assessment meta-analyses (Topping 1998; Falchikov & Goldfinch 2000) |
| E8 | **Transfer test (novel context)** | Apply the skill to a problem surface-different but structure-identical (or a genuinely new domain edge) | The sharpest discriminator between trained-to-test performance and skill | Hard to author well; far transfer is empirically weak, so near-mid transfer is realistic | transfer taxonomy (Barnett & Ceci 2002), context-dependency of skill (Godden & Baddeley 1975; Lock 1990) |

**Design rule for LL-05:** a verification verdict records one *primary* evidence class (E1–E8)
plus optional corroborating classes, each with provenance metadata (timestamp, tool, environment,
hash of artifact). This mirrors Kane's argument structure: claim + evidence + warrant.

---

## 2. Established frameworks worth stealing from

### 2.1 Work sampling (industrial/organizational psychology)
The oldest and most quantitatively solid evidence base for "show, don't tell": candidates perform
samples of the actual job. Robertson & Downs' meta-analysis of work-sample trainability tests and
the wider work-sample literature consistently finds sample-of-work methods among the highest
predictors of later performance, with evidence of lower adverse impact than paper tests
(10.1037/0021-9010.74.3.402; 10.1037/0021-9010.64.2.119). **Lesson:** endpoint = representative
task, sampled across time, auto-scored where the task's correctness is mechanical.

### 2.2 Competency-based & programmatic assessment (health professions)
Miller's pyramid (knows → knows-how → shows → does) is the canonical frame: a *practical* skill
claim lives only at "shows" (performance) and "does" (workplace action) levels
(Miller 1990, doi:10.1097/00001888-199009000-00045; ten Cate et al.'s entrustment extension,
doi:10.1097/acm.0000000000003800 — "how much supervision would you trust this person with?" is a
beautifully calibrated ladder semantic). van der Vleuten's *programmatic assessment* replaces
single high-stakes exams with many low-stakes data points that each carry *decision value* —
precisely the MakeSense loop's shape (doi:10.1007/s40670-016-0343-7; Heeneman et al. 2015,
doi:10.1111/medu.12645). OSATS (objective structured assessment of technical skills) demonstrates
the station + analytic-rubric + rater design that any observation-based verifier should copy
(Bodle et al. 2008, doi:10.1080/01421590701881624).

### 2.3 E-assessment for programming
Auto-graders (unit-test harnesses, static analysis, test-coverage metrics) are the most mature
automated performance verification anywhere: they give instant, reproducible, rubric-free
correctness evidence at scale (Paiva, Leal & Figueira 2022 state-of-the-art review,
doi:10.1145/3513140; Messer, Brown & Kölling systematic review of grading+feedback tools,
doi:10.1145/3636515). The known failure: passing tests ≠ understanding; hence process evidence
and code-walkthrough supplementation (§3).

### 2.4 Music, sport & portfolio assessment
Music/sport assessment converges on *recorded live performance scored on analytic rubrics* plus
longitudinal portfolios; score variability across evaluators is substantial unless presentation
format and evaluation strategy are standardized (Iuşcă et al. 2014,
doi:10.1016/j.sbspro.2014.03.224; DeLuca et al. 2014, doi:10.1177/0027432114540336). Ericsson's
deliberate-practice framework supplies the practice-quality rubric (goal, feedback, repetition at
the edge of ability) that a "practice log" evidence type should enforce
(doi:10.1037/0033-295X.100.3.363), while Macnamara & Maitra's replication cautions that practice
hours alone underdetermine expert status (doi:10.1098/rsos.190327) — verified performance, not
practice time, must be the ladder gate. Portfolio validity research shows portfolios work best as
*programmatic* evidence with rubrics and reflection prompts (Roberts et al. 2014,
doi:10.1186/1472-6920-14-197).

### 2.5 Observation checklists (Montessori lineage)
Montessori's trained-observer protocol — behavior categories, time-sampling, no interruption —
is the ancestor of modern checklist observation; its evidence base is reviewed in Marshall 2017
(doi:10.1038/s41539-017-0012-7). For MakeSense: observation evidence should be event-logged
("did X unprompted within session Y") rather than impression-scored.

### 2.6 Validity theory (the schema constraint)
Kane's interpretive-argument framework and Messick's construct-validity tradition say an
assessment claim decomposes into *scores → observations → inferences → decisions*, each hop
needing warrant (Kane 1994, doi:10.1177/016327879401700202). Black & Wiliam's classroom-assessment
synthesis shows assessment itself changes learning (doi:10.1080/0969595980050102) — verification
sessions are teaching sessions; design them as desirable-difficulty retrieval events, not
administrative checkpoints (§4).

---

## 3. Anti-AI / impostor-completion detection

### 3.1 Why detectors alone fail
Text/code detectors show high false-positive and false-negative rates; cross-lingual and
cross-model generalization is weak (survey: Chakraborty et al. 2023, doi:10.48550/arxiv.2304.04736),
and for *code* the boundary between LLM clone-detection and similarity assessment is explicitly
blurred (Zhang & Saber 2025, doi:10.3390/bdcc9020041). A practical countermeasure that *does*
work: have the system plant stylistic/semantic "pseudo-AI" signatures and flag submissions that
match machine generation patterns it seeds deliberately (Bashir et al. 2025,
doi:10.3389/fcomp.2025.1549761). **Policy: never treat AI-detector output as exonerating or
convicting; treat it as one prior that raises the probability of a defense/transfer probe.**

### 3.2 The four robust patterns
1. **In-session creation** (proctored-by-construction): time-boxed, sandboxed, keystroke/edit
   history captured. Copilot-era caution: even in-session assistance skews what's "theirs";
   productivity studies show novices over-rely and under-learn with code assistants (Dakhel et
   al. 2023, doi:10.1016/j.jss.2023.111734; Prather et al. 2024 widening-gap evidence,
   doi:10.1145/3632620.3671116). Design: "AI-off windows" for verification attempts.
2. **Process forensics**: commit-graph shape, message quality, revert/refactor patterns, DAW
   project edit histories, RAW-with-edited-JPEG pairing. Classical code-similarity systems
   (Joyal et al. / MOSS lineage; Duric et al.'s similarity system, doi:10.1093/comjnl/bxs018)
   plus assignment design that structurally resists copying — randomized parameters per learner,
   high individualization (Simon et al. 2017, doi:10.1145/3013499.3013507).
3. **Viva-voce-over-artifact**: present artifact → answer *perturbation* questions ("change
   requirement X", "why does removing this line break test Y?"), and live-debug a seeded defect.
   Rooted in the viva tradition as integrity check (Stamp & Wright 1990,
   doi:10.1007/978-1-4471-1753-7_11) and in the self-explanation effect — generating explanations
   about one's own work is itself a learning + discriminating act (Chi et al. lineage; model in
   VanLehn et al. 1992, doi:10.1207/s15327809jls0201_1).
4. **Transfer probe**: near-but-novel context (see E8; Barnett & Ceci's transfer taxonomy,
   doi:10.1037/0033-2909.128.4.612). Trained-to-test artifacts fail these at a much higher rate.

### 3.3 Escalation ladder (recommended engine policy)
`artifact accepted (routine)` → anomaly signal (detector prior, similarity hit, implausible time
profile) → `defense request` → defense unsatisfactory or evasion → `in-session re-creation task`
→ failure → verification flagged provisional + spaced re-check. Every rung preserves learner
dignity (false positives with GitHub Copilot-style tooling are common) and logs which rung was
used. This is exactly the work-sample "trainability retest" pattern industrial psych uses when a
sample looks coached (Robertson & Downs 1989).

---

## 4. Mastery decay & re-verification (keeping verdicts current)

- **Forgetting is exponential-ish and structured.** Ebbinghaus's original function
  (doi:10.1037/10011-000) still anchors decay clocks; modern retrieval research shows each
  successful recall *flattens* the future decay curve (Roediger & Karpicke's test-enhanced
  learning, doi:10.1111/j.1467-9280.2006.01693.x; Karpicke & Roediger's critical-importance
  result, doi:10.1126/science.1152408; retrieval > concept maps, doi:10.1126/science.1199327).
- **Spacing engineering.** Leitner boxes and Wozniak's SM-2 algorithm (super-memory.com/english/ol/sm2.htm)
  are the de-facto open implementations for scheduling review at rising intervals; the empirical
  basis is the temporal spacing function — recall probability as a function of elapsed time
  since last retrieval (Cepeda, Pashler, Vul, Wixted & Rohrer 2006 quantitative synthesis,
  doi:10.1037/0033-2909.132.3.354; Carpenter, Cepeda, Rohrer & Kang 2012 review,
  doi:10.1007/s10648-012-9205-z). Bjork's *desirable difficulties* (doi:10.7551/mitpress/4561.003.0011)
  and expanding-interleave schedules (Storm, Bjork & Storm 2010, doi:10.3758/mc.38.2.244) justify
  making re-checks *harder/different* than the original, not identical.
- **Context-dependency warns against pure app-internal re-checks.** Performance degrades when the
  retrieval context diverges from the learning context (Godden & Baddeley 1975,
  doi:10.1111/j.2044-8295.1975.tb01468.x; "state of the art" context-fluctuation account, Smith 2007);
  practical skills are context-tied (Lock 1990, doi:10.1080/0263514900080104). So the re-check
  calendar should *rotate environments* (different project, different instrument setting,
  different city/day for a shoot, different native-speaker partner).
- **Implication for LL-05:** store per skill a `last_verified_perf` strength + `decay_rate`
  fitted from re-check outcomes; SM-2-style interval expansion (×2.5–3 per successful spaced
  re-verification, floor at domain minimums in §9); auto-surface a *performance* re-check
  (E2/E3/E8 flavored) when predicted confidence crosses a threshold; a lapse downgrades the
  ledger entry to "provisional" instead of deleting it.

---

## 5. Rubric design

- **Analytic > holistic for automated or shared scoring.** Dimension-by-dimension scoring is more
  reliable, more diagnostic, and more feedback-useful (Jonsson & Svingby's review of rubric
  reliability/validity/consequences, doi:10.1016/j.edurev.2007.05.002; Reddy & Herrera's
  efficiency findings; Andrade's practical rubric guidance,
  doi:10.3200/ctch.53.1.27-31). Holistic only for fast triage.
- **Anchor exemplars are non-negotiable.** Reliability of both human and model scoring rises
  sharply with calibrated examples per level band (Jonsson & Svingby 2007 above). LL-05 should
  ship each rubric with 2–3 real anchor artifacts per level, curated from the community corpus.
- **Model-assisted scoring:** acceptable for formative feedback and low-stakes gating, with
  (a) dual-scoring or self-consistency checks on boundary cases, (b) an explicit
  *human-escalation band* around the pass threshold, (c) rubric text injected verbatim into the
  prompt, (d) periodic re-calibration against human goldens. The automated-scoring validity
  literature (AES in writing: Weigle 2002, doi:10.1017/cbo9780511732997) shows the pattern:
  agree-with-human in aggregate yes; single-decision authority no.
- **Feedback loop design:** verification must produce actionable feedback ( Sadler's gap model,
  via Hattie & Timperley's synthesis tradition; Black & Wiliam 1998,
  doi:10.1080/0969595980050102). A verdict without a "next-attempt delta" wastes the
  assessment's own teaching effect.

---

## 6. What we are NOT claiming

- We are not claiming AI-detector scores are usable as verdicts (evidence against: §3.1).
- We are not claiming practice hours prove skill (Macnamara & Maitra 2019 caution, §2.4).
- We are not claiming far transfer is common — transfer probes must stay *near-to-mid*
  (Barnett & Ceci 2002, §1-E8).

---

## 7. Verification lifecycle states (schema seed for LL-05)

`unverified → provisional (artifact+process) → verified (artifact+defense|in-session) →
reinforced (spaced performance re-check passed) → provisional→ (lapsed) → re-verify`
Each transition records: evidence classes used, rubric version, decay-clock update, escalation
rung. Append-only with provenance, per vision doc §3 "stores".

---

## 8. Per-domain verification catalog (MakeSense skill families)

Format: best evidence (primary → corroborating), rubric outline, expiry/re-check recommendation.
Rubric levels assumed 4 (Novice/Working/Proficient/Strong) with anchors (§5).

### 8.1 Coding / web-dev
- **Best evidence:** E3 sandboxed tasks with hidden unit tests + time-boxed build → E5 commit/edit
  history → E4 code-walkthrough viva with live perturbation ("break/fix", "migrate to X") → E8
  transfer to unfamiliar repo/stack.
- **Rubric:** correctness-pass-rate (auto) · debugging-independence (from process log: prompts
  needed, error-recovery latency) · design/maintainability (rubric dims: naming, structure, edge
  cases) · explanation quality (viva: predicts behavior of unseen code).
- **Anti-cheat:** per-user randomized spec params; AI-off verification windows; detector only as
  escalation trigger (§3.3).
- **Expiry:** fast-decaying *fluency*, slow-decaying *conceptual* skill. Re-check every
  **45–75 days** for active stacks (spacing function supports ~2-month first interval), 6 months
  for language-agnostic concepts (debugging, data modeling); downgrade provisional if no in-session
  performance within 2× interval.

### 8.2 Music (guitar)
- **Best evidence:** E1 unedited continuous **video+audio recording** of full piece (no
  comping/editing — editing destroys the evidence) → E2 performance with an audience/take-limit
  ("2 takes only") → E8 transfer: play an *unseen* sight-reading/ear-copy excerpt at level,
  accompany a chord progression the learner hasn't rehearsed.
- **Rubric:** technique (timing/pulse stability, tone, sync between hands — some dims
  machine-scoreable: onset timing via audio alignment, tuning, tempo) · musicality
  (dynamics/phrasing, anchor-recorded) · repertoire fluency from memory · error recovery
  (keeps going vs restarts — from single-take recording).
- **Machine assist:** onset/timing and pitch analysis for the objective dims; rubric-scored
  human/model review for musicality.
- **Expiry:** motor memory decays but is slow and *per-repertoire*. Re-check every **60–90
  days**: piece performance re-checks every 3 months; the *transfer* ear/sight probe (the real
  skill) every 6 months. Practice-log (deliberate-practice structured: goal/repetition/feedback)
  corroborates between checks; it never gates.

### 8.3 Finance practice (budgeting, investing, taxes — *doing*, not knowing)
- **Best evidence:** E2/E5 **real artifacts with verified provenance**: 3+ months of a functioning
  budget system (categorized export, reconciliation log), brokerage statement showing a executed
  plan consistent with stated strategy (positions, contributions, rebalancing timestamps), filed
  documents (redacted). Knowledge-only evidence (quizzes about ER/expense ratios) is explicitly
  insufficient — financial *literacy ≠ financial behavior* (Lusardi & Mitchell, behavioral
  finance evidence line, doi:10.3386/w17108).
- **Rubric:** plan-quality vs own constraints · execution consistency (deviations logged and
  explained) · adaptive behavior during life-event scenario sims (E3: "income drops 30%, now
  what — with your actual numbers") · defense: justify any position's rationale without jargon.
- **Expiry:** low-decay procedural (a budget system you maintain IS continuous verification).
  Re-check every **6–12 months** via *fresh artifacts*; mandatory re-verify on account/plan
  change events. Scam/decision drills annually.

### 8.4 Language
- **Best evidence:** E2 **live conversation with a (varied) human interlocutor**, recorded →
  E1 self-contained monologue/storytelling recording on unseen prompt → E8 topic-domain transfer
  (surprise register switch: complain formally after casual fluency). Frame-of-reference:
  ACTFL-style proficiency interviews rate *function + topic + text type*, validated at scale
  (OPIc validation, doi:10.1177/0265532219828253; see also the speaking-rating-process
  literature, e.g. Brown's IELTS speaking rating examination via OpenAlex, cited-by ~34).
- **Rubric:** task completion (did the conversation achieve its goal) · range & accuracy
  (error density vs complexity attempted — they trade off, score the *ceiling*) · fluency
  (pause analysis, machine-assistable) · interaction management (repair, clarification — the
  skill AI-chat cannot show).
- **Anti-cheat:** live turns; transcription tools banned mid-interview; ASR-quality variance
  controlled by requiring camera+audio session.
- **Expiry:** moderate, steep for productive skills. **30–60 day** speaking spot-checks (short
  calls), full rubric re-check every **4–6 months**. Vocabulary decays fastest — fold retrieval
  (production prompts, not recognition) into the SM-2 queue.

### 8.5 Photography / video
- **Best evidence:** E1 shoot on a **timed, randomized brief** ("golden-hour street photography,
  submit 6–10 RAW+JPEG within 48h, RAW required") → E5 RAW metadata (exposure triangle tells the
  in-the-moment story) + edit history in Lightroom/Resolve project file → E4 defense: justify
  frame/sequence choices against brief → E8 transfer: same brief class in unfamiliar genre or
  gear constraint ("one prime lens only").
- **Rubric:** technical (exposure/focus/horizon/audio levels — machine-checkable from metadata
  and loudness analysis) · compositional intentionality (against anchors) · editing restraint
  (RAW→final delta) · series/narrative coherence (video: pacing, continuity, audio mix).
- **Expiry:** technique slow-decay (it's embodied), taste doesn't decay. Re-check every
  **90–120 days** with a fresh constrained brief.

### 8.6 Physical crafts (woodwork, electronics, cooking, etc.)
- **Best evidence:** E2/E6 **in-person or livestreamed station assessment** (OSATS model —
  stations + checklist + rubric, validated for workplace technical skills: Bodle et al. 2008,
  doi:10.1080/01421590701881624) → E1 built object measured against spec (dimensions, joint
  quality, tolerances — often objectively measurable) → defense: "show me your setup and
  demonstrate the risky step" (safety competence is part of the skill).
- **Rubric:** safety & setup behavior (checklist, live) · process execution (order, tool choice)
  · artifact conformance to spec (measurements) · finishing/tolerance · troubleshooting on a
  seeded wrinkle ("this joint is loose — fix it in front of us").
- **Anti-cheat:** time-lapse video of build OR livestream; material receipts + tool-timing
  heuristics for async submissions; buy-nothing rule in rubric anchors.
- **Expiry:** procedural-motor, slow decay but safety habits decay *fast*. **6–12 months**; any
  tool/process change forces re-verification of the affected station.

### 8.7 Math problem-solving
- **Best evidence:** E3 **in-session problem set with randomized parameters and step-level
  capture** (auto-graded correctness + solution-path telemetry) → E4 oral walkthrough of one
  chosen solution incl. "why did your first approach fail" → E8 structural-transfer items
  (same concept, novel surface, not from any practiced family). Re-reads/lecture-watching are
  near-worthless for retention; retrieval-practice evidence dominates (Dunlosky et al. 2013
  utility rankings, doi:10.1177/1529100612453266; Roediger & Karpicke above).
- **Rubric:** final correctness · strategy selection (right tool before grinding) · step validity
  (partial credit for method even with slips — the Schoenfeld tradition of valuing exploration
  and metognition over answer-getting) · novel-item transfer score.
- **Machine assist:** CAS-enabled grading of symbolic steps; LLM scoring only for explanation
  quality, inside escalation band (§5).
- **Expiry:** decays with the forgetting curve unless interleaved. Re-check every **30–45 days**
  via mixed-set retrieval (interleaved across subtopics — spacing/interleaving evidence),
  with expanding intervals per successful re-verification.

---

## 9. Cross-cutting re-verification calendar (default decay parameters)

| Family | First re-check | Steady-state interval | Downgrade trigger |
|---|---|---|---|
| Coding | 30 d | 45–75 d (stack), 6 mo (concepts) | no in-session run in 2× interval |
| Guitar | 30 d (repertoire) | 60–90 d; transfer probe 180 d | failed ear/sight probe |
| Finance | 60 d | 6–12 mo + event-driven | plan abandoned (no artifacts) |
| Language | 21 d micro-checks | 30–60 d spot, 4–6 mo full | 2 failed conversation tasks |
| Photo/video | 45 d | 90–120 d | brief miss on 2 consecutive |
| Crafts | 60 d | 6–12 mo; immediate on tool change | safety checklist miss |
| Math | 21–30 d | 30–45 d interleaved | novel-item score < threshold |

All intervals expand ×2.3–2.7 per clean spaced re-verification up to the family ceiling
(SM-2-style growth, floor = domain minimum), matching the spacing-function literature (§4).

---

## 10. Source list (verified resolvable; each DOI/URL was checked live at research time 2026-10-09)

Frameworks & evidence classes
1. Miller, G. (1990). The assessment of clinical skills/competence/performance. *Acad Med*. — https://doi.org/10.1097/00001888-199009000-00045
2. ten Cate, O., Carraccio, C., et al. (2020). Entrustment Decision Making: Extending Miller's Pyramid. *Acad Med*. — https://doi.org/10.1097/acm.0000000000003800
3. van der Vleuten, C. et al. (2016/2012). A Programmatic Approach to Assessment / programmatic assessment. — https://doi.org/10.1007/s40670-016-0343-7
4. Heeneman, S. et al. (2015). The impact of programmatic assessment on student learning. *Med Educ*. — https://doi.org/10.1111/medu.12645
5. Schuwirth, L. & van der Vleuten, C. (2020). A history of assessment in medical education. — https://doi.org/10.1007/s10459-020-10003-0
6. Kane, M. (1994). Validating interpretive arguments for licensure/certification exams. — https://doi.org/10.1177/016327879401700202
7. Black, P. & Wiliam, D. (1998). Assessment and Classroom Learning. — https://doi.org/10.1080/0969595980050102
8. Marshall, C. (2017). Montessori education: a review of the evidence base. *npj Science of Learning*. — https://doi.org/10.1038/s41539-017-0012-7

Work sampling & personnel assessment
9. Robertson, I. & Downs, S. (1989). Work-sample tests of trainability: a meta-analysis. *J Appl Psychol*. — https://doi.org/10.1037/0021-9010.74.3.402
10. Brugnoli et al./Campion lineage (1979). Racial bias in the use of work samples for personnel selection. *J Appl Psychol*. — https://doi.org/10.1037/0021-9010.64.2.119
11. Paese, P. & Switzer, F. (1988). Validity generalization and the Schmidt–Hunter procedure. *J Appl Psychol*. — https://doi.org/10.1037/0021-9010.73.2.267
12. Bodle, J. et al. (2008). Value and face validity of OSATS for workplace technical-skill assessment. *Med Teach*. — https://doi.org/10.1080/01421590701881624
13. OECD. The Survey of Adult Skills (PIAAC) and the measurement of human capital. — https://doi.org/10.1787/9789264204027-11-en (publisher page: https://www.oecd.org/en/publications/the-survey-of-adult-skills_9789264204027-en.html)

Simulation & transfer
14. Gordon, C. et al. (2016). Simulation-based assessments in health professional education: a systematic review. — https://doi.org/10.2147/JMDH.S92695
15. Cheng, A. et al. (2014). Debriefing for technology-enhanced simulation: systematic review & meta-analysis. *Med Educ*. — https://doi.org/10.1111/medu.12432
16. Barnett, S. & Ceci, S. (2002). When and where do we apply what we learn? A taxonomy for far transfer. *Psychol Bull*. — https://doi.org/10.1037/0033-2909.128.4.612
17. Godden, D. & Baddeley, A. (1975). Context-dependent memory on land and underwater. *Br J Psychol*. — https://doi.org/10.1111/j.2044-8295.1975.tb01468.x
18. Smith, S. (2007). Context fluctuation and time-dependent memory phenomena. — https://doi.org/10.1037/e527342012-142
19. Lock, R. (1990). Assessment of practical skills: context dependency and construct validity. *Res Sci Technol Educ*. — https://doi.org/10.1080/0263514900080104

Expertise & practice
20. Ericsson, K.A., Krampe, R. & Tesch-Römer, C. (1993). The role of deliberate practice in expert performance. *Psychol Rev*. — https://doi.org/10.1037/0033-295X.100.3.363
21. Ericsson, K.A. (2008). Deliberate practice and acquisition of expert performance: a general overview. *Acad Emerg Med*. — https://doi.org/10.1111/j.1553-2712.2008.00227.x
22. Macnamara, B. & Maitra, S. (2019). The role of deliberate practice in expert performance (revisiting Ericsson et al.). *R Soc Open Sci*. — https://doi.org/10.1098/rsos.190327

Memory, spacing, re-verification
23. Ebbinghaus, H. (1913 transl.). Memory: a contribution to experimental psychology. — https://doi.org/10.1037/10011-000
24. Roediger, H. & Karpicke, J. (2006). Test-enhanced learning. *Psychol Sci*. — https://doi.org/10.1111/j.1467-9280.2006.01693.x
25. Karpicke, J. & Roediger, H. (2008). The critical importance of retrieval for learning. *Science*. — https://doi.org/10.1126/science.1152408
26. Karpicke, J. & Blunt, J. (2011). Retrieval practice produces more learning than elaborative studying with concept mapping. *Science*. — https://doi.org/10.1126/science.1199327
27. Cepeda, N. et al. (2006). Distributed practice in verbal recall tasks: review & quantitative synthesis. *Psychol Bull*. — https://doi.org/10.1037/0033-2909.132.3.354
28. Carpenter, S., Cepeda, N., Rohrer, D. & Kang, S. (2012). Using spacing to enhance diverse forms of learning. *Educ Psychol Rev*. — https://doi.org/10.1007/s10648-012-9205-z
29. Storm, B., Bjork, E. & Storm, R. (2010). Optimizing retrieval as a learning event (expanding retrieval practice). — https://doi.org/10.3758/mc.38.2.244
30. Bjork, R. (1994). Memory and metamemory considerations in the training of human beings (desirable difficulties). MIT Press. — https://doi.org/10.7551/mitpress/4561.003.0011
31. Dunlosky, J. et al. (2013). Improving students' learning with effective learning techniques. *PSPI*. — https://doi.org/10.1177/1529100612453266
32. Wozniak, P.A. (1990). SM-2 algorithm documentation (SuperMemo). — https://super-memory.com/english/ol/sm2.htm
33. Rohrer, D. & Pashler, H. (2012). Learning styles: where's the evidence? (caution on modality-based "verification") *Med Educ*. — https://doi.org/10.1111/j.1365-2923.2012.04273.x

Anti-cheating & AI-era integrity
34. Chakraborty, S. et al. (2023). On the possibilities of AI-generated text detection (survey). arXiv. — https://doi.org/10.48550/arXiv.2304.04736
35. Bashir, S. (2025). Using pseudo-AI submissions for detecting AI-generated code. *Front Comput Sci*. — https://doi.org/10.3389/fcomp.2025.1549761
36. Zhang & Saber (2025). Exploring boundaries between LLM code-clone detection and similarity assessment. — https://doi.org/10.3390/bdcc9020041
37. Joyal/Duric lineage: Ďuric, L. et al. (2012). A source code similarity system for plagiarism detection. *Comput J*. — https://doi.org/10.1093/comjnl/bxs018
38. Simon et al. (2017). Designing programming assignments to reduce the likelihood of cheating. — https://doi.org/10.1145/3013499.3013507
39. Dakhel, A.M. et al. (2023). GitHub Copilot AI pair programmer: asset or liability? *J Syst Softw*. — https://doi.org/10.1016/j.jss.2023.111734
40. Prather, J. et al. (2024). The widening gap: benefits and harms of generative AI for novice programmers. SIGCSE. — https://doi.org/10.1145/3632620.3671116
41. Stamp & Wright (1990). The viva voce examination (as integrity/defense check). — https://doi.org/10.1007/978-1-4471-1753-7_11
42. VanLehn, K., Jones, R. & Chi, M. (1992). A model of the self-explanation effect. *J Learn Sci*. — https://doi.org/10.1207/s15327809jls0201_1

E-assessment, rubrics, portfolios, peer review, domain-specific
43. Paiva, J.C., Leal, J.P. & Figueira, A. (2022). Automated assessment in CS education: state-of-the-art review. *ACM TOCE*. — https://doi.org/10.1145/3513140
44. Messer, M., Brown, N. & Kölling, M. (2024). Automated grading and feedback tools for programming education: systematic review. *ACM TOCE*. — https://doi.org/10.1145/3636515
45. Jonsson, A. & Svingby, G.-C. (2007). The use of scoring rubrics: reliability, validity and educational consequences. *Educ Res Rev*. — https://doi.org/10.1016/j.edurev.2007.05.002
46. Andrade, H. (2005). Teaching with rubrics: the good, the bad, and the ugly. — https://doi.org/10.3200/ctch.53.1.27-31
47. Weigle, S.C. (2002). Assessing writing (incl. validity of automated essay scoring). Cambridge. — https://doi.org/10.1017/cbo9780511732997
48. Quinlan, K. et al. (2024). Educationally authentic assessment: reframing authenticity. *Teach High Educ*. — https://doi.org/10.1080/13562517.2024.2394042
49. Topping, K. (1998). Peer assessment between students in colleges and universities. *Rev Educ Res*. — https://doi.org/10.3102/00346543068003249
50. Falchikov, N. & Goldfinch, J. (2000). Student peer assessment in higher education: a meta-analysis. *Rev Educ Res*. — https://doi.org/10.3102/00346543070003287
51. Roberts, C. et al. (2014). Reliability and validity of a portfolio designed as programmatic assessment. *BMC Med Educ*. — https://doi.org/10.1186/1472-6920-14-197
52. Iuşcă, D. et al. (2014). Evaluation strategy and music performance presentation format on score variability. *Procedia Soc Behav Sci*. — https://doi.org/10.1016/j.sbspro.2014.03.224
53. DeLuca, C. et al. (2014). Music performance assessment. *Music Educators Journal*. — https://doi.org/10.1177/0027432114540336
54. Isbell, D. & Winke, P. (2019). ACTFL Oral Proficiency Interview – computer (OPIc) validity. *Lang Test*. — https://doi.org/10.1177/0265532219828253
55. Lusardi, A. & Mitchell, O. (2011). Financial literacy and retirement planning in the United States. NBER WP 17108. — https://doi.org/10.3386/w17108

(55 verified sources; ≥15 requirement met. Every DOI above was resolved against the Crossref or
OpenAlex registry during this task; arXiv and publisher URLs were fetched live.)
