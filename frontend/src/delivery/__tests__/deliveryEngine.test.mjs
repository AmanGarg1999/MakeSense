// LL-04 frontend delivery engine tests (node:test). Verifies the classifier,
// mode resolution, adaptive flip rule, and companion voice mirror the backend
// semantics against the SAME config/delivery_dial.json.
// Run: node --test frontend/src/delivery/__tests__/

import test from 'node:test';
import assert from 'node:assert/strict';
import { classifySegment, resolveMode, modeIsActive, evaluateFlipRule,
         generateBridge, generateBridgesMany } from '../deliveryEngine.js';
import { loadDialConfig } from '../dialConfig.js';

const cfg = loadDialConfig();

test('config loads with all sections', () => {
  for (const k of ['modes', 'track_defaults', 'segment_classifier', 'engagement', 'flip_rule', 'companion_voice']) {
    assert.ok(cfg[k], `missing ${k}`);
  }
});

test('classifier: explicit kind, markers, first-visit', () => {
  assert.equal(classifySegment({ kind: 'consolidation', title: 'Intro' }, cfg), 'consolidation');
  assert.equal(classifySegment({ title: 'Retrieval practice: scales' }, cfg), 'consolidation');
  assert.equal(classifySegment({ title: 'New concept: apertures' }, cfg), 'intake');
  assert.equal(classifySegment({ title: 'Mystery' }, cfg, 0), 'intake');
  assert.equal(classifySegment({ title: 'Mystery' }, cfg, 4), 'consolidation');
});

test('mode resolution: hobby intake passive, consolidation active', () => {
  const intake = resolveMode({ goalType: 'hobby' }, 'intake', { cfg });
  assert.equal(intake.modeClass, 'passive');
  const cons = resolveMode({ goalType: 'hobby' }, 'consolidation', { cfg });
  assert.equal(cons.modeClass, 'active');
});

test('mode resolution: escalation beats everything', () => {
  const d = resolveMode({ goalType: 'hobby' }, 'intake',
    { cfg, activeEscalation: { reason: 'passive_dropout' } });
  assert.equal(d.decidedBy, 'escalation');
  assert.equal(d.modeClass, 'active');
});

test('mode resolution: low energy keeps hobby intake passive with label', () => {
  const d = resolveMode({ goalType: 'hobby' }, 'intake', { cfg, energy: 1 });
  assert.equal(d.modeClass, 'passive');
  assert.ok(['energy_override', 'track_default'].includes(d.decidedBy));
});

const seg = (modeClass, sessionId, { abandoned = false, outcome = 'none', id = null } = {}) =>
  ({ id, modeClass, sessionId, abandoned, retrievalOutcome: outcome });

test('flip rule: not enough sessions -> silent', () => {
  const dec = evaluateFlipRule('guitar', [seg('passive', 's1', { abandoned: true })], cfg);
  assert.equal(dec.shouldFlip, false);
});

test('flip rule: passive dropout fires with evidence', () => {
  const segments = [];
  let i = 0;
  for (const s of ['s1', 's2', 's3', 's4']) segments.push(seg('passive', s, { abandoned: s !== 's1', id: ++i }));
  segments.push(seg('active', 's5', { id: ++i }));
  const dec = evaluateFlipRule('python', segments, cfg);
  assert.equal(dec.shouldFlip, true);
  assert.equal(dec.reason, 'passive_dropout');
  assert.ok(dec.evidence.passive_abandon_rate >= cfg.flip_rule.passive_abandon_rate_threshold);
  assert.ok(dec.evidence.thresholds);
});

test('flip rule: failed retrieval fires', () => {
  const segments = [1, 2, 3].map((n) => seg('passive', `s${n}`, { outcome: 'incorrect', id: n }));
  const dec = evaluateFlipRule('photography', segments, cfg);
  assert.equal(dec.shouldFlip, true);
  assert.equal(dec.reason, 'failed_retrieval');
});

test('flip rule: equal abandon in both modes does not dropout-flip', () => {
  const segments = [
    ...[1, 2].map((n) => seg('passive', `p${n}`, { abandoned: true, id: n })),
    ...[1, 2, 3].map((n) => seg('active', `a${n}`, { abandoned: true, id: n + 10 })),
  ];
  const dec = evaluateFlipRule('tennis', segments, cfg);
  assert.notEqual(dec.reason, 'passive_dropout');
});

// --- companion voice ---------------------------------------------------------

const mkLadder = (subs) => ({
  rungs: ['Novice', 'Competent', 'Proficient', 'Expert'].map((level_name, i) => ({
    level_index: i, level_name,
    sub_skills: subs.map((name) => ({ name, can_do_statements: [`can hold a ${name} routine end-to-end`] })),
  })),
});

test('voice: silent without ladder state', () => {
  assert.equal(generateBridge({ skillTag: 'x' }, {}, { rungs: [] }, { cfg }), null);
});

test('voice: gap callout cites score + can-do from state', () => {
  const mv = { grip: { score: 0.75 }, strumming: { score: 0.3 }, chord_changes: { score: 0.9 } };
  const b = generateBridge({ skillTag: 'guitar', currentLadderRung: 1 }, mv, mkLadder(['grip', 'strumming', 'chord_changes']), { cfg });
  assert.match(b.text, /strumming/);
  assert.match(b.text, /30%/);
  assert.equal(b.motivation, 'competence');
});

test('voice: 20+ distinct strings generated from state matrix', () => {
  const tracks = {
    guitar: ['grip', 'strumming', 'chord_changes'],
    python: ['syntax', 'functions', 'classes'],
    photography: ['exposure', 'focus', 'composition'],
  };
  const scoreSets = [[0.2, 0.4, 0.65], [0.85, 0.9, 0.7], [0.1, 0.2, 0.3],
    [0.62, 0.95, 0.88], [0, 0, 0], [0.75, 0.62, 0.7], [0.45, 0.82, 0.66], [0.28, 0.71, 0.93]];
  const seen = new Set();
  for (const [skill, subs] of Object.entries(tracks)) {
    for (let rung = 0; rung < 4; rung++) {
      for (const scores of scoreSets) {
        const mv = Object.fromEntries(subs.map((n, k) => [n, { score: scores[k] }]));
        const b = generateBridge({ skillTag: skill, currentLadderRung: rung }, mv, mkLadder(subs), { cfg });
        assert.ok(b);
        seen.add(b.text);
      }
    }
  }
  assert.ok(seen.size >= 20, `only ${seen.size} distinct`);
  for (const skill of Object.keys(tracks)) {
    assert.ok([...seen].some((t) => t.toLowerCase().includes(skill)), `${skill} never referenced`);
  }
});

test('voice: word budget respected in batch', () => {
  const out = generateBridgesMany(Array.from({ length: 5 }, () => [
    { skillTag: 'guitar', currentLadderRung: 0 },
    { grip: { score: 0.3 } }, mkLadder(['grip'])]), cfg);
  assert.equal(out.length, 5);
  for (const b of out) assert.ok(b.text.split(/\s+/).length <= cfg.companion_voice.max_bridge_words);
});
