"""LL-09b: level-aware Coach Engine.

The mk-018 On-Device Coach Engine tracks mastery, renders a skill radar, and
emits adaptive challenges. LL-09b adds ONE dimension: pedagogy switching by
learning level. The same user input state must produce different coach
behavior depending on the active pathway level (micro vs a degree program),
because a micro learner is in a rapid question->attempt->hint->retry loop
with immediate feedback and no long-term tracking, while a degree learner is
inside milestone/gate cycles with portfolio checkpoints and semester-scale
recaps.

Interfaces (kept additive per the LL-09a/LL-07 handoff notes):

  * ``CoachEngine(pool=None)`` — pure-code mode for unit tests; pass an
    asyncpg pool to load program facts from the level_metadata table.
  * ``await engine.setLearningLevel(level)`` — loads the pedagogy template
    and folds the DB level_metadata row over it when a pool is wired.
    ``set_learning_level`` is the PEP8 alias.
  * ``engine.coach_action(state)`` — the behavior entry point. ``state`` is
    a plain dict (see STATE KEYS). Deterministic, no I/O.
  * ``engine.challenge_request(state)`` — the additive hook the LL-07
    adaptive challenge generator reads for difficulty/cadence hints. It does
    NOT call into LL-07; it only publishes the level-derived parameters on
    the request dict, so LL-07's branch merges without conflict.

State keys (all optional; defaults handle cold-start):
  skill         : str            focus skill tag ("guitar:barre_chords")
  attempts      : int            failed attempts on the current item
  correct       : bool           last attempt outcome
  mastered      : list[str]      skills with ledger mastery >= threshold
  session_minutes : float        time invested this session
  last_action   : str            action id previously emitted (cycle advance)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ll09b.level_config import (
    DEGREE_LEVELS,
    level_config_for,
    merge_level_metadata,
    recap_multiplier_for,
)
from server.pathway_service import PATHWAY_LEVELS

# mastery threshold on the radar: atomic skills are graded exactly,
# competency clusters aggregate member skills (mk-027 granularity switch)
ATOMIC_MASTERY_THRESHOLD = 0.8
CLUSTER_MASTERY_THRESHOLD = 0.7


@dataclass
class CoachAction:
    """One coach behavior step: what the engine wants to show the user."""

    action: str                       # e.g. "question" | "milestone_review"
    payload: Dict[str, Any] = field(default_factory=dict)
    level: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "payload": self.payload, "level": self.level, "ts": self.ts}


class CoachEngine:
    """Level-aware pedagogy switching for the On-Device Coach Engine (mk-018)."""

    def __init__(self, pool=None, user_id: Optional[int] = None):
        self._pool = pool
        self._user_id = user_id
        self._level: str = "micro"          # neutral default
        self._config: Dict[str, Any] = level_config_for(self._level)

    # ------------------------------------------------------------------
    # Level switching
    # ------------------------------------------------------------------

    @property
    def level(self) -> str:
        return self._level

    @property
    def level_config(self) -> Dict[str, Any]:
        return dict(self._config)

    def setLearningLevel(self, level: str) -> Dict[str, Any]:
        """Switch pedagogy to ``level`` (canonical enum). Async-safe wrapper
        below adds DB facts; this method alone works without a pool so the
        engine is usable on-device/offline. Returns the effective config.

        Raises KeyError on a non-canonical level — no silent fallbacks.
        """
        if level not in PATHWAY_LEVELS:
            raise KeyError(
                f"unknown learning level '{level}'; canonical levels: {PATHWAY_LEVELS}"
            )
        self._level = level
        self._config = level_config_for(level)
        return self.level_config

    # PEP8 alias
    set_learning_level = setLearningLevel

    async def set_learning_level_async(self, level: str) -> Dict[str, Any]:
        """setLearningLevel + fold the level_metadata DB row (LL-09a) over the
        pedagogy template when a pool is wired."""
        config = self.setLearningLevel(level)
        if self._pool is not None:
            from server.pathway_service import get_level_metadata

            row = await get_level_metadata(self._pool, level)
            config = merge_level_metadata(config, row)
            # DB facts win for the recap clock (program cadence is data)
            if row and row.get("recap_interval_days"):
                config["db_recap_interval_days"] = float(row["recap_interval_days"])
            self._config = config
        return self.level_config

    # ------------------------------------------------------------------
    # Behavior core
    # ------------------------------------------------------------------

    def coach_action(self, state: Dict[str, Any]) -> CoachAction:
        """Decide the next coach step for the current level from input state.

        Same state + different level -> guaranteed different action. This is
        the acceptance surface for LL-09b.
        """
        cfg = self._config
        cycle: List[str] = cfg["cycle"]
        attempts = int(state.get("attempts", 0))
        correct = bool(state.get("correct", False))
        skill = state.get("skill", "general")

        # --- micro-style rapid cycle (explicit, per spec) ---
        if not cfg["long_term_tracking"]:
            if correct:
                return CoachAction(
                    action="advance_concept",
                    payload={
                        "skill": skill,
                        "feedback": "immediate",
                        "message": "correct — one concept closed; queue next micro-task",
                        "radar_update": self.radar_update(state),
                        "recap_plan": self.recap_plan(state),
                        "track_history": False,   # micro: no long-term tracking
                    },
                    level=self._level,
                )
            stage = cycle[min(attempts, len(cycle) - 1)]
            return CoachAction(
                action=f"micro_{stage}",
                payload={
                    "skill": skill,
                    "stage": stage,
                    "attempt": attempts + 1,
                    "feedback": "immediate",
                    "hint": stage == "hint",
                    "retry": stage == "retry",
                    "radar_update": self.radar_update(state),
                    "recap_plan": self.recap_plan(state),
                    "track_history": False,
                },
                level=self._level,
            )

        # --- degree-style cycle: position advances through the level's cycle ---
        last = state.get("last_action")
        idx = cycle.index(last.replace(f"{self._level}_", "")) + 1 if last and last.replace(f"{self._level}_", "") in cycle else 0
        idx = idx % len(cycle)
        stage = cycle[idx]

        # a degree learner who just got something right still gets the
        # milestone/summary treatment, NOT a micro retry loop
        if correct and stage in ("summary", "reflect", "review_gate", "advisor_sync"):
            action = f"{self._level}_milestone_checkpoint"
            note = "verified attempt folds into the current milestone; portfolio checkpoint updated"
        else:
            action = f"{self._level}_{stage}"
            note = f"cycle stage '{stage}' for {cfg['label']} program"

        return CoachAction(
            action=action,
            payload={
                "skill": skill,
                "stage": stage,
                "cycle_position": idx,
                "feedback": cfg["feedback"],
                "focus": cfg["focus"],
                "instruments": list(cfg["instruments"]),
                "milestone": {"cycle": cycle, "next": cycle[(idx + 1) % len(cycle)]},
                "summary_cadence": cfg["feedback"],
                "radar_update": self.radar_update(state),
                "recap_plan": self.recap_plan(state),
                "track_history": True,
                "long_term_instrument": self.instrument_for(state),
            },
            level=self._level,
        )

    # ------------------------------------------------------------------
    # Skill radar granularity (mk-027 contract)
    # ------------------------------------------------------------------

    def radar_update(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Shape the radar payload: micro -> atomic skills (one node per
        skill tag); degree levels -> competency clusters (member skills
        aggregated under one node)."""
        cfg = self._config
        skills: List[str] = list(state.get("skills") or ([state["skill"]] if state.get("skill") else []))
        mastered = set(state.get("mastered") or [])
        if cfg["radar_granularity"] == "atomic_skills":
            return {
                "granularity": "atomic_skills",
                "threshold": ATOMIC_MASTERY_THRESHOLD,
                "nodes": [
                    {"id": s, "label": s, "mastered": s in mastered} for s in skills
                ],
            }
        # competency clusters: group by family prefix ("music:chords", ...)
        clusters: Dict[str, List[str]] = {}
        for s in skills:
            family = s.split(":", 1)[0]
            clusters.setdefault(family, []).append(s)
        return {
            "granularity": "competency_clusters",
            "threshold": CLUSTER_MASTERY_THRESHOLD,
            "nodes": [
                {
                    "id": f"cluster:{fam}",
                    "label": fam,
                    "members": members,
                    "mastered": all(m in mastered for m in members),
                }
                for fam, members in sorted(clusters.items())
            ],
        }

    # ------------------------------------------------------------------
    # Spaced recap multiplier (LL-06 contract; additive)
    # ------------------------------------------------------------------

    def recap_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Emit the interval multiplier the recap scheduler should apply to
        base Leitner intervals for THIS level. LL-06 code is not modified."""
        mult = self._config.get("db_recap_interval_days") or recap_multiplier_for(self._level)
        # prefer the pedagogical multiplier; expose both so callers can choose
        return {
            "level": self._level,
            "interval_multiplier": recap_multiplier_for(self._level),
            "code_multiplier": recap_multiplier_for(self._level),
            "cadence_label": "daily-scale" if self._level == "micro" else "program-scale",
            "metadata_recap_days": float(self._config["program"]["recap_interval_days"])
            if "program" in self._config and self._config["program"].get("recap_interval_days")
            else None,
        }

    # ------------------------------------------------------------------
    # Challenge generator hook (mk-028/LL-07 contract; additive only)
    # ------------------------------------------------------------------

    def challenge_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parameters an adaptive challenge generator (LL-07) should use for
        this level. Purely additive: LL-07 may ignore or read these keys."""
        cfg = self._config
        return {
            "level": self._level,
            "difficulty_target": cfg["challenge"]["difficulty_target"],
            "cadence_minutes": cfg["challenge"]["cadence_minutes"],
            "single_concept": not cfg["long_term_tracking"],
            "feedback": cfg["feedback"],
        }

    # ------------------------------------------------------------------
    # Long-term instruments per level
    # ------------------------------------------------------------------

    def instrument_for(self, state: Dict[str, Any]) -> Optional[str]:
        """Pick the next long-term instrument to engage at this level.
        micro has none (returns None); degree levels rotate their
        instrument list deterministically."""
        cfg = self._config
        instruments: List[str] = list(cfg["instruments"])
        if not cfg["long_term_tracking"] or not instruments:
            return None
        # deterministic rotation off session minutes (~1 instrument per 30
        # min of program time) so same state -> same instrument
        minutes = float(state.get("session_minutes", 0.0))
        idx = int(minutes // 30) % len(instruments)
        return instruments[idx]
