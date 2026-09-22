"""Test script for viral script generation pipeline."""

import json
from datetime import datetime
from viral_script_pipeline import (
    ViralScriptPipeline,
    Topic, Story, ScrapedContent, SourceType,
    FrameworkType, LLMClient
)


def test_pipeline_initialization():
    """Test pipeline initializes correctly."""
    pipeline = ViralScriptPipeline(
        frameworks=[FrameworkType.AIDA, FrameworkType.PAS],
        target_duration_seconds=60,
        variants_per_framework=1,
        output_dir="./test_output"
    )
    
    assert len(pipeline.frameworks) == 2
    assert pipeline.target_duration_seconds == 60
    assert pipeline.variants_per_framework == 1
    print("✓ Pipeline initialization test passed")


def test_data_models():
    """Test data model creation and serialization."""
    topic = Topic(
        source=SourceType.YOUTUBE_TRENDING,
        topic="Test Topic",
        volume=10000,
        url="https://example.com"
    )
    
    story = Story(
        source_url="https://example.com/article",
        title="Test Article",
        content="Test content",
        published_at=datetime.now(),
        metrics={"views": 5000}
    )
    
    scraped = ScrapedContent(topics=[topic], stories=[story])
    
    # Test topic filtering
    relevant = scraped.get_relevant_stories(topic, limit=1)
    assert len(relevant) == 1
    
    # Test topic sorting
    topic2 = Topic(source=SourceType.GOOGLE_TRENDS, topic="Low Volume", volume=100)
    scraped.topics.append(topic2)
    top_topics = scraped.get_topics_for_pipeline(limit=1)
    assert top_topics[0].topic == "Test Topic"
    
    print("✓ Data models test passed")


def test_scoring_heuristics():
    """Test scoring functions."""
    from viral_script_pipeline.scoring import (
        analyze_hook, analyze_retention_beats, analyze_engagement,
        score_script_variant, rank_variants
    )
    from viral_script_pipeline.models.output_models import (
        Hook, RetentionBeat, CTA, TitleIdeas, ScriptVariant
    )
    
    # Create test variant
    hook = Hook(
        text="What if I told you this secret makes $10k/month?",
        framework=FrameworkType.AIDA,
        technique="question",
        estimated_retention_impact=0.8
    )
    
    beats = [
        RetentionBeat("0:03-0:15", "Meet John. He cracked the code.", "build_tension", "Split screen"),
        RetentionBeat("0:15-0:30", "The secret isn't the tool. It's the framework.", "deliver_value", "Text overlay"),
        RetentionBeat("0:30-0:45", "Here's the exact 3-step process.", "proof", "Diagram"),
        RetentionBeat("0:45-1:00", "Get the template free in description.", "payoff", "Arrow down"),
    ]
    
    cta = CTA(
        primary="Comment 'TEMPLATE' for instant access",
        placement="end",
        style="value_first"
    )
    
    titles = TitleIdeas(
        titles=["Secret $10k Framework Revealed", "Stop Using Tools Wrong"],
        thumbnail_concepts=["Split screen money vs struggle"],
        predicted_ctr=[0.09, 0.07]
    )
    
    variant = ScriptVariant(
        framework=FrameworkType.AIDA,
        hook=hook,
        beats=beats,
        cta=cta,
        title_ideas=titles,
        full_script=" ".join([hook.text] + [b.content for b in beats] + [cta.primary]),
        estimated_duration_seconds=90,
        word_count=150
    )
    
    # Test scoring
    scored = score_script_variant(variant)
    
    assert 0 < scored.predicted_ctr <= 0.3
    assert 0.2 <= scored.predicted_retention <= 0.85
    assert 0.15 <= scored.engagement_score <= 0.9
    assert 0 < scored.overall_score < 1.0
    assert "hook_analysis" in scored.score_breakdown
    assert "retention_analysis" in scored.score_breakdown
    assert "engagement_analysis" in scored.score_breakdown
    
    # Test ranking
    ranked = rank_variants([variant])
    assert len(ranked) == 1
    assert ranked[0] == scored
    
    print("✓ Scoring heuristics test passed")


def test_prompt_generation():
    """Test prompt building."""
    from viral_script_pipeline.prompts import build_generation_prompt
    
    topic = Topic(
        source=SourceType.YOUTUBE_TRENDING,
        topic="AI Video Trends",
        volume=50000
    )
    
    stories = [
        Story(
            source_url="https://example.com",
            title="AI Video Article",
            content="Content about AI video tools..."
        )
    ]
    
    prompt = build_generation_prompt(
        framework=FrameworkType.AIDA,
        topic=topic,
        stories=stories,
        target_duration_seconds=90
    )
    
    assert "AIDA" in prompt
    assert "AI Video Trends" in prompt
    assert "HOOK" in prompt
    assert "BEATS" in prompt
    assert "CTA" in prompt
    assert "TITLES" in prompt
    
    print("✓ Prompt generation test passed")


def test_mock_generation():
    """Test mock variant generation."""
    from viral_script_pipeline.main import create_mock_variant
    from viral_script_pipeline.scoring import score_script_variant
    
    topic = Topic(
        source=SourceType.YOUTUBE_TRENDING,
        topic="Test Topic",
        volume=10000
    )
    
    for framework in [FrameworkType.AIDA, FrameworkType.PAS, FrameworkType.CURIOSITY_GAP]:
        variant = create_mock_variant(framework, topic, [], [])
        scored = score_script_variant(variant)
        
        assert scored.variant.framework == framework
        assert len(scored.variant.beats) >= 4
        assert scored.variant.hook.text
        assert scored.variant.title_ideas.titles
        assert scored.overall_score > 0
    
    print("✓ Mock generation test passed")


def test_output_serialization():
    """Test JSON serialization of results."""
    from viral_script_pipeline.models.output_models import PipelineResult
    from viral_script_pipeline.main import create_mock_variant
    from viral_script_pipeline.scoring import score_script_variant
    
    topic = Topic(
        source=SourceType.YOUTUBE_TRENDING,
        topic="Serialization Test",
        volume=1000
    )
    
    variant = create_mock_variant(FrameworkType.AIDA, topic, [], [])
    scored = score_script_variant(variant)
    
    result = PipelineResult(
        topic="Serialization Test",
        variants=[scored],
        input_context_summary="Test context"
    )
    
    json_output = result.to_json()
    
    assert "topic" in json_output
    assert "variants" in json_output
    assert len(json_output["variants"]) == 1
    assert "framework" in json_output["variants"][0]
    assert "overall_score" in json_output["variants"][0]
    
    # Verify it's valid JSON
    json_str = json.dumps(json_output)
    parsed = json.loads(json_str)
    assert parsed["topic"] == "Serialization Test"
    
    print("✓ Output serialization test passed")


def test_pipeline_factory():
    """Test pipeline creation from config."""
    from viral_script_pipeline.pipeline import create_pipeline_from_config
    
    config = {
        "frameworks": ["AIDA", "PAS"],
        "target_duration_seconds": 120,
        "variants_per_framework": 2,
        "output_dir": "./test_factory_output"
    }
    
    pipeline = create_pipeline_from_config(config)
    
    assert len(pipeline.frameworks) == 2
    assert pipeline.target_duration_seconds == 120
    assert pipeline.variants_per_framework == 2
    
    print("✓ Pipeline factory test passed")


def run_all_tests():
    """Run all tests."""
    print("Running pipeline tests...\n")
    
    test_pipeline_initialization()
    test_data_models()
    test_scoring_heuristics()
    test_prompt_generation()
    test_mock_generation()
    test_output_serialization()
    test_pipeline_factory()
    
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    run_all_tests()