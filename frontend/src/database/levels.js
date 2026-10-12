// Canonical level vocabulary for multi-level learning pathways (LL-09a).
// Single source of truth in the frontend; mirrored by
// server/pathway_service.py PATHWAY_LEVELS and the CHECK constraints in
// server/migrations/009_learning_pathways.sql. LL-09b/c/d must extend here,
// not re-declare.
export const PATHWAY_LEVELS = [
  'micro',
  'certificate',
  'undergrad',
  'masters',
  'phd',
  'mba',
]

export const PATHWAY_STATUSES = ['active', 'paused', 'completed', 'archived']

export const LEVEL_LABELS = {
  micro: 'Micro-learning',
  certificate: 'Certificate',
  undergrad: 'Undergraduate',
  masters: 'Master\u2019s',
  phd: 'PhD',
  mba: 'MBA',
}

export const isValidPathwayLevel = (level) => PATHWAY_LEVELS.includes(level)

// ---------------------------------------------------------------------------
// LL-09d: Coach Insights UI vocabulary (extends, never re-declares, the enum
// above). Mirrors ll09b/level_config.py radar_granularity and the level
// metadata contract from LL-09a — keep in sync if pedagogy templates change.
// ---------------------------------------------------------------------------

export const DEGREE_LEVELS = ['certificate', 'undergrad', 'masters', 'phd', 'mba']

export const isDegreeLevel = (level) => DEGREE_LEVELS.includes(level)

// Skill radar granularity (LL-09b radar_update contract):
// micro -> one node per atomic skill; degrees -> competency-cluster nodes.
export const RADAR_GRANULARITY = {
  micro: 'atomic_skills',
  certificate: 'competency_clusters',
  undergrad: 'competency_clusters',
  masters: 'competency_clusters',
  phd: 'competency_clusters',
  mba: 'competency_clusters',
}

// Mastery heatmap time-scale: days (micro) -> weeks (cert) -> semesters (degree).
export const HEATMAP_TIMESCALE = {
  micro: 'days',
  certificate: 'weeks',
  undergrad: 'semesters',
  masters: 'semesters',
  phd: 'semesters',
  mba: 'semesters',
}

// Widgets rendered by the Coach Insights dashboard per level (LL-09d spec).
export const LEVEL_DASHBOARDS = {
  micro: ['progress_ring', 'streak_counter', 'next_micro_task', 'skill_radar', 'mastery_heatmap'],
  certificate: ['project_timeline', 'portfolio_gallery', 'peer_feedback_wall', 'completion_pct', 'skill_radar', 'mastery_heatmap', 'transcript_export'],
  undergrad: ['gpa_trend', 'credit_progress', 'degree_audit', 'exam_calendar', 'skill_radar', 'mastery_heatmap', 'transcript_export'],
  masters: ['milestone_tracker', 'literature_map', 'thesis_chapters', 'publication_count', 'skill_radar', 'mastery_heatmap', 'transcript_export'],
  phd: ['dissertation_chapters', 'citation_network', 'conference_timeline', 'advisor_meeting_log', 'skill_radar', 'mastery_heatmap', 'transcript_export'],
  mba: ['case_matrix', 'cohort_ranking', 'leadership_radar', 'capstone_integrator', 'skill_radar', 'mastery_heatmap', 'transcript_export'],
}
