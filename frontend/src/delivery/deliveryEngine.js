// LL-04 mode controller — active vs passive delivery engine.
// Pure logic; all thresholds come from config/delivery_dial.json.
// Mirrors services/event-tracker/app/delivery_engine.py (single JSON config
// feeds both). Track keys are LL-02 track ids / goal_type values.

import { loadDialConfig } from './dialConfig.js';

// --- Segment classifier: intake vs consolidation ---------------------------

export function classifySegment(segment, cfg = loadDialConfig(), priorVisits = 0) {
  const clf = cfg.segment_classifier;
  const kind = (segment.kind || '').toLowerCase();
  if (kind === 'intake' || kind === 'consolidation') return kind;

  const haystack = [
    segment.title || '',
    segment.contentType || segment.content_type || '',
    segment.nodeType || segment.node_type || '',
    (segment.tags || []).join(' '),
  ].join(' ').toLowerCase();

  for (const marker of clf.consolidation_markers) {
    if (haystack.includes(marker)) return 'consolidation';
  }
  for (const marker of clf.intake_markers) {
    if (haystack.includes(marker)) return 'intake';
  }
  if (priorVisits === 0 && clf.first_visit_is_intake) return 'intake';
  return 'consolidation';
}

export function modeIsActive(mode, cfg = loadDialConfig()) {
  return cfg.modes.active.includes(mode);
}

// --- Mode resolution --------------------------------------------------------
// Precedence: escalation (flip rule) > energy override > segment-kind default
// > track default mode. Returns {mode, modeClass, decidedBy, reason}.

export function resolveMode(track, segmentKind, { cfg = loadDialConfig(), activeEscalation = null, energy = null } = {}) {
  const goalType = track.goalType || track.goal_type || 'hobby';
  const defaults = cfg.track_defaults[goalType]
    || cfg.track_defaults[Object.keys(cfg.track_defaults).sort()[0]];

  if (activeEscalation) {
    const mode = segmentKind === 'consolidation' ? 'retrieval_prompt' : 'predict_before_reveal';
    return { mode, modeClass: 'active', decidedBy: 'escalation',
             reason: activeEscalation.reason || 'flip_rule' };
  }

  if (energy != null && energy <= (cfg.energy_overrides?.energy_max ?? 2)
      && segmentKind === 'intake' && !modeIsActive(defaults.intake_mode, cfg)) {
    return { mode: defaults.intake_mode, modeClass: 'passive',
             decidedBy: 'energy_override', reason: `energy=${energy}, intake stretch` };
  }

  const mode = segmentKind === 'intake' ? defaults.intake_mode
    : segmentKind === 'consolidation' ? defaults.consolidation_mode
    : defaults.default_mode;
  return { mode, modeClass: modeIsActive(mode, cfg) ? 'active' : 'passive',
           decidedBy: 'track_default', reason: `${goalType} default for ${segmentKind}` };
}

// --- Adaptive flip rule -----------------------------------------------------
// segments: array of {modeClass, abandoned, retrievalOutcome, sessionId}
// Returns {skillTag, shouldFlip, reason, evidence}.

export function evaluateFlipRule(skillTag, segments, cfg = loadDialConfig()) {
  const fr = cfg.flip_rule;
  const passive = segments.filter((s) => (s.modeClass || s.mode_class) === 'passive');
  const active = segments.filter((s) => (s.modeClass || s.mode_class) === 'active');
  const sessions = new Set(segments.map((s) => s.sessionId || s.session_id).filter(Boolean));

  const evidenceCommon = {
    sessions_observed: sessions.size,
    passive_segments: passive.length,
    active_segments: active.length,
    thresholds: {
      min_sessions_per_skill: fr.min_sessions_per_skill,
      passive_abandon_rate_threshold: fr.passive_abandon_rate_threshold,
      failed_retrieval_count_threshold: fr.failed_retrieval_count_threshold,
    },
  };

  if (sessions.size < fr.min_sessions_per_skill) {
    return { skillTag, shouldFlip: false,
             evidence: { ...evidenceCommon, note: 'below min_sessions_per_skill' } };
  }

  // Trigger 1: passive-correlated drop-off
  if (passive.length) {
    const pAb = passive.filter((s) => s.abandoned);
    const pRate = pAb.length / passive.length;
    const aRate = active.length ? active.filter((s) => s.abandoned).length / active.length : 0;
    if (pRate >= fr.passive_abandon_rate_threshold && pRate > aRate) {
      return { skillTag, shouldFlip: true, reason: 'passive_dropout', evidence: {
        ...evidenceCommon,
        passive_abandon_rate: Number(pRate.toFixed(3)),
        active_abandon_rate: Number(aRate.toFixed(3)),
        sample_segment_ids: pAb.map((s) => s.id).filter(Boolean).slice(0, 10),
      } };
    }
  }

  // Trigger 2: failed later retrieval
  const failedAny = segments.filter((s) => (s.retrievalOutcome || s.retrieval_outcome) === 'incorrect');
  const failedPassive = passive.filter((s) => (s.retrievalOutcome || s.retrieval_outcome) === 'incorrect');
  if (failedAny.length >= fr.failed_retrieval_count_threshold) {
    return { skillTag, shouldFlip: true, reason: 'failed_retrieval', evidence: {
      ...evidenceCommon,
      failed_retrieval_count: failedAny.length,
      failed_after_passive_count: failedPassive.length,
      sample_segment_ids: failedAny.map((s) => s.id).filter(Boolean).slice(0, 10),
    } };
  }

  return { skillTag, shouldFlip: false, evidence: evidenceCommon };
}

// --- Companion voice layer ---------------------------------------------------
// Generates narrative bridges from ACTUAL ladder/mastery state — never canned.

export function generateBridge(trackState, masteryVector, ladder,
                               { cfg = loadDialConfig() } = {}) {
  const skill = trackState.skillTag || trackState.skill_tag || 'this skill';
  const rungs = ladder.rungs || [];
  if (!rungs.length) return null; // no state -> silence (non-negotiable #6)
  const rungIdx = Math.min(trackState.currentLadderRung ?? trackState.current_ladder_rung ?? 0,
                           rungs.length - 1);
  const subSkills = rungs[rungIdx].sub_skills || [];

  const scored = subSkills.map((ss) => ({
    name: ss.name,
    score: Number(masteryVector[ss.name]?.score ?? 0),
    ss,
  }));
  const gaps = scored.filter((x) => x.score < 0.6);
  const near = scored.filter((x) => x.score >= 0.6 && x.score < 0.8);
  const strengths = scored.filter((x) => x.score >= 0.8);

  const firstCanDo = (ss) => {
    const c = (ss.can_do_statements || [null])[0];
    // render "can X" statements as bare verb phrases for sentence templates
    return c ? c.replace(/^can\s+(do\s+)?/i, '') : null;
  };

  if (gaps.length) {
    const g = gaps.reduce((a, b) => (b.score > a.score ? b : a));
    const cando = firstCanDo(g.ss);
    if (cando) {
      const remaining = Math.max(1, Math.round((0.8 - g.score) / 0.1));
      return {
        text: `Here's the honest read on ${skill}: ${g.name} is at ${Math.round(g.score * 100)}%. ` +
              `You're ${remaining} session${remaining !== 1 ? 's' : ''} from being able to ` +
              `${cando} — that's the one to push on.`,
        motivation: 'competence',
      };
    }
  }

  if (near.length) {
    const g = near.reduce((a, b) => (b.score > a.score ? b : a));
    const cando = firstCanDo(g.ss);
    const tail = cando ? ` Once it's solid, ${cando} comes with it.` : '';
    return {
      text: `${g.name} is close — ${Math.round(g.score * 100)}% and climbing. ` +
            `You choose how to spend this session; a quick retrieval round usually finishes it.${tail}`,
      motivation: 'autonomy',
    };
  }

  if (strengths.length) {
    const g = strengths[0];
    const nxt = rungs[rungIdx + 1];
    if (nxt) {
      const rawNext = ((nxt.sub_skills || [{}])[0].can_do_statements || [null])[0];
      const nxtCanDo = rawNext ? rawNext.replace(/^can\s+(do\s+)?/i, '') : null;
      const est = trackState.sessionsRemainingEstimate ?? trackState.sessions_remaining_estimate;
      const fromTxt = est && nxtCanDo
        ? `You're about ${est} sessions from ${nxtCanDo}`
        : nxtCanDo
          ? `Next up at the ${nxt.level_name} level: ${nxtCanDo}`
          : `Next up: the ${nxt.level_name} level of ${skill}.`;
      return {
        text: `${g.name} is genuinely solid now (${Math.round(g.score * 100)}%). ${fromTxt}. ` +
              `I'll keep the harder reps in your way until it feels automatic.`,
        motivation: 'relatedness',
      };
    }
    return {
      text: `${g.name} is genuinely solid (${Math.round(g.score * 100)}%). This rung of ${skill} ` +
            `is verified ground — we build on it, not repeat it.`,
      motivation: 'competence',
    };
  }

  const firstName = subSkills[0]?.name || skill;
  return {
    text: `No readings on ${firstName} yet, so this session is a probe: attempt it, ` +
          `don't worry about being wrong — it calibrates everything after.`,
    motivation: 'autonomy',
  };
}

export function generateBridgesMany(triples, cfg = loadDialConfig()) {
  const budget = cfg.companion_voice?.max_bridge_words ?? 45;
  const out = [];
  for (const [ts, mv, lad] of triples) {
    const b = generateBridge(ts, mv, lad, { cfg });
    if (b && b.text.split(/\s+/).length <= budget) out.push(b);
  }
  return out;
}
