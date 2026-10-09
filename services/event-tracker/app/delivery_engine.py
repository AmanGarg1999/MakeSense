"""LL-04 delivery engine: segment classification, mode resolution, adaptive
flip rule, and companion-voice generation.

All thresholds come from config/delivery_dial.json (see dial_config.load_config)
— never hardcoded. Persistence is dependency-injected: pass an asyncpg-style
connection/pool with fetch/fetchrow/execute, or use the pure-logic functions
(classify_segment, resolve_mode, evaluate_flip_rule, generate_bridge) directly.

Telemetry + escalation state key off LL-02's track IDs and ladder state
(skill_tracks.id, skill_ladders.level_index / sub_skills).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from app.dial_config import load_config

# ---------------------------------------------------------------------------
# Segment classifier (intake vs consolidation)
# ---------------------------------------------------------------------------


def classify_segment(segment: dict[str, Any], cfg: Optional[dict] = None,
                     prior_visits: int = 0) -> str:
    """Return 'intake' or 'consolidation' for a segment descriptor.

    Signals used (in priority order):
    1. explicit segment['kind'] if already classified
    2. consolidation markers in title/tags/type (practice, retrieval, recap...)
    3. intake markers (new_concept, first_exposure, explain, demo...)
    4. first-visit heuristic: 0 prior visits + no markers -> intake
    """
    cfg = cfg or load_config()
    clf = cfg["segment_classifier"]

    kind = (segment.get("kind") or "").lower()
    if kind in ("intake", "consolidation"):
        return kind

    haystack = " ".join([
        str(segment.get("title", "")),
        str(segment.get("content_type", "")),
        str(segment.get("node_type", "")),
        " ".join(str(t) for t in segment.get("tags", [])),
    ]).lower()

    for marker in clf["consolidation_markers"]:
        if marker in haystack:
            return "consolidation"
    for marker in clf["intake_markers"]:
        if marker in haystack:
            return "intake"

    if prior_visits == 0 and clf.get("first_visit_is_intake", True):
        return "intake"
    return "consolidation"


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------


def mode_is_active(mode: str, cfg: Optional[dict] = None) -> bool:
    cfg = cfg or load_config()
    return mode in cfg["modes"]["active"]


@dataclass
class ModeDecision:
    mode: str
    mode_class: str          # 'passive' | 'active'
    decided_by: str          # track_default|classifier|escalation|energy_override
    reason: str


def resolve_mode(track: dict[str, Any], segment_kind: str,
                 cfg: Optional[dict] = None,
                 active_escalation: Optional[dict] = None,
                 energy: Optional[int] = None) -> ModeDecision:
    """Decide the delivery mode for one segment.

    Precedence: escalation (flip rule) > energy override (low energy -> passive
    intake) > segment-kind classifier default > track default mode.
    """
    cfg = cfg or load_config()
    goal_type = track.get("goal_type", "hobby")
    defaults = cfg["track_defaults"].get(
        goal_type, cfg["track_defaults"][sorted(cfg["track_defaults"])[0]])

    if active_escalation:
        mode = _pick_active_mode(segment_kind, cfg)
        return ModeDecision(mode, "active", "escalation",
                            active_escalation.get("reason", "flip_rule"))

    # Low energy during intake -> passive scaffold (autonomy-preserving).
    if (energy is not None
            and energy <= cfg.get("energy_overrides", {}).get("energy_max", 2)
            and segment_kind == "intake"):
        mode = defaults["intake_mode"]
        if not mode_is_active(mode, cfg):
            return ModeDecision(mode, "passive", "energy_override",
                                f"energy={energy}, intake stretch")
        # default intake is active; honor it, classifier path below

    if segment_kind == "intake":
        mode = defaults["intake_mode"]
        decided = "track_default"
    elif segment_kind == "consolidation":
        mode = defaults["consolidation_mode"]
        decided = "track_default"
    else:
        mode = defaults["default_mode"]
        decided = "track_default"

    return ModeDecision(mode, "active" if mode_is_active(mode, cfg) else "passive",
                        decided, f"{goal_type} default for {segment_kind}")


def _pick_active_mode(segment_kind: str, cfg: dict) -> str:
    """An active mode appropriate to the segment kind (escalation target)."""
    if segment_kind == "consolidation":
        return "retrieval_prompt"
    return "predict_before_reveal"


# ---------------------------------------------------------------------------
# Adaptive flip rule
# ---------------------------------------------------------------------------


@dataclass
class FlipDecision:
    skill_tag: str
    should_flip: bool
    reason: Optional[str] = None        # 'passive_dropout' | 'failed_retrieval'
    evidence: dict[str, Any] = field(default_factory=dict)


def evaluate_flip_rule(skill_tag: str, segments: list[dict[str, Any]],
                       cfg: Optional[dict] = None) -> FlipDecision:
    """Given the recent delivery_segments rows for one skill (dicts with keys
    mode_class, abandoned, retrieval_outcome, session_id), decide whether to
    escalate that skill to active delivery.

    Two independent triggers, thresholds from config:
    - passive_dropout: over sessions with >= min_sessions_per_skill of passive
      segments, passive-abandon rate >= passive_abandon_rate_threshold
      while active-segment abandon rate stays below it.
    - failed_retrieval: >= failed_retrieval_count_threshold 'incorrect'
      retrieval outcomes across sessions.
    """
    cfg = cfg or load_config()
    fr = cfg["flip_rule"]

    passive = [s for s in segments if s.get("mode_class") == "passive"]
    active = [s for s in segments if s.get("mode_class") == "active"]

    sessions = {s.get("session_id") for s in segments if s.get("session_id")}
    evidence_common = {
        "sessions_observed": len(sessions),
        "passive_segments": len(passive),
        "active_segments": len(active),
        "thresholds": {
            "min_sessions_per_skill": fr["min_sessions_per_skill"],
            "passive_abandon_rate_threshold": fr["passive_abandon_rate_threshold"],
            "failed_retrieval_count_threshold": fr["failed_retrieval_count_threshold"],
        },
    }

    if len(sessions) < fr["min_sessions_per_skill"]:
        return FlipDecision(skill_tag, False,
                            evidence={**evidence_common,
                                      "note": "below min_sessions_per_skill"})

    # Trigger 1: passive-correlated drop-off
    if passive:
        passive_abandons = [s for s in passive if s.get("abandoned")]
        passive_rate = len(passive_abandons) / len(passive)
        active_rate = (len([s for s in active if s.get("abandoned")]) / len(active)) if active else 0.0
        if (passive_rate >= fr["passive_abandon_rate_threshold"]
                and passive_rate > active_rate):
            return FlipDecision(skill_tag, True, "passive_dropout", evidence={
                **evidence_common,
                "passive_abandon_rate": round(passive_rate, 3),
                "active_abandon_rate": round(active_rate, 3),
                "sample_segment_ids": [s.get("id") for s in passive_abandons][:10],
            })

    # Trigger 2: failed later retrieval on this skill
    failed = [s for s in segments
              if s.get("retrieval_outcome") == "incorrect"
              and s.get("mode_class") == "passive"]
    failed_any = [s for s in segments if s.get("retrieval_outcome") == "incorrect"]
    if len(failed_any) >= fr["failed_retrieval_count_threshold"]:
        return FlipDecision(skill_tag, True, "failed_retrieval", evidence={
            **evidence_common,
            "failed_retrieval_count": len(failed_any),
            "failed_after_passive_count": len(failed),
            "sample_segment_ids": [s.get("id") for s in failed_any][:10],
        })

    return FlipDecision(skill_tag, False, evidence=evidence_common)


# ---------------------------------------------------------------------------
# Companion voice layer
# ---------------------------------------------------------------------------


def _can_do_phrase(statement):
    """Render a 'can X' can-do statement as a bare verb phrase for templates."""
    if not statement:
        return None
    import re
    return re.sub(r'^can\s+(do\s+)?', '', statement, count=1, flags=re.I)


def generate_bridge(track_state: dict[str, Any], mastery_vector: dict[str, Any],
                    ladder: dict[str, Any], cfg: Optional[dict] = None,
                    next_goal: Optional[str] = None) -> Optional[dict[str, str]]:
    """Generate ONE narrative bridge from actual ladder/mastery state.

    track_state: {skill_tag, goal_type, current_ladder_rung, sessions_remaining_estimate?}
    mastery_vector: {sub_skill: {score: 0..1, last_seen?}}  (LL-02 format)
    ladder: {rungs: [{level_index, level_name, sub_skills: [{name, can_do_statements: [...]}]}]}

    Returns {text, motivation} or None when there is no state to speak from
    (the companion stays silent rather than emitting generic filler —
    non-negotiable #6).
    """
    cfg = cfg or load_config()
    voice = cfg["companion_voice"]
    skill = track_state.get("skill_tag", "this skill")
    rung_idx = int(track_state.get("current_ladder_rung", 0))
    rungs = ladder.get("rungs", [])
    if not rungs:
        return None
    rung_idx = min(rung_idx, len(rungs) - 1)
    current = rungs[rung_idx]
    sub_skills = current.get("sub_skills", [])

    # Scored sub-skills at the current rung
    scored = []
    for ss in sub_skills:
        name = ss.get("name", "")
        score = float(mastery_vector.get(name, {}).get("score", 0.0))
        scored.append((name, score, ss))

    gaps = [(n, s, ss) for n, s, ss in scored if s < 0.6]
    strengths = [(n, s, ss) for n, s, ss in scored if s >= 0.8]
    near = [(n, s, ss) for n, s, ss in scored if 0.6 <= s < 0.8]

    # Priority 1: honest gap callout (competence framing, evidence-sourced)
    if gaps:
        name, score, ss = max(gaps, key=lambda g: g[1])  # closest-to-ready gap
        cando = _can_do_phrase((ss.get("can_do_statements") or [None])[0])
        if cando:
            remaining = max(1, round((0.8 - score) / 0.1))
            return {
                "text": (f"Here's the honest read on {skill}: {name} is at "
                         f"{int(score * 100)}%. You're {remaining} session"
                         f"{'s' if remaining != 1 else ''} from being able to "
                         f"{cando} — that's the one to push on."),
                "motivation": "competence",
            }

    # Priority 2: near-ready consolidation (autonomy framing)
    if near:
        name, score, ss = max(near, key=lambda g: g[1])
        cando = _can_do_phrase((ss.get("can_do_statements") or [None])[0])
        tail = f" Once it's solid, {cando} comes with it." if cando else ""
        return {
            "text": (f"{name} is close — {int(score * 100)}% and climbing. "
                     f"You choose how to spend this session; a quick retrieval "
                     f"round usually finishes it.{tail}"),
            "motivation": "autonomy",
        }

    # Priority 3: strength -> name the next rung (competence + relatedness)
    if strengths:
        name, score, _ = strengths[0]
        nxt = rungs[rung_idx + 1] if rung_idx + 1 < len(rungs) else None
        if nxt:
            nxt_cando = _can_do_phrase(((nxt.get("sub_skills") or [{}])[0]
                                        .get("can_do_statements") or [None])[0])
            est = track_state.get("sessions_remaining_estimate")
            from_txt = (f"You're about {est} sessions from "
                        f"{nxt_cando}" if est and nxt_cando else
                        (f"Next up at the {nxt.get('level_name', 'following')} "
                         f"level: {nxt_cando}" if nxt_cando else
                         f"Next up: the {nxt.get('level_name', 'following')} "
                         f"level of {skill}."))
            return {
                "text": (f"{name} is genuinely solid now ({int(score * 100)}%). "
                         f"{from_txt}. I'll keep the harder reps in your way "
                         f"until it feels automatic."),
                "motivation": "relatedness",
            }
        return {
            "text": (f"{name} is genuinely solid ({int(score * 100)}%). This "
                     f"rung of {skill} is verified ground — we build on it, "
                     f"not repeat it."),
            "motivation": "competence",
        }

    # Priority 4: nothing measurable yet — frame the diagnostic honestly
    first = sub_skills[0]["name"] if sub_skills else skill
    return {
        "text": (f"No readings on {first} yet, so this session is a probe: "
                 f"attempt it, don't worry about being wrong — it calibrates "
                 f"everything after." ),
        "motivation": "autonomy",
    }


def generate_bridges_many(track_states: list[tuple[dict, dict, dict]],
                          cfg: Optional[dict] = None,
                          max_words: int = 45) -> list[dict[str, str]]:
    """Generate a bridge for each (track_state, mastery_vector, ladder) triple;
    drop any that exceed the configured word budget."""
    cfg = cfg or load_config()
    bridge_cfg = cfg.get("companion_voice", {})
    budget = bridge_cfg.get("max_bridge_words", max_words)
    out = []
    for ts, mv, lad in track_states:
        b = generate_bridge(ts, mv, lad, cfg)
        if b and len(b["text"].split()) <= budget:
            out.append(b)
    return out
