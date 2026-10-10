// LL-08 frontend mode router tests (node:test). Mirrors the backend
// learning_modes semantics against the SAME config/interest_drift.json.
// Run: node --test frontend/src/learning/__tests__/

import test from 'node:test';
import assert from 'node:assert/strict';
import { selectLearningMode, modesForSkill, verificationEndpoint,
         allModesShareEndpoint } from '../modeRouter.js';
import { loadInterestConfig } from '../interestConfig.js';

const cfg = loadInterestConfig();

test('config loads with all LL-08 sections', () => {
  for (const k of ['time', 'signal_weights', 'profile', 'change_point', 'drift',
                   'goal_protection', 'mode_routing', 'future_paths', 'project_mode']) {
    assert.ok(cfg[k], `missing ${k}`);
  }
});

test('goal defaults: hobby -> guided, job-ready -> project_together', () => {
  assert.equal(selectLearningMode({ skillTag: 'guitar', goalType: 'hobby' }, { cfg }).mode, 'guided');
  const d = selectLearningMode({ skillTag: 'python', goalType: 'job-ready' }, { cfg });
  assert.equal(d.mode, 'project_together');
  assert.equal(d.decidedBy, 'goal_default');
});

test('level default: novice -> guided even for a job-ready goal', () => {
  const d = selectLearningMode({ skillTag: 'python', goalType: 'job-ready' }, { cfg, learnerLevel: 'novice' });
  assert.equal(d.mode, 'guided');
  assert.equal(d.decidedBy, 'level_default');
});

test('user override wins and is validated', () => {
  const d = selectLearningMode({ skillTag: 'python', goalType: 'job-ready' }, { cfg, override: 'drill_verify' });
  assert.equal(d.mode, 'drill_verify');
  assert.equal(d.decidedBy, 'user_override');
  assert.throws(() => selectLearningMode({ skillTag: 'x' }, { cfg, override: 'nope' }));
});

test('all four doors reachable for one skill', () => {
  assert.equal(modesForSkill('guitar', cfg).length, 4);
});

test('every mode shares the same verification endpoint', () => {
  assert.ok(allModesShareEndpoint('guitar', cfg));
  assert.equal(verificationEndpoint('guided', 'guitar', cfg).endpoint,
               cfg.mode_routing.verification_endpoint);
});
