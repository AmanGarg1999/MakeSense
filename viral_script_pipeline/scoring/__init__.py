"""Scoring package for viral script generation."""

from .heuristics import (
    score_script_variant,
    rank_variants,
    analyze_hook,
    analyze_retention_beats,
    analyze_engagement,
    SCORE_WEIGHTS
)

__all__ = [
    "score_script_variant",
    "rank_variants",
    "analyze_hook",
    "analyze_retention_beats",
    "analyze_engagement",
    "SCORE_WEIGHTS"
]