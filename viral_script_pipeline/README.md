# Viral Script Generation Pipeline

A Python pipeline that generates YouTube-optimized viral video scripts from scraped topics and stories. Uses proven copywriting frameworks (AIDA, PAS, Curiosity Gap) and includes a scoring heuristic to rank script variants by predicted CTR, retention, and engagement.

## Features

- **Multi-framework generation**: AIDA, PAS, Curiosity Gap, Hook-Story-Offer, Before-After-Bridge
- **Structured output**: Hook (0-3s), retention beats, CTA, title/thumbnails ideas
- **Scoring heuristic**: Predicts CTR, retention, engagement with detailed breakdown
- **Ranked variants**: 3 variants per topic, sorted by composite score
- **JSON output**: Machine-readable results for downstream automation
- **Extensible**: Easy to add new frameworks, scoring signals, or LLM providers

## Installation

```bash
cd /home/huntingvision/viral_script_pipeline
pip install -e .
```

Requires: `openai` (for NVIDIA/OpenAI API), `anthropic` (optional), `jsonschema`

## Quick Start

```python
from viral_script_pipeline import (
    ViralScriptPipeline,
    Topic, Story, ScrapedContent, SourceType,
    FrameworkType
)

# 1. Create or load scraped content
scraped = ScrapedContent(
    topics=[
        Topic(
            source=SourceType.YOUTUBE_TRENDING,
            topic="AI video generation trends 2026",
            volume=150000,
            url="https://youtube.com/trending"
        ),
        # ... more topics
    ],
    stories=[
        Story(
            source_url="https://example.com/article",
            title="AI Video Tools Revolutionize Creation",
            content="Full article text here...",
            metrics={"views": 100000}
        ),
        # ... more stories
    ]
)

# 2. Initialize pipeline
pipeline = ViralScriptPipeline(
    frameworks=[FrameworkType.AIDA, FrameworkType.PAS, FrameworkType.CURIOSITY_GAP],
    target_duration_seconds=90,
    output_dir="./my_output"
)

# 3. Run pipeline
results = pipeline.run_from_scraped_content(scraped_content=scraped, max_topics=5)

# 4. Save results
pipeline.save_results(results, prefix="my_campaign")

# 5. Access top scripts
for result in results:
    top = result.top_variant()
    print(f"Topic: {result.topic}")
    print(f"Best Framework: {top.variant.framework.value}")
    print(f"Overall Score: {top.overall_score:.3f}")
    print(f"Hook: {top.variant.hook.text}")
    print(f"Best Title: {top.variant.title_ideas.best_title()}")
```

## Architecture

```
viral_script_pipeline/
├── models/
│   ├── input_models.py    # Topic, Story, ScrapedContent, SourceType
│   └── output_models.py   # ScriptVariant, ScoredScriptVariant, PipelineResult
├── prompts/
│   ├── generation_prompts.py  # Framework-specific prompts
│   ├── llm_client.py          # LLM API wrapper
│   └── parser.py              # Output parser
├── scoring/
│   └── heuristics.py     # CTR, retention, engagement scoring
├── pipeline.py           # Main orchestrator
└── main.py               # Demo entry point
```

## Data Models

### Input: ScrapedContent
```python
ScrapedContent(
    topics: List[Topic],           # Trending topics with volume/source
    stories: List[Story],          # Extracted articles/videos
    competitor_videos: List[Story] # Competitor metadata
)
```

### Output: PipelineResult (per topic)
```python
PipelineResult(
    topic: str,
    variants: List[ScoredScriptVariant],  # Ranked by overall_score
    generated_at: str,
    input_context_summary: str
)
```

### ScoredScriptVariant
```python
ScoredScriptVariant(
    variant: ScriptVariant,      # Full script with hook, beats, CTA, titles
    predicted_ctr: float,        # 0-1 (click-through rate)
    predicted_retention: float,  # 0-1 (average viewer retention)
    engagement_score: float,     # 0-1 (likes/comments/shares potential)
    overall_score: float,        # Weighted composite
    score_breakdown: dict        # Detailed component scores
)
```

## Frameworks

| Framework | Best For | Structure |
|-----------|----------|-----------|
| **AIDA** | Educational, product demos | Attention → Interest → Desire → Action |
| **PAS** | Pain-point content | Problem → Agitation → Solution → Action |
| **Curiosity Gap** | Mystery, reveals, tutorials | Gap → Tease → Reveal → Extension → Action |
| **Hook-Story-Offer** | Personal brand, case studies | Hook → Story → Offer → Action |
| **Before-After-Bridge** | Transformations, courses | Before → After → Bridge → Action |

## Scoring Heuristic

The pipeline scores each variant on three dimensions:

1. **Predicted CTR (35%)**: Hook technique, power words, length, curiosity signals
2. **Predicted Retention (40%)**: Beat count, purpose diversity, pattern interrupts, visual cues
3. **Engagement Score (25%)**: CTA style/placement, title CTR, question count, engagement triggers

### Hook Techniques & Base Scores
- `shock_stat`: 0.80
- `pattern_interrupt`: 0.75
- `bold_claim`: 0.70
- `visual_tease`: 0.70
- `question`: 0.65
- `story_open`: 0.60

## Configuration

```python
pipeline = ViralScriptPipeline(
    llm_client=LLMClient(
        model="nvidia/nemotron-3-ultra-550b-a55b",
        provider="nvidia",
        api_key="your-key",
        temperature=0.7,
        max_tokens=4000
    ),
    frameworks=[FrameworkType.AIDA, FrameworkType.PAS, FrameworkType.CURIOSITY_GAP],
    target_duration_seconds=90,
    variants_per_framework=1,  # Generate N variants per framework
    output_dir="./output"
)
```

### From Config Dict
```python
config = {
    "frameworks": ["AIDA", "PAS", "CURIOSITY_GAP"],
    "target_duration_seconds": 90,
    "variants_per_framework": 2,
    "output_dir": "./output",
    "llm_config": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "provider": "nvidia",
        "api_key": "your-key"
    }
}
pipeline = create_pipeline_from_config(config)
```

## Output Files

The pipeline saves:
- **Combined JSON**: All topics + variants with full scores
- **Per-topic JSON**: Individual topic results for easy loading

Example combined output structure:
```json
{
  "generated_at": "2026-09-03T15:36:06",
  "pipeline_config": {...},
  "results": [
    {
      "topic": "AI video trends",
      "variants": [
        {
          "framework": "AIDA",
          "predicted_ctr": 0.085,
          "predicted_retention": 0.405,
          "engagement_score": 0.402,
          "overall_score": 0.652,
          "hook": {"text": "...", "technique": "question"},
          "beats": [...],
          "cta": {...},
          "title_ideas": {...},
          "full_script": "..."
        }
      ]
    }
  ]
}
```

## Integration with Scrapers

The pipeline accepts data from the Figranium scrapers built in the parent task:

```python
# From trending topics scraper (t_9d181e36)
topics = [
    Topic(source=SourceType.YOUTUBE_TRENDING, topic=t["topic"], volume=t["volume"])
    for t in trending_data
]

# From story/content scraper (t_b559a739)
stories = [
    Story(source_url=s["source_url"], title=s["title"], content=s["content"], ...)
    for s in scraped_content
]

# From competitor scraper (t_834981d6)
competitor_videos = [
    Story(source_url=v["url"], title=v["title"], metrics=v["stats"], ...)
    for v in competitor_data
]

scraped = ScrapedContent(topics=topics, stories=stories, competitor_videos=competitor_videos)
results = pipeline.run_from_scraped_content(scraped)
```

## Running the Demo

```bash
cd /home/huntingvision
python -m viral_script_pipeline.main
```

Generates mock results for 5 topics × 3 frameworks = 15 script variants with scores.

## Extending the Pipeline

### Add a New Framework
1. Add to `FrameworkType` enum in `output_models.py`
2. Add prompt in `FRAMEWORK_PROMPTS` dict in `generation_prompts.py`
3. Add hook technique scoring in `heuristics.py`

### Add Custom Scoring Signals
```python
from viral_script_pipeline.scoring import analyze_hook

# Custom hook analysis
def my_hook_analyzer(hook_text, technique):
    base = analyze_hook(hook_text, technique)
    # Add your signals
    base["my_custom_signal"] = calculate_my_signal(hook_text)
    return base
```

### Use Different LLM Provider
```python
client = LLMClient(
    model="claude-3-opus-20240229",
    provider="anthropic",
    api_key="your-anthropic-key"
)
pipeline = ViralScriptPipeline(llm_client=client)
```

## Requirements

- Python 3.10+
- openai >= 1.0.0
- anthropic (optional)
- jsonschema
- pydantic (for validation, optional)

## License

Internal tool for Hermes Agent workflow automation.