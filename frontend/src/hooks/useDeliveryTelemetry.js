// LL-04 session telemetry: mode, engagement signals (pause/abandon/dwell),
// and retrieval outcomes for each played segment → POST to event-tracker
// (/api/delivery/segments). The server runs the adaptive flip rule on ingest.
// Falls back to localStorage buffering when the service is unreachable so
// offline sessions still emit telemetry on next sync.

import { useEffect, useRef, useCallback, useState } from 'react';
import { classifySegment, resolveMode } from '../delivery/deliveryEngine.js';
import { loadDialConfig } from '../delivery/dialConfig.js';

const EVENT_TRACKER = import.meta.env?.VITE_EVENT_TRACKER_URL || 'http://localhost:8000';
const BUFFER_KEY = 'makesense_delivery_telemetry_buffer';

export function useDeliveryTelemetry({ track, trackId, skillTag, sessionId, energy } = {}) {
  const cfg = useRef(loadDialConfig());
  const buffer = useRef(loadBuffer());
  const [flipCheck, setFlipCheck] = useState(null);
  const [escalation, setEscalation] = useState(null);

  const flush = useCallback(async () => {
    if (!buffer.current.length) return;
    const batch = buffer.current.splice(0, 50);
    try {
      const res = await fetch(`${EVENT_TRACKER}/api/delivery/telemetry/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segments: batch }),
      });
      if (!res.ok) throw new Error(`telemetry flush failed: ${res.status}`);
      const data = await res.json();
      const last = data.results?.[data.results.length - 1]?.flip_check;
      if (last) setFlipCheck(last);
      saveBuffer(buffer.current);
    } catch {
      buffer.current.unshift(...batch);
      saveBuffer(buffer.current);
    }
  }, []);

  // Periodic + unload flush
  useEffect(() => {
    const t = setInterval(flush, 15000);
    const onUnload = () => {
      if (buffer.current.length) {
        navigator.sendBeacon?.(`${EVENT_TRACKER}/api/delivery/telemetry/batch`,
          JSON.stringify({ segments: buffer.current }));
      }
    };
    window.addEventListener('beforeunload', onUnload);
    return () => { clearInterval(t); window.removeEventListener('beforeunload', onUnload); flush(); };
  }, [flush]);

  const decide = useCallback((segment, priorVisits = 0) => {
    const kind = classifySegment(segment, cfg.current, priorVisits);
    const decision = resolveMode(
      { goalType: track?.goal_type || track?.goalType || 'hobby' },
      kind, { cfg: cfg.current, activeEscalation: escalation, energy });
    return { kind, ...decision };
  }, [track, escalation, energy]);

  const recordSegment = useCallback((seg) => {
    buffer.current.push({
      user_id: Number(localStorage.getItem('makesense_user_id') || 1),
      track_id: trackId, skill_tag: skillTag, session_id: sessionId,
      goal_type: track?.goal_type || 'hobby',
      ...seg,
    });
    if (buffer.current.length >= 20) flush();
  }, [trackId, skillTag, sessionId, track, flush]);

  return { decide, recordSegment, flipCheck, escalation, setEscalation };
}

// --- engagement tracking helpers ------------------------------------------------
// Call attachEngagement(el) on a segment container; returns {stop} with dwell
// and pause accounting (visibility/blur-aware).

export function trackEngagement(el, { onSignal, dwellFloorSeconds = 8 } = {}) {
  let visibleMs = 0, pausedMs = 0, lastTick = Date.now(), paused = false;
  const start = Date.now();
  const timer = setInterval(() => {
    const now = Date.now();
    const delta = now - lastTick;
    lastTick = now;
    if (paused) pausedMs += delta; else visibleMs += delta;
  }, 250);
  const onVis = () => { paused = document.hidden; };
  const onBlur = () => { paused = true; };
  const onFocus = () => { paused = false; };
  document.addEventListener('visibilitychange', onVis);
  window.addEventListener('blur', onBlur);
  window.addEventListener('focus', onFocus);

  return {
    stop() {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      const dwell = Math.round(visibleMs / 1000);
      const abandoned = dwell < (el?.dataset.expectedSeconds
        ? Math.min(el.dataset.expectedSeconds, 15) : 15)
        && !el?.dataset.completed;
      onSignal?.({ dwell_seconds: dwell, paused_seconds: Math.round(pausedMs / 1000), abandoned,
                   below_dwell_floor: dwell < dwellFloorSeconds });
    },
  };
}

function loadBuffer() {
  try { return JSON.parse(localStorage.getItem(BUFFER_KEY) || '[]'); } catch { return []; }
}
function saveBuffer(items) {
  try { localStorage.setItem(BUFFER_KEY, JSON.stringify(items)); } catch { /* quota */ }
}
