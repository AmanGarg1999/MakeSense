// LL-08 mode-router demo: shows one skill reachable by all four doors, each
// terminating at the same LL-05 verification endpoint, with a per-track mode
// selectable and defaulted by level/goal.
// Run: node scripts/tests/demo_ll08_modes.mjs

import assert from 'node:assert/strict';
import { selectLearningMode, modesForSkill, verificationEndpoint }
  from '../../frontend/src/learning/modeRouter.js';
import { loadInterestConfig } from '../../frontend/src/learning/interestConfig.js';

const cfg = loadInterestConfig();
const skill = 'python';

console.log(`== One skill ("${skill}"), four doors ==\n`);
for (const d of modesForSkill(skill, cfg)) {
  const ep = verificationEndpoint(d.mode, skill, cfg).endpoint;
  console.log(`  ${d.mode.padEnd(16)} ${d.description.padEnd(70)} -> ${ep}`);
}

console.log('\n== Per-track selection: defaults by level then goal ==\n');
const cases = [
  [{ skillTag: 'guitar', goalType: 'hobby' }, {}],
  [{ skillTag: 'python', goalType: 'job-ready' }, {}],
  [{ skillTag: 'python', goalType: 'job-ready' }, { learnerLevel: 'novice' }],
  [{ skillTag: 'python', goalType: 'job-ready' }, { override: 'explore_explain' }],
];
for (const [track, opts] of cases) {
  const s = selectLearningMode(track, { cfg, ...opts });
  console.log(`  ${track.skillTag}(${track.goalType}${opts.learnerLevel ? `, ${opts.learnerLevel}` : ''}${opts.override ? `, override` : ''}) -> ${s.mode.padEnd(16)} [${s.decidedBy}]`);
}

const endpoints = new Set(cfg.mode_routing.modes.map(
  (m) => verificationEndpoint(m, skill, cfg).endpoint));
assert.equal(endpoints.size, 1, 'all modes must share one verification endpoint');
console.log('\nDemo OK: all four modes terminate at', [...endpoints][0]);
