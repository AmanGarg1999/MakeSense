// LL-09d demo seed data for the Coach Insights dashboards.
//
// Route-level demo (per acceptance): /#/coach-insights?level=micro and
// ?level=undergrad (etc.) render each variant offline, no server needed.
// Shapes mirror the real payloads:
//   pathway  -> GET /api/pathways/active (LL-09a)
//   radar    -> CoachEngine.radar_update(state) (LL-09b)
//   heatmap  -> mastery ledger buckets at the level's timescale (levels.js)
//   insights -> level-specific widget data (LL-09d spec)
import { PATHWAY_LEVELS } from '../database/levels.js'

const day = (n) => new Date(Date.now() - n * 86400000).toISOString()

// one pathway envelope per level with a plausible curriculum + transcript
const CURRICULA = {
  micro: ['guitar:barre_chords', 'guitar:strum', 'guitar:rhythm', 'guitar:fingerstyle'],
  certificate: ['web:html_css', 'web:javascript', 'web:react', 'web:project_capstone'],
  undergrad: ['ug:math101', 'ug:cs101', 'ug:cs201', 'ug:stats210', 'ug:ethics105', 'ug:cs301',
    'ug:db401', 'ug:os402', 'ug:ml501', 'ug:capstone601'],
  masters: ['ms:research_methods', 'ms:lit_review', 'ms:thesis_proposal', 'ms:thesis_ch1',
    'ms:thesis_ch2', 'ms:thesis_defense'],
  phd: ['phd:comprehensive', 'phd:proposal', 'phd:ch1_literature', 'phd:ch2_method',
    'phd:ch3_results', 'phd:ch4_discussion', 'phd:defense'],
  mba: ['mba:finance_core', 'mba:marketing_cases', 'mba:org_behavior', 'mba:strategy_cases',
    'mba:leadership_lab', 'mba:capstone_integrator'],
}

const CREDITS = {
  micro: 0, certificate: 2.5, undergrad: 3, masters: 4, phd: 6, mba: 3,
}

function fakeTranscript(level, skills, fracDone, masteryFn) {
  const cut = Math.round(skills.length * fracDone)
  return skills.map((s, i) => i < cut
    ? {
        content_pack_id: s,
        mastery_score: masteryFn(i),
        completed_at: day((skills.length - i) * (level === 'micro' ? 2 : 21)),
        credential_issued: level !== 'micro' && i === cut - 1,
        credential_type: level !== 'micro' && i === cut - 1 ? `${level}_module_${i}` : null,
      }
    : { content_pack_id: s, mastery_score: 0, completed_at: null,
        credential_issued: false, credential_type: null })
}

// skill families for the radar (atomic vs cluster views come from granularity)
const RADAR_SKILLS = {
  micro: ['guitar:barre_chords', 'guitar:strum', 'guitar:rhythm', 'music:theory_basics',
    'music:ear_training', 'guitar:fingerstyle'],
  certificate: ['web:html_css', 'web:javascript', 'web:react', 'web:testing', 'design:ui', 'design:ux'],
  undergrad: ['cs:algorithms', 'cs:systems', 'math:calculus', 'math:stats', 'humanities:ethics', 'cs:ai'],
  masters: ['research:methods', 'research:writing', 'field:ml_theory', 'field:evaluation'],
  phd: ['research:theory', 'research:experiments', 'research:writing', 'teaching:mentoring',
    'service:reviewing', 'field:nlp'],
  mba: ['business:finance', 'business:strategy', 'people:leadership', 'people:negotiation',
    'ops:analytics', 'ops:supply_chain'],
}

const masteredFraction = { micro: 0.5, certificate: 0.62, undergrad: 0.44,
  masters: 0.55, phd: 0.4, mba: 0.68 }

function buildRadar(level) {
  // mirrors ll09b/coach_engine.py radar_update() client-side for the demo
  const skills = RADAR_SKILLS[level]
  const mastered = new Set(skills.slice(0, Math.round(skills.length * masteredFraction[level])))
  if (level === 'micro') {
    return { granularity: 'atomic_skills', threshold: 0.8,
      nodes: skills.map((s) => ({ id: s, label: s, mastered: mastered.has(s),
        mastery: mastered.has(s) ? 0.86 : 0.35 })) }
  }
  const clusters = new Map()
  for (const s of skills) {
    const fam = s.split(':')[0]
    if (!clusters.has(fam)) clusters.set(fam, [])
    clusters.get(fam).push(s)
  }
  return { granularity: 'competency_clusters', threshold: 0.7,
    nodes: [...clusters.entries()].sort().map(([fam, members]) => ({
      id: `cluster:${fam}`, label: fam, members,
      mastered: members.every((m) => mastered.has(m)),
      mastery: members.reduce((a, m) => a + (mastered.has(m) ? 0.86 : 0.35), 0) / members.length,
    })) }
}

function buildHeatmap(level) {
  // deterministic-ish mastery intensity per bucket at the level's timescale
  const scale = level === 'micro' ? 'days' : level === 'certificate' ? 'weeks' : 'semesters'
  const buckets = scale === 'days' ? 28 : scale === 'weeks' ? 16 : 6
  const labels = scale === 'days'
    ? Array.from({ length: buckets }, (_, i) => `D-${buckets - i}`)
    : scale === 'weeks'
      ? Array.from({ length: buckets }, (_, i) => `W${i + 1}`)
      : ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5', 'Sem 6']
  const values = Array.from({ length: buckets }, (_, i) => {
    const wave = Math.sin(i * 1.7 + PATHWAY_LEVELS.indexOf(level) * 2.3)
    return Math.max(0, Math.min(1, 0.45 + 0.5 * wave * (i / buckets + 0.4)))
  })
  return { scale, labels, values }
}

function buildInsights(level, skills) {
  switch (level) {
    case 'micro':
      return {
        progress_pct: 68,
        streak: 12,
        next_task: { skill: 'guitar:fingerstyle', concept: 'Travis picking pattern', est_minutes: 5 },
      }
    case 'certificate':
      return {
        completion_pct: 62,
        timeline: [
          { id: 'p1', label: 'Project: static site', state: 'done', week: 3 },
          { id: 'p2', label: 'Checkpoint: JS fundamentals', state: 'done', week: 6 },
          { id: 'p3', label: 'Project: React app', state: 'active', week: 9 },
          { id: 'p4', label: 'Peer review gate', state: 'upcoming', week: 11 },
        ],
        portfolio: skills.filter((_, i) => i % 2 === 0).map((s, i) => ({
          id: `pf-${i}`, title: s, thumb: '🖼️', updated: day(i * 9 + 2) })),
        peer_feedback: [
          { id: 'f1', author: 'priya.k', text: 'Clean component boundaries — nice job on the hooks refactor.', when: day(2) },
          { id: 'f2', author: 'dev.m', text: 'Consider extracting the data layer; strong overall structure.', when: day(5) },
          { id: 'f3', author: 'ana.r', text: 'Accessibility pass is thorough. Approved for gate.', when: day(9) },
        ],
      }
    case 'undergrad':
      return {
        gpa_trend: [
          { term: 'F23', gpa: 3.1 }, { term: 'S24', gpa: 3.25 }, { term: 'F24', gpa: 3.4 },
          { term: 'S25', gpa: 3.35 }, { term: 'F25', gpa: 3.55 }, { term: 'S26', gpa: 3.7 },
        ],
        credits: { earned: 78, required: 120 },
        audit: [
          { req: 'Composition I-II', done: true },
          { req: 'Calculus sequence', done: true },
          { req: 'CS core (4 courses)', done: true },
          { req: 'Upper-division electives (6)', done: false, progress: 0.5 },
          { req: 'Ethics requirement', done: false },
          { req: 'Capstone sequence', done: false },
        ],
        exams: [
          { course: 'CS 301 — Algorithms', when: day(-4), conf: 0.9 },
          { course: 'STAT 210 — Probability', when: day(-11), conf: 0.7 },
          { course: 'CS 401 — Databases', when: day(-25), conf: 0.5 },
        ],
      }
    case 'masters':
      return {
        milestones: [
          { label: 'Research proposal', state: 'done', date: day(140) },
          { label: 'Literature review', state: 'done', date: day(70) },
          { label: 'Qualifying exam', state: 'active', date: day(-14) },
          { label: 'Data collection', state: 'upcoming', date: day(-90) },
          { label: 'Thesis defense', state: 'upcoming', date: day(-260) },
        ],
        literature: [
          { area: 'Evaluation methods', coverage: 0.85 },
          { area: 'Representation learning', coverage: 0.6 },
          { area: 'Human factors', coverage: 0.3 },
          { area: 'Benchmark critiques', coverage: 0.72 },
        ],
        thesis_chapters: [
          { n: 1, title: 'Introduction', status: 'final' },
          { n: 2, title: 'Related Work', status: 'review' },
          { n: 3, title: 'Method', status: 'draft' },
          { n: 4, title: 'Experiments', status: 'outline' },
        ],
        publications: { submitted: 2, accepted: 1, workshops: 1 },
      }
    case 'phd':
      return {
        chapters: [
          { n: 1, title: 'Literature synthesis', pct: 100 },
          { n: 2, title: 'Formal framework', pct: 90 },
          { n: 3, title: 'Experiments I', pct: 55 },
          { n: 4, title: 'Experiments II', pct: 20 },
          { n: 5, title: 'Discussion', pct: 5 },
        ],
        citations: { nodes: 12, edges: 18, orphans: 2 },
        conferences: [
          { name: 'NeurIPS', deadline: day(-18), status: 'submitted' },
          { name: 'ICLR', deadline: day(-80), status: 'drafting' },
          { name: 'ACL', deadline: day(-140), status: 'watching' },
        ],
        advisor_meetings: [
          { when: day(7), notes: 'Ch3 experiment matrix approved; run ablations.' },
          { when: day(21), notes: 'Scope narrowing: drop Experiments II baseline.' },
          { when: day(35), notes: 'NeurIPS shepherding plan agreed.' },
        ],
      }
    case 'mba':
      return {
        cases: {
          domains: ['Finance', 'Strategy', 'Marketing', 'Ops', 'Leadership'],
          scores: [
            { student: 'You', row: [3.7, 3.4, 4.0, 3.1, 3.6] },
            { student: 'Cohort avg', row: [3.3, 3.5, 3.2, 3.4, 3.3] },
          ],
        },
        cohort_ranking: { percentile: 78, size: 240 },
        competencies: [
          { label: 'Strategic thinking', score: 0.78 },
          { label: 'Financial literacy', score: 0.66 },
          { label: 'Negotiation', score: 0.84 },
          { label: 'Team leadership', score: 0.9 },
          { label: 'Data decisioning', score: 0.6 },
          { label: 'Communication', score: 0.88 },
        ],
        capstone: { phase: 'Integration week 3/6', stakeholders: 2, gates_passed: 2, gates_total: 5 },
      }
    default:
      return {}
  }
}

/** Full demo state for one level: pathway envelope + radar + heatmap + widgets. */
export function seedForLevel(level) {
  const skills = CURRICULA[level] || CURRICULA.micro
  const pathway = {
    id: `seed-${level}`,
    user_id: 1,
    level,
    title: level === 'micro' ? 'Guitar fundamentals'
      : level === 'certificate' ? 'Full-stack web certificate'
      : level === 'undergrad' ? 'B.Sc. Computer Science'
      : level === 'masters' ? "M.Sc. Machine Learning"
      : level === 'phd' ? 'PhD Computational Linguistics'
      : 'MBA General Management',
    status: 'active',
    started_at: day(level === 'micro' ? 14 : 200),
    target_completion: null,
    completed_at: null,
    curriculum: skills.map((content_pack_id, sequence) => ({
      content_pack_id, sequence, required: true, credits: CREDITS[level],
    })),
    transcript: fakeTranscript(level, skills, masteredFraction[level],
      (i) => 0.72 + ((i * 37) % 25) / 100),
  }
  return {
    pathway,
    radar: buildRadar(level),
    heatmap: buildHeatmap(level),
    insights: buildInsights(level, skills),
  }
}

export const SEED_LEVELS = PATHWAY_LEVELS
