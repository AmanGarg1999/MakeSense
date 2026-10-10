// LL-08 interest/mode config loader.
// Single source of truth: config/interest_drift.json at repo root (shared with
// services/event-tracker). Vite imports JSON natively; node --test uses import
// attributes.

import cfg from '../../../config/interest_drift.json' with { type: 'json' };

export function loadInterestConfig() {
  return cfg;
}
