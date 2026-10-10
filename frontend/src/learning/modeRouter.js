// LL-08 learning-mode router (frontend mirror of
// services/event-tracker/app/learning_modes.py — one JSON config feeds both).
// One skill, many doors; every mode funnels into the SAME LL-05 verification
// endpoint. All thresholds come from config/interest_drift.json.

import { loadInterestConfig } from './interestConfig.js';

// Precedence: explicit user override > level default (novice -> guided,
// employable/job-ready -> project_together) > goal default.
export function selectLearningMode(track, { cfg = loadInterestConfig(), override = null, learnerLevel = null } = {}) {
  const mr = cfg.mode_routing;
  const modes = new Set(mr.modes);
  const skill = track.skillTag || track.skill_tag || 'this skill';
  const goal = track.goalType || track.goal_type || 'hobby';
  const level = learnerLevel || track.learnerLevel || track.learner_level || null;

  if (override) {
    if (!modes.has(override)) {
      throw new Error(`unknown mode: ${override}; expected one of ${[...modes].join(', ')}`);
    }
    return { skillTag: skill, mode: override, decidedBy: 'user_override',
             reason: `learner picked ${override} for ${skill}` };
  }

  if (level && mr.by_level[level]) {
    const mode = mr.by_level[level];
    return { skillTag: skill, mode, decidedBy: 'level_default',
             reason: `level ${level} defaults to ${mode}` };
  }

  const mode = mr.by_goal[goal] || 'guided';
  return { skillTag: skill, mode, decidedBy: 'goal_default',
           reason: `goal ${goal} defaults to ${mode}` };
}

export function modesForSkill(skillTag, cfg = loadInterestConfig()) {
  return cfg.mode_routing.modes.map((mode) => ({
    skillTag, mode, description: cfg.mode_routing.descriptions[mode] || '',
  }));
}

export function verificationEndpoint(mode, skillTag, cfg = loadInterestConfig()) {
  const mr = cfg.mode_routing;
  return { skillTag, mode, endpoint: mr.verification_endpoint, owner: 'LL-05',
           note: mr.verification_note };
}

// Invariant guard used by tests and the mode switcher UI: every door to a skill
// must resolve to the same verification endpoint.
export function allModesShareEndpoint(skillTag, cfg = loadInterestConfig()) {
  const eps = new Set(cfg.mode_routing.modes.map(
    (m) => verificationEndpoint(m, skillTag, cfg).endpoint));
  return eps.size === 1;
}
