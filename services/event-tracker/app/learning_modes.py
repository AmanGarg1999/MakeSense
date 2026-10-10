"""LL-08 learning-mode routing + project-together reverse-derivation.

One skill, many doors (vision §4): the same skill is reachable by guided,
project_together, explore_explain and drill_verify. The mode is selectable per
track; defaults come from the learner's level (novice -> guided) and the track
goal (employable/job-ready -> project_together). Every mode terminates at the
SAME LL-05 verification endpoint — no mode has a private verification path.

project_together derives a curriculum BACKWARDS from a chosen artifact: start
from the thing to be built, walk the artifact's capability list, pull the KG
prerequisite closure, and emit foundational -> capability -> assemble steps,
each carrying cited content (content_citations). If -- and only if -- the pack
has no match, a step is flagged `blocked_pending_content` rather than asserting
uncited material (anti-hallucination contract).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.content_citations import citation_pool, verify_citations
from app.interest_config import load_config, load_kg


# ---------------------------------------------------------------------------
# mode selection
# ---------------------------------------------------------------------------


@dataclass
class ModeSelection:
    skill_tag: str
    mode: str
    decided_by: str          # user_override | level_default | goal_default
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"skill_tag": self.skill_tag, "mode": self.mode,
                "decided_by": self.decided_by, "reason": self.reason}


def select_learning_mode(track: dict[str, Any], cfg: Optional[dict] = None,
                         override: Optional[str] = None,
                         learner_level: Optional[str] = None) -> ModeSelection:
    """Resolve the learning mode for a track.

    Precedence: explicit user override > level default (novice->guided,
    employable-goal->project) > goal default. `learner_level` may be passed
    explicitly or taken from track["learner_level"].
    """
    cfg = cfg or load_config()
    mr = cfg["mode_routing"]
    modes = set(mr["modes"])
    skill = track.get("skill_tag", "this skill")
    goal = track.get("goal_type", "hobby")
    level = learner_level or track.get("learner_level")

    if override:
        if override not in modes:
            raise ValueError(f"unknown mode: {override!r}; expected one of {sorted(modes)}")
        return ModeSelection(skill, override, "user_override",
                             f"learner picked {override} for {skill}")

    if level and level in mr["by_level"]:
        mode = mr["by_level"][level]
        return ModeSelection(skill, mode, "level_default",
                             f"level {level} defaults to {mode}")

    mode = mr["by_goal"].get(goal, "guided")
    return ModeSelection(skill, mode, "goal_default",
                         f"goal {goal} defaults to {mode}")


def modes_for_skill(skill_tag: str, cfg: Optional[dict] = None) -> list[dict[str, Any]]:
    """All doors to the same skill, with their one-line descriptions."""
    cfg = cfg or load_config()
    mr = cfg["mode_routing"]
    return [{"skill_tag": skill_tag, "mode": m,
             "description": mr["descriptions"].get(m, "")}
            for m in mr["modes"]]


def verification_endpoint(mode: str, skill_tag: str, cfg: Optional[dict] = None) -> dict[str, Any]:
    """The single LL-05 verification endpoint every mode funnels into."""
    cfg = cfg or load_config()
    mr = cfg["mode_routing"]
    return {"skill_tag": skill_tag, "mode": mode,
            "endpoint": mr["verification_endpoint"], "owner": "LL-05",
            "note": mr["verification_note"]}


# ---------------------------------------------------------------------------
# project-together: reverse-derive a curriculum from an artifact
# ---------------------------------------------------------------------------


def _prereq_closure(skill: str, kg: dict[str, Any],
                    _seen: Optional[set[str]] = None) -> list[str]:
    """Prerequisite skills of `skill` in deepest-first (build) order, excluding self."""
    _seen = _seen or set()
    node = (kg.get("skills") or {}).get(skill, {})
    out: list[str] = []
    for pre in node.get("prerequisites", []):
        if pre in _seen:
            continue
        _seen.add(pre)
        out.extend(_prereq_closure(pre, kg, _seen))
        out.append(pre)
    return out


def _resolve_skill_name(name: str, kg: dict[str, Any]) -> str:
    """Map a loose capability/sub-skill name onto a KG skill key when possible."""
    skills = kg.get("skills") or {}
    if name in skills:
        return name
    slug = name.strip().lower().replace(" ", "_")
    if slug in skills:
        return slug
    for key, node in skills.items():
        if name.strip().lower() in (t.lower() for t in node.get("topics", [])):
            return key
    return name


def derive_project_curriculum(artifact: dict[str, Any], kg: Optional[dict] = None,
                              pack: Optional[dict[str, Any]] = None,
                              cfg: Optional[dict] = None) -> dict[str, Any]:
    """Reverse-derive an ordered build plan for `artifact`, each step cited.

    artifact = {
      "title": "...",
      "skill_tag": "coordinate_geometry",
      "capabilities": [{"sub_skill": "plotting", "can_do": "..."}],   # what the artifact must do
      "end_state": "..."                                              # what 'done' looks like
    }
    """
    cfg = cfg or load_config()
    kg = kg or load_kg()
    pm = cfg["project_mode"]
    skill = artifact.get("skill_tag", "")
    per = pm["citations_per_step"]

    steps: list[dict[str, Any]] = []
    pools: dict[str, list[dict[str, Any]]] = {}
    cursor: dict[str, int] = {}

    def cites_for(name: str) -> list[dict[str, Any]]:
        """Rotate through the skill's cited-content pool so successive steps are
        grounded in successive pack items (not the same chunk repeated)."""
        key = _resolve_skill_name(name, kg)
        if key not in pools:
            pools[key] = citation_pool(key, kg, pack)
        pool = pools[key]
        if not pool:
            return []
        start = cursor.get(key, 0)
        out = [pool[(start + i) % len(pool)] for i in range(min(per, len(pool)))]
        cursor[key] = start + len(out)
        return out

    # 1. foundational prerequisites (deepest first) — what the artifact implies you already need
    for pre in _prereq_closure(skill, kg):
        steps.append(_step("foundation", pre, kg, cites_for(pre), pm,
                           why=f"the KG says {skill} rests on {pre}"))

    # 2. capability steps — each is a thing the artifact must be able to do
    for cap in artifact.get("capabilities", []):
        name = cap.get("sub_skill") or cap.get("name")
        steps.append(_step("capability", name, kg, cites_for(skill), pm,
                           why=f"the artifact needs '{name}'"
                               + (f" — {cap['can_do']}" if cap.get("can_do") else "")))

    # 3. terminal assembly — the artifact itself (this is where reverse-derivation lands)
    terminal_cites = cites_for(skill)
    steps.append({
        "kind": "assemble",
        "skill": skill,
        "sub_skill": skill,
        "title": f"Build: {artifact.get('title', skill)}",
        "why": "this IS the artifact — the reverse-derived plan terminates here",
        "cites": terminal_cites,
        "cited": bool(terminal_cites),
        "blocked_pending_content": pm.get("require_cited_content", True) and not terminal_cites,
        "verification": verification_endpoint("project_together", skill, cfg),
    })

    # index + honest citation audit
    for i, s in enumerate(steps):
        s["index"] = i
    all_cites = [c for s in steps for c in s.get("cites", [])]
    return {
        "mode": "project_together",
        "skill_tag": skill,
        "artifact": artifact,
        "direction": "reverse (artifact -> capabilities -> prerequisites)",
        "steps": steps,
        "step_count": len(steps),
        "cited": verify_citations(all_cites, pack) if pm.get("require_cited_content") else bool(all_cites),
        "verification_endpoint": cfg["mode_routing"]["verification_endpoint"],
        "uncited_steps": [s["sub_skill"] for s in steps if not s.get("cited")],
    }


def _step(kind: str, name: str, kg: dict[str, Any], cites: list[dict[str, Any]],
          pm: dict[str, Any], why: str) -> dict[str, Any]:
    skill_key = _resolve_skill_name(name, kg)
    title_node = (kg.get("skills") or {}).get(skill_key, {})
    return {
        "kind": kind,
        "skill": skill_key,
        "sub_skill": name,
        "title": f"{'Reach: ' if kind == 'foundation' else ''}{title_node.get('name', name)}",
        "why": why,
        "cites": cites,
        "cited": bool(cites),
        "blocked_pending_content": pm.get("require_cited_content", True) and not cites,
    }
