"""Scoring heuristics for predicting script performance."""

import re
from typing import Dict, List
from ..models.output_models import ScriptVariant, ScoredScriptVariant, FrameworkType


# Heuristic weights for overall score
SCORE_WEIGHTS = {
    "predicted_ctr": 0.35,
    "predicted_retention": 0.40,
    "engagement_score": 0.25,
}


# Positive signal patterns (increase scores)
POSITIVE_HOOK_PATTERNS = [
    r'\b(you won\'t believe|shocking|secret|hidden|nobody tells you)\b',
    r'\b(how to|why|what if|imagine|discover)\b',
    r'\b(stop|don\'t|never|avoid|mistake)\b',
    r'^\d+',  # Starts with number
    r'\$[\d,]+',  # Money mention
    r'\b(free|instant|guaranteed|proven)\b',
]

POSITIVE_RETENTION_PATTERNS = [
    r'\b(but|however|wait|actually|here\'s the thing)\b',  # Pattern interrupts
    r'\b(step \d+|first|second|third|finally)\b',  # Structured steps
    r'\b(example|case study|proof|results?)\b',  # Evidence
    r'\b(you might wonder|question|answer)\b',  # Q&A rhythm
    r'\b(bonus|extra|plus|also)\b',  # Extra value
]

POSITIVE_ENGAGEMENT_PATTERNS = [
    r'\b(comment|subscribe|follow|share|like)\b',
    r'\b(what do you think|your thoughts|agree\?)\b',
    r'\b(poll|vote|choose|pick)\b',
    r'\b(link in bio|description|pinned)\b',
]


# Negative signal patterns (decrease scores)
NEGATIVE_PATTERNS = [
    r'\b(um|uh|like|you know|basically|literally)\b',  # Filler words
    r'(.{200,})',  # Overly long sentences (>200 chars)
    r'\b(today I want to talk about|in this video I will)\b',  # Boring openings
    r'\b(thanks for watching|smash that like)\b',  # Generic CTAs
]


def analyze_hook(hook_text: str, technique: str) -> Dict[str, float]:
    """Analyze hook quality and predict CTR impact."""
    text_lower = hook_text.lower()
    
    # Base score from technique
    technique_scores = {
        "pattern_interrupt": 0.75,
        "bold_claim": 0.70,
        "question": 0.65,
        "visual_tease": 0.70,
        "story_open": 0.60,
        "shock_stat": 0.80,
    }
    base_score = technique_scores.get(technique.lower(), 0.55)
    
    # Positive signals
    positive_bonus = 0.0
    for pattern in POSITIVE_HOOK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            positive_bonus += 0.03
    
    # Negative signals
    negative_penalty = 0.0
    for pattern in NEGATIVE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            negative_penalty += 0.05
    
    # Length check - sweet spot 10-80 chars
    length = len(hook_text)
    if 10 <= length <= 80:
        length_bonus = 0.05
    elif length < 10:
        length_bonus = -0.10
    else:
        length_bonus = -0.05
    
    predicted_ctr = max(0.01, min(0.30, base_score + positive_bonus - negative_penalty + length_bonus))
    
    return {
        "predicted_ctr": predicted_ctr,
        "base_technique_score": base_score,
        "positive_bonus": positive_bonus,
        "negative_penalty": negative_penalty,
        "length_bonus": length_bonus,
    }


def analyze_retention_beats(beats: List, full_script: str) -> Dict[str, float]:
    """Analyze retention beat structure and predict average retention."""
    if not beats:
        return {"predicted_retention": 0.35, "beat_count": 0, "structure_score": 0.0}
    
    # Beat count score (optimal 4-6 for 90s)
    beat_count = len(beats)
    if 4 <= beat_count <= 6:
        count_score = 1.0
    elif beat_count == 3:
        count_score = 0.8
    elif beat_count >= 7:
        count_score = 0.7
    else:
        count_score = 0.5
    
    # Purpose diversity
    purposes = [b.purpose for b in beats]
    unique_purposes = len(set(purposes))
    diversity_score = min(1.0, unique_purposes / 4)  # Want at least 4 different purposes
    
    # Positive patterns in script
    script_lower = full_script.lower()
    positive_signals = 0
    for pattern in POSITIVE_RETENTION_PATTERNS:
        positive_signals += len(re.findall(pattern, script_lower, re.IGNORECASE))
    
    positive_score = min(1.0, positive_signals / 8)  # Normalize
    
    # Negative patterns
    negative_signals = 0
    for pattern in NEGATIVE_PATTERNS:
        negative_signals += len(re.findall(pattern, script_lower, re.IGNORECASE))
    
    negative_penalty = min(0.3, negative_signals * 0.03)
    
    # Visual cues presence
    visual_cues = sum(1 for b in beats if b.visual_cue)
    visual_score = min(1.0, visual_cues / max(1, beat_count))
    
    # Base retention for short-form
    base_retention = 0.50
    
    predicted_retention = base_retention * (
        0.3 * count_score +
        0.2 * diversity_score +
        0.25 * positive_score +
        0.15 * visual_score +
        0.1 * (1 - negative_penalty)
    )
    
    predicted_retention = max(0.20, min(0.85, predicted_retention))
    
    return {
        "predicted_retention": predicted_retention,
        "beat_count": beat_count,
        "count_score": count_score,
        "diversity_score": diversity_score,
        "positive_score": positive_score,
        "negative_penalty": negative_penalty,
        "visual_score": visual_score,
        "structure_score": (count_score + diversity_score + positive_score + visual_score) / 4
    }


def analyze_engagement(cta, title_ideas, full_script: str) -> Dict[str, float]:
    """Analyze engagement potential (likes, comments, shares)."""
    script_lower = full_script.lower()
    
    # CTA quality
    cta_scores = {
        "direct": 0.6,
        "soft": 0.5,
        "curiosity": 0.7,
        "value_first": 0.75,
    }
    cta_base = cta_scores.get(cta.style.lower(), 0.5)
    
    # CTA placement bonus
    placement_bonus = {
        "early": 0.05,
        "mid": 0.1,
        "end": 0.0,
        "throughout": 0.15,
    }.get(cta.placement.lower(), 0.0)
    
    # Title CTR potential
    title_ctr = 0.05
    if title_ideas.predicted_ctr:
        title_ctr = max(title_ideas.predicted_ctr) / 10  # Normalize
    
    # Engagement triggers in script
    engagement_triggers = 0
    for pattern in POSITIVE_ENGAGEMENT_PATTERNS:
        engagement_triggers += len(re.findall(pattern, script_lower, re.IGNORECASE))
    
    trigger_score = min(1.0, engagement_triggers / 5)
    
    # Question marks (direct questions to audience)
    question_count = full_script.count('?')
    question_score = min(1.0, question_count / 4)
    
    predicted_engagement = (
        0.3 * cta_base +
        0.1 * placement_bonus +
        0.2 * title_ctr +
        0.25 * trigger_score +
        0.15 * question_score
    )
    
    predicted_engagement = max(0.15, min(0.90, predicted_engagement))
    
    return {
        "engagement_score": predicted_engagement,
        "cta_base": cta_base,
        "placement_bonus": placement_bonus,
        "title_ctr": title_ctr,
        "trigger_score": trigger_score,
        "question_score": question_score,
    }


def score_script_variant(variant: ScriptVariant) -> ScoredScriptVariant:
    """Score a complete script variant."""
    
    # Analyze each component
    hook_analysis = analyze_hook(variant.hook.text, variant.hook.technique)
    retention_analysis = analyze_retention_beats(variant.beats, variant.full_script)
    engagement_analysis = analyze_engagement(
        variant.cta, variant.title_ideas, variant.full_script
    )
    
    # Calculate overall weighted score
    overall_score = (
        SCORE_WEIGHTS["predicted_ctr"] * hook_analysis["predicted_ctr"] / 0.30 +  # Normalize
        SCORE_WEIGHTS["predicted_retention"] * retention_analysis["predicted_retention"] / 0.85 +
        SCORE_WEIGHTS["engagement_score"] * engagement_analysis["engagement_score"] / 0.90
    )
    
    # Combine breakdowns
    score_breakdown = {
        "hook_analysis": hook_analysis,
        "retention_analysis": retention_analysis,
        "engagement_analysis": engagement_analysis,
        "weights": SCORE_WEIGHTS,
    }
    
    return ScoredScriptVariant.from_variant(variant, {
        "predicted_ctr": hook_analysis["predicted_ctr"],
        "predicted_retention": retention_analysis["predicted_retention"],
        "engagement_score": engagement_analysis["engagement_score"],
        "overall_score": overall_score,
        **score_breakdown
    })


def rank_variants(variants: List[ScriptVariant]) -> List[ScoredScriptVariant]:
    """Score and rank multiple variants."""
    scored = [score_script_variant(v) for v in variants]
    return sorted(scored, key=lambda v: v.overall_score, reverse=True)