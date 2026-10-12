"""LL-09b: per-level pedagogy configuration for the Coach Engine.

Two sources of truth, layered (see LL-09a handoff):

  * ``level_metadata`` table (server/migrations/009_learning_pathways.sql)
    — program facts: typical_duration_weeks, credit_system, assessment_type,
    mentor_model, recap_interval_days. Loaded via
    :func:`server.pathway_service.get_level_metadata` when a DB pool is wired.

  * ``LEVEL_CONFIGS`` (this module)
    — pedagogy templates: the coaching cycle, feedback timing, skill-radar
    granularity, challenge difficulty/cadence, and the long-term-tracking
    posture. These are behavioral, versioned in code, and unit-testable
    without a DB.

The canonical level enum lives in server/pathway_service.PATHWAY_LEVELS; it
is imported, never re-declared here (LL-09a contract).

Spaced recap (LL-06) integration: ``recap_multiplier_for`` returns an
*interval multiplier* keyed by level, meant to scale the LL-06 Leitner base
intervals (daily for micro -> weekly/semester for degree levels). It is
additive: LL-06's scheduler is unchanged; the coach engine passes the
multiplier through its challenge/recap planning output.
"""

from __future__ import annotations

import copy
import functools
from typing import Any, Dict, List, Optional

from server.pathway_service import PATHWAY_LEVELS  # canonical enum (LL-09a)

assert len(PATHWAY_LEVELS) == 6, "LL-09b expects the 6 canonical levels"

DEGREE_LEVELS: List[str] = ["certificate", "undergrad", "masters", "phd", "mba"]

# pedagogy templates — one per canonical level, from the LL-09b spec
LEVEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "micro": {
        "label": "Micro-task",
        "cycle": ["question", "attempt", "hint", "retry"],
        "feedback": "immediate",
        "focus": "single_concept",
        "long_term_tracking": False,
        "radar_granularity": "atomic_skills",
        "recap_multiplier": 0.5,          # daily-scale recaps
        "challenge": {"difficulty_target": 0.4, "cadence_minutes": 15},
        "instruments": ["rapid_feedback_loop", "single_concept_drills"],
    },
    "certificate": {
        "label": "Certificate",
        "cycle": ["milestone", "checkpoint", "review_gate", "summary"],
        "feedback": "weekly",
        "focus": "project",
        "long_term_tracking": True,
        "radar_granularity": "competency_clusters",
        "recap_multiplier": 1.0,         # weekly-scale recaps
        "challenge": {"difficulty_target": 0.5, "cadence_minutes": 240},
        "instruments": [
            "project_milestones",
            "portfolio_checkpoints",
            "peer_review_gates",
            "weekly_progress_summaries",
        ],
    },
    "undergrad": {
        "label": "Undergraduate",
        "cycle": ["plan", "study", "assess", "reflect"],
        "feedback": "per_module",
        "focus": "course",
        "long_term_tracking": True,
        "radar_granularity": "competency_clusters",
        "recap_multiplier": 1.5,         # weekly -> biweekly
        "challenge": {"difficulty_target": 0.55, "cadence_minutes": 1440},
        "instruments": [
            "semester_planner",
            "credit_tracker",
            "breadth_requirements",
            "exam_prep_mode",
            "gpa_projection",
        ],
    },
    "masters": {
        "label": "Master's",
        "cycle": ["research", "review", "gate", "advisor_sync"],
        "feedback": "per_milestone",
        "focus": "thesis",
        "long_term_tracking": True,
        "radar_granularity": "competency_clusters",
        "recap_multiplier": 2.0,         # ~biweekly->monthly
        "challenge": {"difficulty_target": 0.65, "cadence_minutes": 4320},
        "instruments": [
            "research_proposal_tracker",
            "literature_review_manager",
            "thesis_milestone_gates",
            "advisor_meeting_prep",
        ],
    },
    "phd": {
        "label": "PhD",
        "cycle": ["investigate", "write", "publish", "committee_sync"],
        "feedback": "per_chapter",
        "focus": "dissertation",
        "long_term_tracking": True,
        "radar_granularity": "competency_clusters",
        "recap_multiplier": 2.5,         # monthly-scale
        "challenge": {"difficulty_target": 0.75, "cadence_minutes": 10080},
        "instruments": [
            "dissertation_chapter_tracker",
            "publication_pipeline",
            "conference_deadline_calendar",
            "advisor_coinvestigator_sync",
        ],
    },
    "mba": {
        "label": "MBA",
        "cycle": ["case_prep", "discussion", "reflect", "integrate"],
        "feedback": "per_session",
        "focus": "case",
        "long_term_tracking": True,
        "radar_granularity": "competency_clusters",
        "recap_multiplier": 1.5,
        "challenge": {"difficulty_target": 0.6, "cadence_minutes": 2880},
        "instruments": [
            "case_study_discussion_prep",
            "cohort_sync_scheduler",
            "leadership_reflection_prompts",
            "capstone_integrator",
        ],
    },
}

# sanity: pedagogy templates must cover exactly the canonical enum
assert set(LEVEL_CONFIGS) == set(PATHWAY_LEVELS), (
    "LEVEL_CONFIGS drifted from the canonical level enum "
    f"{PATHWAY_LEVELS}"
)


def level_config_for(level: str) -> Dict[str, Any]:
    """Pedagogy template for a canonical level. KeyError on unknown level."""
    if level not in LEVEL_CONFIGS:
        raise KeyError(
            f"unknown learning level '{level}'; canonical levels: {PATHWAY_LEVELS}"
        )
    return copy.deepcopy(LEVEL_CONFIGS[level])  # deep copy — configs are read-only contracts


def recap_multiplier_for(level: str) -> float:
    """LL-06 interval multiplier for a level (additive interface: the recap
    scheduler stays untouched; callers scale base intervals with this)."""
    return float(level_config_for(level)["recap_multiplier"])


def merge_level_metadata(
    pedagogy: Dict[str, Any],
    row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Fold a level_metadata DB row (LL-09a) over a pedagogy template.

    DB facts win for program characteristics (duration, credit system,
    assessment type, mentor model, recap interval); pedagogy behavior stays
    code-owned so unit tests are deterministic without a DB.
    """
    merged = dict(pedagogy)
    if row:
        merged["program"] = {
            "typical_duration_weeks": row.get("typical_duration_weeks"),
            "credit_system": row.get("credit_system"),
            "assessment_type": row.get("assessment_type"),
            "mentor_model": row.get("mentor_model"),
            "recap_interval_days": row.get("recap_interval_days"),
        }
    return merged
