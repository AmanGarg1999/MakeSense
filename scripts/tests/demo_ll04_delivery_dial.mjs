// LL-04 acceptance demo: plays a demo track's session stream through the
// delivery engine and shows (a) the classifier switching modes per segment,
// (b) the adaptive flip rule firing on the telemetry pattern, (c) companion
// bridges generated from ladder/mastery state.
//
// Run: node scripts/tests/demo_ll04_delivery_dial.mjs

import assert from 'node:assert/strict';
import { classifySegment, resolveMode, evaluateFlipRule, generateBridge }
  from '../../frontend/src/delivery/deliveryEngine.js';
import { loadDialConfig } from '../../frontend/src/delivery/dialConfig.js';

const cfg = loadDialConfig();
const track = { id: 'track-demo-guitar', skill_tag: 'guitar', goal_type: 'hobby',
                current_ladder_rung: 1 };

// --- demo track: segments as the course player would emit them ---------------
const sessions = [
  { id: 's1', segments: [
    { title: 'New concept: the fretboard map', tags: ['new_concept'] },
    { title: 'Watch: chord shapes in action', content_type: 'video' } ] },
  { id: 's2', segments: [
    { title: 'Explanation: why barre chords buzz', tags: ['explanation'] },
    { title: 'Read: finger pressure basics', content_type: 'read' } ] },
  { id: 's3', segments: [
    { title: 'Practice: chord changes drill', tags: ['practice'] },
    { title: 'Overview recap', tags: ['recap'] } ] },
  { id: 's4', segments: [
    { title: 'Revisit: strumming patterns', tags: ['review'] } ] },
];

// Simulated engagement: passive intake segments were abandoned early,
// active consolidation segments were completed.
const abandonPattern = { s1: [true, true], s2: [true, false], s3: [false, false], s4: [false] };

console.log('== LL-04 demo track: mode decisions per segment ==\n');
const telemetry = [];
let id = 0;
for (const s of sessions) {
  s.segments.forEach((seg, idx) => {
    const kind = classifySegment(seg, cfg);
    const decision = resolveMode(track, kind, { cfg });
    const abandoned = abandonPattern[s.id][idx];
    console.log(`  [${s.id}.${idx}] ${kind.padEnd(13)} ${decision.mode.padEnd(22)} (${decision.modeClass})  <- ${decision.reason}${abandoned ? '  ⚠ abandoned' : ''}`);
    telemetry.push({ id: ++id, session_id: s.id, mode_class: decision.modeClass,
                     abandoned, retrieval_outcome: 'none' });
  });
}

console.log('\n== Adaptive flip rule on this telemetry pattern ==\n');
const flip = evaluateFlipRule('guitar', telemetry, cfg);
assert.equal(flip.shouldFlip, true, 'flip rule must fire on this pattern');
assert.equal(flip.reason, 'passive_dropout');
console.log(`  FLIP -> guitar escalated to ACTIVE for next ${cfg.flip_rule.escalation_sessions} sessions`);
console.log(`  evidence: passive_abandon_rate=${flip.evidence.passive_abandon_rate} (threshold ${flip.evidence.thresholds.passive_abandon_rate_threshold}), active_abandon_rate=${flip.evidence.active_abandon_rate}, sessions=${flip.evidence.sessions_observed}`);
console.log(`  sample segments: [${flip.evidence.sample_segment_ids.join(', ')}]`);

// Next segment under escalation -> active delivery, decided_by=escalation
const underEsc = resolveMode(track, 'intake', { cfg, activeEscalation: { reason: flip.reason } });
console.log(`\n  next intake segment under escalation: ${underEsc.mode} (${underEsc.modeClass}, ${underEsc.decidedBy})`);
assert.equal(underEsc.modeClass, 'active');

console.log('\n== Companion bridges from ladder/mastery state ==\n');
const ladder = { rungs: [
  { level_index: 0, level_name: 'Novice', sub_skills: [
    { name: 'hold the pick', can_do_statements: ['hold the pick without tension during a 2-minute drill'] }] },
  { level_index: 1, level_name: 'Competent', sub_skills: [
    { name: 'chord changes', can_do_statements: ['switch G to D mid-phrase without stopping'] },
    { name: 'strumming', can_do_statements: ['keep a steady down-up pattern at 90 bpm'] }] },
  { level_index: 2, level_name: 'Proficient', sub_skills: [
    { name: 'barre chords', can_do_statements: ['play an F-major barre chord cleanly for a full song section'] }] },
] };
for (const mv of [
  { 'chord changes': { score: 0.82 }, 'strumming': { score: 0.3 } },   // gap
  { 'chord changes': { score: 0.7 }, 'strumming': { score: 0.65 } },   // near
  { 'chord changes': { score: 0.9 }, 'strumming': { score: 0.88 } },   // strength
]) {
  const b = generateBridge(track, mv, ladder, cfg);
  console.log(`  [${b.motivation}] ${b.text}`);
}

console.log('\nDemo OK: classifier switched modes, flip rule fired with evidence, bridges state-sourced.');
