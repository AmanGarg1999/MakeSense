"""Viral Script Generation Pipeline - Main Package"""

from .models import (
    Topic, Story, ScrapedContent, SourceType,
    Hook, RetentionBeat, CTA, TitleIdeas, ThumbnailIdeas,
    ScriptVariant, ScoredScriptVariant, PipelineResult, FrameworkType
)
from .pipeline import ViralScriptPipeline, create_pipeline_from_config
from .prompts import LLMClient, build_generation_prompt
from .scoring import score_script_variant, rank_variants

__version__ = "1.0.0"
__all__ = [
    # Models
    "Topic", "Story", "ScrapedContent", "SourceType",
    "Hook", "RetentionBeat", "CTA", "TitleIdeas", "ThumbnailIdeas",
    "ScriptVariant", "ScoredScriptVariant", "PipelineResult", "FrameworkType",
    # Pipeline
    "ViralScriptPipeline", "create_pipeline_from_config",
    # Prompts
    "LLMClient", "build_generation_prompt",
    # Scoring
    "score_script_variant", "rank_variants",
]