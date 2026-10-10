"""LL-08 future-path recommendation — extends the mk-031 career engine
(server/path_generator.py).

Where mk-031 proposes *pathways* for one topic, this proposes the NEXT concrete
move across a learner's concurrent tracks: from their current mastery vectors it
suggests next-level advancement, KG-adjacent skills, consolidation of a gap, and
cross-track leverage — each with a grounded "why this, why now" narrative that
quotes the learner's own numbers (scores, can-do counts, KG edge rationale),
never generic advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.interest_config import load_config, load_kg


@dataclass
class Suggestion:
    kind: str                 # next_level | adjacent | consolidate | cross_track
    suggested_skill: str
    suggested_level: Optional[int]
    title: str
    why_now: str
    priority: float
    from_track_id: Optional[str] = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "suggested_skill": self.suggested_skill,
            "suggested_level": self.suggested_level, "title": self.title,
            "why_now": self.why_now, "priority": round(self.priority, 4),
            "from_track_id": self.from_track_id, "evidence": self.evidence,
        }


def _subs_for(track: dict[str, Any], kg: dict[str, Any]) -> tuple[list[str], Optional[dict]]:
    """Sub-skills at the track's current rung (+ the rung dict) — from the ladder if given, else KG topics."""
    rungs = (track.get("ladder") or {}).get("rungs", [])
    idx = int(track.get("level_index", track.get("current_ladder_rung", 0)))
    if rungs:
        idx = min(idx, len(rungs) - 1)
        rung = rungs[idx]
        names = [ss.get("name") for ss in rung.get("sub_skills", []) if ss.get("name")]
        return names, rung
    node = (kg.get("skills") or {}).get(track.get("skill_tag", ""), {})
    return list(node.get("topics") or []), None


def _track_stats(track: dict[str, Any], kg: dict[str, Any], cfg: dict) -> dict[str, Any]:
    fp = cfg["future_paths"]
    mv = track.get("mastery_vector") or {}
    subs, rung = _subs_for(track, kg)
    scores = {name: float((mv.get(name) or {}).get("score", 0.0)) for name in subs}
    vals = list(scores.values())
    avg = round(sum(vals) / len(vals), 4) if vals else 0.0
    cleared = sum(1 for v in vals if v >= fp["rung_clear_score"])
    weakest = min(scores.items(), key=lambda kv: (kv[1], kv[0])) if scores else (None, 0.0)
    rungs = (track.get("ladder") or {}).get("rungs", [])
    idx = int(track.get("level_index", track.get("current_ladder_rung", 0)))
    next_rung = rungs[idx + 1] if (rungs and idx + 1 < len(rungs)) else None
    return {
        "skill": track.get("skill_tag"),
        "track_id": track.get("track_id"),
        "goal_type": track.get("goal_type", "hobby"),
        "level_index": idx,
        "level_name": (rung or {}).get("level_name") if rung else track.get("level_name"),
        "subs": subs, "scores": scores, "avg": avg,
        "cleared": cleared, "total_subs": len(vals),
        "weakest": weakest[0], "weakest_score": round(weakest[1], 4),
        "at_rung_end": bool(vals) and (cleared / len(vals)) >= 0.75 and avg >= fp["rung_clear_score"],
        "next_rung": next_rung,
        "sessions": int(track.get("sessions", 0)),
    }


def propose_future_paths(tracks: list[dict[str, Any]], kg: Optional[dict[str, Any]] = None,
                         cfg: Optional[dict] = None,
                         limit: Optional[int] = None) -> list[Suggestion]:
    cfg = cfg or load_config()
    kg = kg or load_kg()
    fp = cfg["future_paths"]
    limit = limit or fp["max_suggestions"]
    stats = [_track_stats(t, kg, cfg) for t in tracks]
    by_skill = {s["skill"]: s for s in stats}
    adjacency = kg.get("adjacency", [])
    candidates: list[Suggestion] = []

    for s in stats:
        skill, skill_name = s["skill"], s["skill"]
        node = (kg.get("skills") or {}).get(skill, {})
        display = node.get("name", skill)

        # --- next level: the current rung is cleared ------------------------
        if s["at_rung_end"] and s["next_rung"]:
            nxt = s["next_rung"]
            nxt_sub = ((nxt.get("sub_skills") or [{}])[0]).get("name", "the next rung")
            candidates.append(Suggestion(
                kind="next_level", suggested_skill=skill,
                suggested_level=int(nxt.get("level_index", s["level_index"] + 1)),
                title=f"Advance {display} to {nxt.get('level_name', 'the next level')}",
                why_now=(f"You've cleared {s['cleared']} of {s['total_subs']} can-do "
                         f"statements at {s['level_name'] or 'your current level'} "
                         f"(avg {int(s['avg'] * 100)}%). The next rung opens "
                         f"'{nxt_sub}' — you're ready for it now, not later."),
                priority=0.7 + fp["next_level_priority_bonus"],
                from_track_id=s["track_id"],
                evidence={"avg_mastery": s["avg"], "cleared": s["cleared"],
                          "total_subs": s["total_subs"], "level_index": s["level_index"],
                          "sessions": s["sessions"]}))

        # --- adjacent skills from the KG ------------------------------------
        if s["avg"] >= fp["mastery_strong_score"]:
            for edge in adjacency:
                if edge.get("from") != skill or edge.get("weight", 0) < fp["adjacency_min_weight"]:
                    continue
                target = edge["to"]
                if target in by_skill:
                    continue  # already a track
                tgt_node = (kg.get("skills") or {}).get(target, {})
                candidates.append(Suggestion(
                    kind="adjacent", suggested_skill=target, suggested_level=0,
                    title=f"Adjacent skill: {tgt_node.get('name', target)}",
                    why_now=(f"Your {display} is strong (avg {int(s['avg'] * 100)}%). "
                             f"The KG links it to {tgt_node.get('name', target)}: "
                             f"{edge.get('why', 'an adjacent capability')}. You'd compound "
                             f"existing strength instead of starting cold."),
                    priority=0.45 + 0.5 * float(edge.get("weight", 0.5)),
                    from_track_id=s["track_id"],
                    evidence={"avg_mastery": s["avg"], "kg_edge": {"from": skill, "to": target},
                              "edge_weight": edge.get("weight"), "edge_why": edge.get("why")}))

        # --- consolidate a gap ----------------------------------------------
        if s["weakest"] and s["weakest_score"] < fp["rung_gap_score"]:
            gap = round(fp["rung_gap_score"] - s["weakest_score"], 4)
            candidates.append(Suggestion(
                kind="consolidate", suggested_skill=skill,
                suggested_level=s["level_index"],
                title=f"Shore up {s['weakest']} in {display}",
                why_now=(f"'{s['weakest']}' sits at {int(s['weakest_score'] * 100)}% while "
                         f"your {display} average is {int(s['avg'] * 100)}%. It will block the "
                         f"next rung that depends on it, so fix it before advancing."),
                priority=0.6 + gap + fp["consolidate_priority_bonus"],
                from_track_id=s["track_id"],
                evidence={"weakest_sub": s["weakest"], "weakest_score": s["weakest_score"],
                          "avg_mastery": s["avg"], "gap": gap}))

    # --- cross-track leverage: a strong track teaches a weak one ------------
    if len(stats) >= 2:
        strong = max(stats, key=lambda s: s["avg"])
        weak = min(stats, key=lambda s: s["avg"])
        if strong["skill"] != weak["skill"] and strong["avg"] >= fp["mastery_strong_score"] \
                and weak["avg"] < strong["avg"]:
            candidates.append(Suggestion(
                kind="cross_track", suggested_skill=weak["skill"],
                suggested_level=weak["level_index"],
                title=f"Use {strong['skill']} as the example domain for {weak['skill']}",
                why_now=(f"You're strongest in {strong['skill']} (avg {int(strong['avg'] * 100)}%) "
                         f"and weakest in {weak['skill']} (avg {int(weak['avg'] * 100)}%). "
                         f"Teaching {weak['skill']} through {strong['skill']} analogies turns "
                         f"prior mastery into a shortcut."),
                priority=0.4 + fp["cross_track_priority_bonus"],
                from_track_id=weak["track_id"],
                evidence={"strong_skill": strong["skill"], "strong_avg": strong["avg"],
                          "weak_skill": weak["skill"], "weak_avg": weak["avg"]}))

    # dedupe + rank (deterministic)
    seen: set[tuple[str, str]] = set()
    uniq: list[Suggestion] = []
    for c in sorted(candidates, key=lambda c: (-c.priority, c.kind, c.suggested_skill)):
        key = (c.kind, c.suggested_skill)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq[:limit]
