// LL-04 delivery dial config loader.
// Single source of truth: config/delivery_dial.json at repo root (shared with
// services/event-tracker). Vite imports JSON natively; node --test uses import
// attributes. Fallback fetch for deployed builds where the JSON is served
// statically from /config/delivery_dial.json.

import cfg from '../../../config/delivery_dial.json' with { type: 'json' };

export function loadDialConfig() {
  return cfg;
}
