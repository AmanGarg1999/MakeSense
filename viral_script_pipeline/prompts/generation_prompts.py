"""Prompt templates for viral script generation using various frameworks."""

from typing import Dict, List
from ..models.output_models import FrameworkType
from ..models.input_models import Topic, Story


# Base system prompt for all frameworks
SYSTEM_PROMPT = """You are an expert YouTube scriptwriter specializing in viral, high-retention content.
Your scripts are optimized for:
- Hook viewers in the first 3 seconds (pattern interrupt, curiosity gap, bold claim)
- Retention beats every 15-30 seconds (tension, value delivery, payoff cycles)
- Clear CTA that converts without feeling salesy
- Titles and thumbnails that maximize CTR

Write for a 60-90 second vertical video (Shorts/Reels/TikTok style) but structure works for longer form too.
Use conversational, energetic tone. Short sentences. Active voice. Visual-first thinking."""


# Framework-specific prompts
FRAMEWORK_PROMPTS: Dict[FrameworkType, str] = {
    FrameworkType.AIDA: """Use the AIDA framework:
ATTENTION: Hook with a pattern interrupt - visual, auditory, or conceptual shock
INTEREST: Build intrigue with a story, surprising fact, or relatable problem
DESIRE: Show the transformation/result/benefit - make them want it
ACTION: Clear, low-friction CTA (subscribe, comment, link in bio)

Structure: Hook (0-3s) → Interest beats (3-30s) → Desire beats (30-60s) → Action (60-90s)""",

    FrameworkType.PAS: """Use the PAS framework:
PROBLEM: Open with a painful, relatable problem (agitate the pain)
AGITATION: Deepen the problem - show consequences, emotional cost, why it persists
SOLUTION: Reveal your solution/insight/answer as the relief
ACTION: CTA tied to the solution

Structure: Hook/Problem (0-5s) → Agitation beats (5-35s) → Solution beats (35-70s) → Action (70-90s)""",

    FrameworkType.CURIOSITY_GAP: """Use the CURIOSITY GAP framework:
GAP OPENING: Pose a question or show a result WITHOUT the explanation
TEASE: Layer clues, near-misses, "almost reveals" 
REVEAL: Deliver the answer with a satisfying "aha!" moment
EXTENSION: Show implications/applications (bonus value)
ACTION: CTA to learn more/deeper dive

Structure: Gap Hook (0-3s) → Tease beats (3-40s) → Reveal (40-60s) → Extension (60-80s) → Action (80-90s)""",

    FrameworkType.HOOK_STORY_OFFER: """Use the HOOK-STORY-OFFER framework:
HOOK: Immediate visual/conceptual grab
STORY: Personal narrative or case study with emotional arc
OFFER: The value proposition (what they get by watching/following)
ACTION: Direct CTA

Structure: Hook (0-3s) → Story beats (3-50s) → Offer (50-70s) → Action (70-90s)""",

    FrameworkType.BEFORE_AFTER_BRIDGE: """Use the BEFORE-AFTER-BRIDGE framework:
BEFORE: Paint the current painful state (viewer sees themselves)
AFTER: Paint the desired future state (emotional pull)
BRIDGE: Your method/insight/content that gets them there
ACTION: CTA to start the journey

Structure: Before Hook (0-5s) → After vision (5-25s) → Bridge beats (25-70s) → Action (70-90s)""",
}


def build_generation_prompt(
    framework: FrameworkType,
    topic: Topic,
    stories: List[Story],
    competitor_insights: List[str] = None,
    target_duration_seconds: int = 90
) -> str:
    """Build the complete prompt for script generation."""
    
    # Format stories for context
    story_context = "\n\n---\n\n".join([
        s.to_prompt_context(max_content_chars=1500) for s in stories[:3]
    ]) if stories else "No source stories provided."
    
    competitor_context = ""
    if competitor_insights:
        competitor_context = "\n\nCOMPETITOR INSIGHTS:\n" + "\n".join([
            f"- {insight}" for insight in competitor_insights[:5]
        ])
    
    prompt = f"""{SYSTEM_PROMPT}

{FRAMEWORK_PROMPTS[framework]}

TARGET TOPIC: {topic.topic}
SOURCE: {topic.source.value}
{f"VOLUME: {topic.volume}" if topic.volume else ""}
{f"SOURCE URL: {topic.url}" if topic.url else ""}

SOURCE STORIES FOR INSPIRATION/FACTS:
{story_context}
{competitor_context}

REQUIREMENTS:
- Target duration: ~{target_duration_seconds} seconds
- Generate 1 hook, 4-6 retention beats, 1 CTA, 3 title ideas + thumbnail concepts
- Hook must work in first 3 seconds (visual + audio)
- Each beat needs timestamp range and purpose
- Titles must be click-worthy but not clickbait
- Include visual cues for each beat

OUTPUT FORMAT (respond with this exact structure):
=== HOOK ===
Text: [hook text]
Technique: [pattern_interrupt|bold_claim|question|visual_tease|story_open|shock_stat]
Retention Impact: [0.0-1.0]

=== BEATS ===
[Timestamp] | [Content] | [Purpose: build_tension|deliver_value|pattern_interrupt|payoff|transition] | [Visual Cue]

=== CTA ===
Primary: [primary CTA text]
Secondary: [optional secondary]
Placement: [early|mid|end|throughout]
Style: [direct|soft|curiosity|value_first]

=== TITLES ===
1. [Title 1] | Pred. CTR: [0.0-1.0]
2. [Title 2] | Pred. CTR: [0.0-1.0]
3. [Title 3] | Pred. CTR: [0.0-1.0]

=== THUMBNAILS ===
1. [Concept 1]
2. [Concept 2]
3. [Concept 3]

=== FULL SCRIPT ===
[Complete assembled script with natural flow, ~{target_duration_seconds}s when spoken]"""
    
    return prompt


def build_refinement_prompt(
    original_script: str,
    scores: dict,
    framework: FrameworkType,
    feedback: str
) -> str:
    """Build a prompt to refine a script based on scores and feedback."""
    return f"""{SYSTEM_PROMPT}

You are refining a {framework.value} script based on scoring feedback.

ORIGINAL SCRIPT:
{original_script}

CURRENT SCORES:
- Predicted CTR: {scores.get('predicted_ctr', 'N/A')}
- Predicted Retention: {scores.get('predicted_retention', 'N/A')}
- Engagement Score: {scores.get('engagement_score', 'N/A')}

FEEDBACK TO ADDRESS:
{feedback}

IMPROVE THE SCRIPT by addressing the feedback. Keep the same framework ({framework.value}).
Output in the same format as the generation prompt."""