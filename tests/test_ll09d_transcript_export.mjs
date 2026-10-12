// LL-09d acceptance: JSON transcript export (frontend builder).
//
// Runs on plain node (no vitest configured in this repo):
//   node tests/test_ll09d_transcript_export.mjs
//
// The shared fixture (tests/fixtures/ll09d_transcript_fixture.json) is also
// run through the Python builder in tests/test_ll09d_export.py — both sides
// must agree on every number (cross-language contract for the export).

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  buildTranscriptDocument,
  letterGrade,
  TRANSCRIPT_SCHEMA,
} from '../frontend/src/lib/transcriptExport.js'
import {
  PATHWAY_LEVELS,
  DEGREE_LEVELS,
  RADAR_GRANULARITY,
  HEATMAP_TIMESCALE,
  LEVEL_DASHBOARDS,
} from '../frontend/src/database/levels.js'
import { seedForLevel, SEED_LEVELS } from '../frontend/src/lib/coachInsightsSeed.js'

const here = dirname(fileURLToPath(import.meta.url))
const fixture = JSON.parse(
  readFileSync(join(here, 'fixtures', 'll09d_transcript_fixture.json'), 'utf8'))

let passed = 0
const test = (name, fn) => {
  try {
    fn()
    passed += 1
    console.log(`  ok - ${name}`)
  } catch (err) {
    console.error(`  FAIL - ${name}\n    ${err.message}`)
    process.exitCode = 1
  }
}

console.log('LL-09d transcript export (frontend builder)')

// ---------------------------------------------------------------------------
test('fixture contract: sums, GPA, grades match the cross-language fixture', () => {
  const doc = buildTranscriptDocument({
    pathway: fixture.pathway,
    transcript: fixture.transcript,
    levelRows: [fixture.level_row],
  })
  const exp = fixture.expected
  assert.equal(doc.schema, exp.schema)
  assert.equal(doc.summary.total_records, exp.total_records)
  assert.equal(doc.summary.completed, exp.completed)
  assert.equal(doc.summary.completion_pct, exp.completion_pct)
  assert.equal(doc.summary.credits_required, exp.credits_required)
  assert.equal(doc.summary.credits_earned, exp.credits_earned)
  assert.equal(doc.summary.gpa, exp.gpa)
  assert.equal(doc.summary.credentials.length, exp.credential_count)
  assert.equal(doc.extra_entries.length, exp.extra_count)
  for (const [pack, letter] of Object.entries(exp.grade_letters)) {
    const rec = doc.records.find((r) => r.content_pack_id === pack)
    assert.equal(rec.grade_letter, letter, `${pack} letter`)
  }
})

test('schema constant is the shared transcript/v1 id', () => {
  assert.equal(TRANSCRIPT_SCHEMA, 'makesense.transcript/v1')
})

test('unfinished curriculum records export as nulls, not zeros', () => {
  const doc = buildTranscriptDocument({ pathway: fixture.pathway, transcript: fixture.transcript })
  const pending = doc.records.find((r) => r.content_pack_id === 'capstone401')
  assert.equal(pending.completed, false)
  assert.equal(pending.mastery_score, null)
  assert.equal(pending.grade_letter, null)
  assert.equal(pending.completed_at, null)
})

test('transcript row for a non-curriculum pack lands in extra_entries flagged', () => {
  const doc = buildTranscriptDocument({ pathway: fixture.pathway, transcript: fixture.transcript })
  const extra = doc.extra_entries.find((e) => e.content_pack_id === 'dropped_pack')
  assert.ok(extra, 'dropped_pack present in extra_entries')
  assert.equal(extra.flag, 'not_in_curriculum')
})

test('pathway without level refuses to export (TypeError)', () => {
  assert.throws(() => buildTranscriptDocument({ pathway: { title: 'nope' } }), TypeError)
  assert.throws(() => buildTranscriptDocument({ pathway: null }), TypeError)
})

test('letter grade ladder matches the Python mirror thresholds', () => {
  const cases = [[1, 'A'], [0.93, 'A'], [0.92, 'A-'], [0.87, 'A-'], [0.86, 'B+'],
    [0.8, 'B+'], [0.79, 'B'], [0.73, 'B'], [0.72, 'B-'], [0.67, 'B-'], [0.66, 'C+'],
    [0.6, 'C+'], [0.59, 'C'], [0.53, 'C'], [0.52, 'D'], [0.4, 'D'], [0.39, 'F'], [0, 'F']]
  for (const [m, letter] of cases) assert.equal(letterGrade(m), letter, `mastery ${m}`)
})

test('zero-credit pathway exports GPA null without divide-by-zero', () => {
  const doc = buildTranscriptDocument({
    pathway: { id: 'x', level: 'micro', curriculum: [{ content_pack_id: 'a', credits: 0 }], transcript: null },
    transcript: [{ content_pack_id: 'a', mastery_score: 0.9, completed_at: new Date().toISOString() }],
  })
  assert.equal(doc.summary.gpa, null)
  assert.equal(doc.summary.credits_earned, 0)
})

// ---------------------------------------------------------------------------
// vocabulary + seed integrity (the dashboards' contract surface)
test('levels.js extends, never re-declares: 6 canonical levels, 5 degrees', () => {
  assert.deepEqual(PATHWAY_LEVELS, ['micro', 'certificate', 'undergrad', 'masters', 'phd', 'mba'])
  assert.deepEqual(DEGREE_LEVELS, PATHWAY_LEVELS.filter((l) => l !== 'micro'))
})

test('radar granularity + heatmap timescale cover every canonical level', () => {
  for (const lvl of PATHWAY_LEVELS) {
    assert.ok(RADAR_GRANULARITY[lvl], `radar granularity for ${lvl}`)
    assert.ok(HEATMAP_TIMESCALE[lvl], `heatmap timescale for ${lvl}`)
    assert.equal(RADAR_GRANULARITY.micro, 'atomic_skills')
    if (lvl !== 'micro') assert.equal(RADAR_GRANULARITY[lvl], 'competency_clusters')
  }
  assert.equal(HEATMAP_TIMESCALE.micro, 'days')
  assert.equal(HEATMAP_TIMESCALE.certificate, 'weeks')
  assert.equal(HEATMAP_TIMESCALE.undergrad, 'semesters')
})

test('every level dashboard includes radar + heatmap; degree ones include transcript export', () => {
  assert.deepEqual(SEED_LEVELS, PATHWAY_LEVELS)
  for (const lvl of PATHWAY_LEVELS) {
    const widgets = LEVEL_DASHBOARDS[lvl]
    assert.ok(widgets.includes('skill_radar') && widgets.includes('mastery_heatmap'))
    const isDegree = DEGREE_LEVELS.includes(lvl)
    assert.equal(widgets.includes('transcript_export'), isDegree, `transcript_export on ${lvl}`)
  }
})

test('seed data feeds the exporter cleanly for every level (demo variant renders)', () => {
  for (const lvl of PATHWAY_LEVELS) {
    const seed = seedForLevel(lvl)
    assert.equal(seed.pathway.level, lvl)
    assert.ok(seed.insights, `insights for ${lvl}`)
    const doc = buildTranscriptDocument({
      pathway: seed.pathway,
      transcript: seed.pathway.transcript,
    })
    assert.equal(doc.schema, TRANSCRIPT_SCHEMA)
    assert.ok(doc.summary.total_records > 0)
  }
})

console.log(`\n${passed} LL-09d frontend export checks passed${process.exitCode ? ' (FAILURES above)' : ''}`)
