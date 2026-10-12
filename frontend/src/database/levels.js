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
