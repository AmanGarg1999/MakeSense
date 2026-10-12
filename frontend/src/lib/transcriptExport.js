// LL-09d: JSON transcript export for degree pathways.
//
// Turns the LL-09a API payloads (GET /api/pathways/{id},
// GET /api/pathways/{id}/transcript, GET /api/pathways/levels) into a
// canonical, schema-versioned transcript document. Pure functions — this
// module runs unchanged in the browser (download button) and in node
// (tests/test_ll09d_transcript_export.mjs), which is the acceptance surface
// for "tests for the transcript export".
//
// PDF export reuses the SAME document via ll09d/export_api.py
// (POST /api/export/transcript) so the two formats can never disagree.

export const TRANSCRIPT_SCHEMA = 'makesense.transcript/v1'

const num = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const iso = (v) => {
  if (v == null) return null
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

/**
 * Build the canonical transcript document for one pathway.
 *
 * @param {object}       input
 * @param {object}       input.pathway      learning_pathways row + curriculum
 *                                          (GET /api/pathways/{id} shape; a
 *                                          level_metadata sub-object wins)
 * @param {object[]|null} input.transcript  user_transcript rows
 *                                          (GET /api/pathways/{id}/transcript)
 * @param {object[]|null} input.levelRows  level_metadata rows (GET /api/pathways/levels)
 * @returns canonical transcript document
 * @throws  TypeError on a pathway without a canonical level (never export garbage)
 */
export function buildTranscriptDocument({ pathway, transcript = null, levelRows = null }) {
  if (!pathway || typeof pathway !== 'object') {
    throw new TypeError('buildTranscriptDocument: pathway object required')
  }
  const level = pathway.level
  if (!level || typeof level !== 'string') {
    throw new TypeError(`buildTranscriptDocument: pathway has no level (cannot export)`)
  }

  // Level facts: prefer the pathway's embedded row, fall back to the levels
  // directory, else nulls (a micro badge pathway legitimately has no credits).
  const levelRow =
    pathway.level_metadata ??
    (Array.isArray(levelRows) ? levelRows.find((r) => r && r.level === level) : null) ??
    null

  const curriculum = Array.isArray(pathway.curriculum) ? pathway.curriculum : []
  const entries = Array.isArray(transcript) ? transcript : []

  // Join transcript rows onto curriculum by content_pack_id; rows for packs
  // no longer in the curriculum are kept in `extra_entries` (audit trail).
  const byPack = new Map()
  for (const e of entries) {
    if (e && e.content_pack_id != null) byPack.set(e.content_pack_id, e)
  }

  let earnedCredits = 0
  let completedCount = 0
  let weightedSum = 0
  let weightTotal = 0

  const records = curriculum.map((item) => {
    const credit = num(item.credits)
    const entry = byPack.get(item.content_pack_id)
    const done = Boolean(entry && entry.completed_at != null)
    const mastery = entry ? num(entry.mastery_score) : 0
    if (done) {
      completedCount += 1
      earnedCredits += credit
      weightedSum += mastery * credit
      weightTotal += credit
    }
    return {
      content_pack_id: item.content_pack_id,
      sequence: item.sequence == null ? null : Number(item.sequence),
      required: item.required !== false,
      credits: credit,
      completed: done,
      completed_at: entry ? iso(entry.completed_at) : null,
      mastery_score: done ? mastery : null,
      // 4.0-scale grade for degree transcripts; null when no grade weight
      grade_points: done ? Math.round((mastery * 4) * 100) / 100 : null,
      grade_letter: done ? letterGrade(mastery) : null,
      credential_issued: entry ? Boolean(entry.credential_issued) : false,
      credential_type: entry && entry.credential_issued ? entry.credential_type ?? null : null,
    }
  })

  // curriculum-external transcript entries (dropped packs) still count as
  // evidence but are flagged so reviewers see the mismatch.
  const inCurriculum = new Set(curriculum.map((c) => c.content_pack_id))
  const extraEntries = entries
    .filter((e) => e && e.content_pack_id != null && !inCurriculum.has(e.content_pack_id))
    .map((e) => ({
      content_pack_id: e.content_pack_id,
      completed: e.completed_at != null,
      completed_at: iso(e.completed_at),
      mastery_score: num(e.mastery_score),
      credential_issued: Boolean(e.credential_issued),
      credential_type: e.credential_type ?? null,
      flag: 'not_in_curriculum',
    }))

  const totalCredits = curriculum.reduce((s, c) => s + num(c.credits), 0)
  const gpa = weightTotal > 0 ? Math.round((weightedSum / weightTotal) * 4 * 100) / 100 : null
  const completionPct = curriculum.length
    ? Math.round((completedCount / curriculum.length) * 1000) / 10
    : 0

  const credentials = records
    .concat(extraEntries)
    .filter((r) => r.credential_issued)
    .map((r) => ({ content_pack_id: r.content_pack_id, credential_type: r.credential_type }))

  return {
    schema: TRANSCRIPT_SCHEMA,
    generated_at: new Date().toISOString(),
    pathway: {
      id: pathway.id ?? null,
      user_id: pathway.user_id ?? null,
      level,
      title: pathway.title ?? null,
      status: pathway.status ?? null,
      started_at: iso(pathway.started_at),
      target_completion: pathway.target_completion ?? null,
      completed_at: iso(pathway.completed_at),
    },
    program: levelRow
      ? {
          typical_duration_weeks: levelRow.typical_duration_weeks ?? null,
          credit_system: levelRow.credit_system ?? null,
          assessment_type: levelRow.assessment_type ?? null,
          mentor_model: levelRow.mentor_model ?? null,
          recap_interval_days: levelRow.recap_interval_days ?? null,
        }
      : null,
    summary: {
      total_records: records.length,
      completed: completedCount,
      completion_pct: completionPct,
      credits_required: Math.round(totalCredits * 100) / 100,
      credits_earned: Math.round(earnedCredits * 100) / 100,
      gpa, // credit-weighted, 4.0 scale; null if no graded credit records
      credentials,
    },
    records,
    extra_entries: extraEntries,
  }
}

// mastery [0,1] -> letter on a 4.0 scale (A >= .93, A- >= .87, B+ >= .80, ...)
export function letterGrade(mastery) {
  const m = num(mastery)
  if (m >= 0.93) return 'A'
  if (m >= 0.87) return 'A-'
  if (m >= 0.8) return 'B+'
  if (m >= 0.73) return 'B'
  if (m >= 0.67) return 'B-'
  if (m >= 0.6) return 'C+'
  if (m >= 0.53) return 'C'
  if (m >= 0.4) return 'D'
  return 'F'
}

/** Trigger a browser download of the transcript as pretty-printed JSON. */
export function downloadTranscriptJson(doc, filename) {
  const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `transcript-${doc.pathway.level}-${doc.pathway.id ?? 'export'}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
