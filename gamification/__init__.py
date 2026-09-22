"""
Gamification Package

A complete gamification system for MakeSense including:
- User levels and XP progression
- Engagement points ledger
- Skill ratings with Bayesian inference
- Achievement/badge system
- Interaction event logging
- Leaderboards and analytics
- Points calculation and leveling engine
"""

__version__ = "1.0.0"

from .skills import (
    SkillRatingEngine,
    SkillRatingConfig,
    SkillEvidence,
    nightly_skill_recalculation,
    update_skill_taxonomy_from_content,
    create_skill_rating_engine,
)

from .engine import (
    PointsRules,
    LevelThresholds,
    GamificationEngine,
    process_user_events,
    load_points_rules
)

__all__ = [
    "SkillRatingEngine",
    "SkillRatingConfig",
    "SkillEvidence",
    "nightly_skill_recalculation",
    "update_skill_taxonomy_from_content",
    "create_skill_rating_engine",
    "PointsRules",
    "LevelThresholds",
    "GamificationEngine",
    "process_user_events",
    "load_points_rules",
]