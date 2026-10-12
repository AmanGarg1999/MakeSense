"""LL-09b: Coach Engine level-aware pedagogy switching.

Extends the mk-018 On-Device Coach Engine concept: the engine adapts its
pedagogy (feedback cadence, cycle template, radar granularity, challenge
difficulty, recap intervals) to the user's canonical learning level from
LL-09a (micro | certificate | undergrad | masters | phd | mba).

The level vocabulary is NOT re-declared here — it is imported from
server.pathway_service.PATHWAY_LEVELS (LL-09a canonical source).
"""

from ll09b.level_config import LEVEL_CONFIGS, level_config_for, recap_multiplier_for
from ll09b.coach_engine import CoachEngine, CoachAction

__all__ = [
    "CoachEngine",
    "CoachAction",
    "LEVEL_CONFIGS",
    "level_config_for",
    "recap_multiplier_for",
]
