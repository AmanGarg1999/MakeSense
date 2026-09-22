"""Output data models for the viral script generation pipeline."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class FrameworkType(Enum):
    """Copywriting frameworks used for script generation."""
    AIDA = "AIDA"  # Attention, Interest, Desire, Action
    PAS = "PAS"    # Problem, Agitation, Solution
    CURIOSITY_GAP = "CURIOSITY_GAP"
    HOOK_STORY_OFFER = "HOOK_STORY_OFFER"
    BEFORE_AFTER_BRIDGE = "BEFORE_AFTER_BRIDGE"


@dataclass
class Hook:
    """The opening hook (0-3 seconds) of a YouTube script."""
    text: str
    framework: FrameworkType
    technique: str  # e.g., "pattern_interrupt", "bold_claim", "question", "visual_tease"
    estimated_retention_impact: float  # 0-1 score

    def to_prompt_format(self) -> str:
        return f"[HOOK - {self.framework.value}] {self.text} (Technique: {self.technique})"


@dataclass
class RetentionBeat:
    """A retention beat - a moment designed to keep viewers watching."""
    timestamp_range: str  # e.g., "0:03-0:15", "1:30-2:00"
    content: str
    purpose: str  # e.g., "build_tension", "deliver_value", "pattern_interrupt", "payoff"
    visual_cue: Optional[str] = None

    def to_prompt_format(self) -> str:
        parts = [f"[{self.timestamp_range}] {self.content} (Purpose: {self.purpose})"]
        if self.visual_cue:
            parts.append(f"Visual: {self.visual_cue}")
        return " ".join(parts)


@dataclass
class CTA:
    """Call to action for the video."""
    primary: str
    secondary: Optional[str] = None
    placement: str = "end"  # "early", "mid", "end", "throughout"
    style: str = "direct"  # "direct", "soft", "curiosity", "value_first"

    def to_prompt_format(self) -> str:
        parts = [f"CTA ({self.placement}, {self.style}): {self.primary}"]
        if self.secondary:
            parts.append(f"Secondary: {self.secondary}")
        return " | ".join(parts)


@dataclass
class TitleIdeas:
    """Title and thumbnail ideas for the video."""
    titles: List[str] = field(default_factory=list)
    thumbnail_concepts: List[str] = field(default_factory=list)
    predicted_ctr: List[float] = field(default_factory=list)  # Parallel to titles

    def best_title(self) -> Optional[str]:
        if not self.titles:
            return None
        if self.predicted_ctr:
            best_idx = self.predicted_ctr.index(max(self.predicted_ctr))
            return self.titles[best_idx]
        return self.titles[0]

    def to_prompt_format(self) -> str:
        parts = ["TITLE IDEAS:"]
        for i, title in enumerate(self.titles):
            ctr = self.predicted_ctr[i] if i < len(self.predicted_ctr) else "N/A"
            parts.append(f"  {i+1}. {title} (Pred. CTR: {ctr})")
        if self.thumbnail_concepts:
            parts.append("\nTHUMBNAIL CONCEPTS:")
            for i, concept in enumerate(self.thumbnail_concepts):
                parts.append(f"  {i+1}. {concept}")
        return "\n".join(parts)


@dataclass
class ThumbnailIdeas:
    """Detailed thumbnail concepts."""
    concepts: List[str] = field(default_factory=list)
    color_schemes: List[str] = field(default_factory=list)
    text_overlays: List[str] = field(default_factory=list)
    focal_points: List[str] = field(default_factory=list)


@dataclass
class ScriptVariant:
    """A complete script variant generated from a framework."""
    framework: FrameworkType
    hook: Hook
    beats: List[RetentionBeat]
    cta: CTA
    title_ideas: TitleIdeas
    full_script: str  # The assembled script text
    estimated_duration_seconds: int
    word_count: int

    def to_prompt_format(self) -> str:
        parts = [
            f"=== SCRIPT VARIANT: {self.framework.value} ===",
            f"Duration: ~{self.estimated_duration_seconds}s | Words: {self.word_count}",
            "",
            self.hook.to_prompt_format(),
            "",
            "RETENTION BEATS:",
        ]
        for beat in self.beats:
            parts.append(f"  {beat.to_prompt_format()}")
        parts.append("")
        parts.append(self.cta.to_prompt_format())
        parts.append("")
        parts.append(self.title_ideas.to_prompt_format())
        parts.append("")
        parts.append("FULL SCRIPT:")
        parts.append(self.full_script)
        return "\n".join(parts)


@dataclass
class ScoredScriptVariant:
    """A script variant with quality scores."""
    variant: ScriptVariant
    predicted_ctr: float  # 0-1
    predicted_retention: float  # 0-1 (average viewer retention %)
    engagement_score: float  # 0-1 (likes, comments, shares potential)
    overall_score: float  # Weighted composite
    score_breakdown: dict = field(default_factory=dict)

    @classmethod
    def from_variant(cls, variant: ScriptVariant, scores: dict) -> "ScoredScriptVariant":
        return cls(
            variant=variant,
            predicted_ctr=scores.get("predicted_ctr", 0.0),
            predicted_retention=scores.get("predicted_retention", 0.0),
            engagement_score=scores.get("engagement_score", 0.0),
            overall_score=scores.get("overall_score", 0.0),
            score_breakdown=scores
        )


@dataclass
class PipelineResult:
    """Complete result of the pipeline for one topic."""
    topic: str
    variants: List[ScoredScriptVariant] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    input_context_summary: str = ""

    def get_ranked_variants(self) -> List[ScoredScriptVariant]:
        """Get variants sorted by overall score descending."""
        return sorted(self.variants, key=lambda v: v.overall_score, reverse=True)

    def top_variant(self) -> Optional[ScoredScriptVariant]:
        ranked = self.get_ranked_variants()
        return ranked[0] if ranked else None

    def to_json(self) -> dict:
        """Serialize for JSON output."""
        return {
            "topic": self.topic,
            "generated_at": self.generated_at,
            "input_context_summary": self.input_context_summary,
            "variants": [
                {
                    "framework": v.variant.framework.value,
                    "predicted_ctr": v.predicted_ctr,
                    "predicted_retention": v.predicted_retention,
                    "engagement_score": v.engagement_score,
                    "overall_score": v.overall_score,
                    "score_breakdown": v.score_breakdown,
                    "hook": {
                        "text": v.variant.hook.text,
                        "technique": v.variant.hook.technique,
                        "estimated_retention_impact": v.variant.hook.estimated_retention_impact
                    },
                    "beats": [
                        {
                            "timestamp": b.timestamp_range,
                            "content": b.content,
                            "purpose": b.purpose,
                            "visual_cue": b.visual_cue
                        }
                        for b in v.variant.beats
                    ],
                    "cta": {
                        "primary": v.variant.cta.primary,
                        "secondary": v.variant.cta.secondary,
                        "placement": v.variant.cta.placement,
                        "style": v.variant.cta.style
                    },
                    "title_ideas": {
                        "titles": v.variant.title_ideas.titles,
                        "thumbnail_concepts": v.variant.title_ideas.thumbnail_concepts,
                        "predicted_ctr": v.variant.title_ideas.predicted_ctr
                    },
                    "full_script": v.variant.full_script,
                    "estimated_duration_seconds": v.variant.estimated_duration_seconds,
                    "word_count": v.variant.word_count
                }
                for v in self.get_ranked_variants()
            ]
        }