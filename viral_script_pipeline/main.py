"""Main entry point for viral script generation pipeline."""

from datetime import datetime
from viral_script_pipeline.models.input_models import (
    Topic, Story, ScrapedContent, SourceType
)
from viral_script_pipeline.models.output_models import FrameworkType
from viral_script_pipeline.pipeline import ViralScriptPipeline, create_pipeline_from_config
from viral_script_pipeline.prompts import LLMClient


def create_sample_data() -> ScrapedContent:
    """Create sample scraped content for testing."""
    
    topics = [
        Topic(
            source=SourceType.YOUTUBE_TRENDING,
            topic="AI-generated video content going viral",
            volume=245000,
            url="https://youtube.com/trending",
            metadata={"category": "Technology", "region": "US"}
        ),
        Topic(
            source=SourceType.GOOGLE_TRENDS,
            topic="ChatGPT prompts for content creators",
            volume=189000,
            url="https://trends.google.com",
            metadata={"category": "How-to", "trend_type": "rising"}
        ),
        Topic(
            source=SourceType.TWITTER_X,
            topic="Faceless YouTube channels making $10k/month",
            volume=156000,
            url="https://twitter.com/trending",
            metadata={"hashtags": ["#sidehustle", "#youtube", "#AI"]}
        ),
        Topic(
            source=SourceType.NEWS_SITE,
            topic="New YouTube algorithm update changes everything",
            volume=134000,
            url="https://techcrunch.com/youtube-algorithm-2026",
            metadata={"source": "TechCrunch", "author": "Sarah Chen"}
        ),
        Topic(
            source=SourceType.YOUTUBE_CHANNEL,
            topic="MiniMax H3 video generation breakthrough",
            volume=98000,
            url="https://youtube.com/@ai-video-lab",
            metadata={"channel": "AI Video Lab", "subscribers": 450000}
        ),
    ]
    
    stories = [
        Story(
            source_url="https://techcrunch.com/ai-video-tools-2026",
            title="AI Video Tools Are Reshaping Creator Economy",
            content="""New AI video generation tools like MiniMax H3, Sora, and Runway Gen-3 are enabling creators to produce high-quality video content without cameras, actors, or expensive equipment. The technology has matured to the point where AI-generated videos are indistinguishable from real footage in many cases. Creators are building entire faceless channels using these tools, with some reporting $10k-50k monthly revenue. The key differentiator is no longer video quality but script quality and niche selection.""",
            published_at=datetime.fromisoformat("2026-08-15T10:00:00"),
            author="Marcus Johnson",
            tags=["AI", "video generation", "creator economy", "MiniMax", "Sora"],
            metrics={"views": 245000, "shares": 3400, "comments": 890}
        ),
        Story(
            source_url="https://youtube.com/watch?v=abc123",
            title="I Built a Faceless Channel Using Only AI - Results After 30 Days",
            content="""Documenting my 30-day experiment building a completely AI-generated YouTube channel. Used ChatGPT for scripts, MiniMax for video, ElevenLabs for voiceover. Total cost: $47 in API credits. Result: 127k subscribers, $3,400 revenue. The secret wasn't the tools - it was the script framework. I used a modified AIDA structure with curiosity gaps every 15 seconds. Retention averaged 68% vs 45% for my previous manual videos.""",
            published_at=datetime.fromisoformat("2026-08-20T14:30:00"),
            author="ContentCreatorPro",
            tags=["faceless channel", "AI video", "case study", "MiniMax H3"],
            metrics={"views": 890000, "likes": 34000, "comments": 2100, "retention": 0.68}
        ),
        Story(
            source_url="https://blog.youtube.com/algorithm-update-2026",
            title="YouTube's 2026 Algorithm Update: What Creators Need to Know",
            content="""YouTube has rolled out its largest algorithm update in three years. Key changes: 1) Shorts now factor into long-form recommendations, 2) Retention velocity (first 30 seconds) weighted 40% higher, 3) Topic authority signals boost niche experts, 4) Cross-platform engagement (comments on Community tab, Shorts replies) now counts. Creators adapting to these signals see 2-3x reach increases. The update penalizes clickbait titles that don't deliver - audience satisfaction surveys now directly impact distribution.""",
            published_at=datetime.fromisoformat("2026-08-10T09:00:00"),
            author="YouTube Liaison Team",
            tags=["algorithm", "YouTube update", "Shorts", "retention", "distribution"],
            metrics={"views": 567000, "shares": 12000, "saves": 45000}
        ),
        Story(
            source_url="https://twitter.com/ai_video_guru/status/12345",
            title="Thread: 7 ChatGPT Prompts That Generate Viral Video Scripts",
            content="""1/ The "Curiosity Gap" prompt: "Write a 60-second script about [topic] that opens with a question nobody knows the answer to, teases 3 clues, reveals at 40s, ends with CTA"
2/ The "Contrarian Take" prompt: "Argue against the popular opinion on [topic] with data, then pivot to the nuanced truth"
3/ The "Behind the Scenes" prompt: "Show the messy reality of [successful outcome] - failures, costs, time"
... (7 total prompts with examples)""",
            published_at=datetime.fromisoformat("2026-08-25T16:45:00"),
            author="@ai_video_guru",
            tags=["ChatGPT", "prompts", "viral scripts", "thread"],
            metrics={"likes": 12000, "retweets": 3400, "replies": 567, "bookmarks": 8900}
        ),
        Story(
            source_url="https://youtube.com/watch?v=competitor1",
            title="How I Make $15k/Month with AI Faceless Channels (Full Blueprint)",
            content="Complete breakdown of faceless channel strategy using AI tools. Covers niche selection, script frameworks, video generation pipeline, monetization. 2.3M views.",
            published_at=datetime.fromisoformat("2026-07-15T12:00:00"),
            author="FacelessKing",
            tags=["faceless channel", "AI", "monetization", "blueprint"],
            metrics={"view_count": 2300000, "like_count": 89000, "comment_count": 4500}
        ),
        Story(
            source_url="https://youtube.com/watch?v=competitor2",
            title="MiniMax H3 vs Sora vs Runway: Which AI Video Tool Wins?",
            content="Head-to-head comparison of top AI video generators. Tests prompt adherence, motion quality, consistency. MiniMax H3 wins for character consistency. 1.8M views.",
            published_at=datetime.fromisoformat("2026-08-01T10:00:00"),
            author="AI Video Lab",
            tags=["MiniMax H3", "Sora", "Runway", "comparison", "AI video"],
            metrics={"view_count": 1800000, "like_count": 67000, "comment_count": 3200}
        ),
    ]
    
    return ScrapedContent(
        topics=topics,
        stories=stories,
        competitor_videos=[s for s in stories if "competitor" in s.source_url]
    )


def run_demo():
    """Run a demonstration of the pipeline with sample data."""
    print("=" * 60)
    print("VIRAL SCRIPT GENERATION PIPELINE - DEMO")
    print("=" * 60)
    
    # Create sample data
    print("\n[1/4] Creating sample scraped content...")
    scraped_content = create_sample_data()
    print(f"   Loaded {len(scraped_content.topics)} topics")
    print(f"   Loaded {len(scraped_content.stories)} stories")
    print(f"   Loaded {len(scraped_content.competitor_videos)} competitor videos")
    
    # Initialize pipeline (without LLM for demo - will use mock)
    print("\n[2/4] Initializing pipeline...")
    pipeline = ViralScriptPipeline(
        frameworks=[
            FrameworkType.AIDA,
            FrameworkType.PAS,
            FrameworkType.CURIOSITY_GAP,
        ],
        target_duration_seconds=90,
        variants_per_framework=1,
        output_dir="./viral_script_pipeline/output"
    )
    
    # For demo, we'll create mock variants since we don't have LLM API
    print("\n[3/4] Generating mock script variants (demo mode)...")
    results = generate_mock_results(pipeline, scraped_content)
    
    # Save results
    print("\n[4/4] Saving results...")
    pipeline.save_results(results, prefix="demo_viral_scripts")
    
    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for result in results:
        print(f"\nTopic: {result.topic}")
        print(f"  Variants generated: {len(result.variants)}")
        for i, variant in enumerate(result.get_ranked_variants()[:3]):
            print(f"  #{i+1} [{variant.variant.framework.value}] "
                  f"Overall: {variant.overall_score:.3f} | "
                  f"CTR: {variant.predicted_ctr:.3f} | "
                  f"Retention: {variant.predicted_retention:.1%} | "
                  f"Engagement: {variant.engagement_score:.3f}")
            print(f"      Hook: {variant.variant.hook.text[:60]}...")
            print(f"      Best Title: {variant.variant.title_ideas.best_title()}")
    
    print("\n✓ Demo complete! Check ./viral_script_pipeline/output/ for JSON files")


def generate_mock_results(
    pipeline: ViralScriptPipeline,
    scraped_content: ScrapedContent
) -> list:
    """Generate mock results for demo without LLM calls."""
    from viral_script_pipeline.models.output_models import (
        Hook, RetentionBeat, CTA, TitleIdeas, ScriptVariant, ScoredScriptVariant
    )
    from viral_script_pipeline.scoring import score_script_variant
    
    topics = scraped_content.get_topics_for_pipeline(limit=5)
    results = []
    
    for topic in topics:
        topic_stories = pipeline._filter_relevant_stories(topic, scraped_content.stories)
        competitor_insights = pipeline._extract_competitor_insights(scraped_content.competitor_videos)
        
        variants = []
        for framework in pipeline.frameworks:
            # Create a mock variant for each framework
            variant = create_mock_variant(framework, topic, topic_stories, competitor_insights)
            scored = score_script_variant(variant)
            variants.append(scored)
        
        result = pipeline.generate_scripts_for_topic(topic, topic_stories, competitor_insights)
        result.variants = variants
        results.append(result)
    
    return results


def create_mock_variant(
    framework,
    topic: Topic,
    stories: list,
    competitor_insights: list
):
    """Create a mock script variant for demonstration."""
    from viral_script_pipeline.models.output_models import (
        Hook, RetentionBeat, CTA, TitleIdeas, ScriptVariant, FrameworkType
    )
    
    framework_hooks = {
        FrameworkType.AIDA: Hook(
            text="What if I told you a 19-year-old makes $15k/month without ever showing his face?",
            framework=framework,
            technique="question",
            estimated_retention_impact=0.78
        ),
        FrameworkType.PAS: Hook(
            text="You're posting daily, getting 200 views, and wondering why the algorithm hates you.",
            framework=framework,
            technique="pain_point",
            estimated_retention_impact=0.75
        ),
        FrameworkType.CURIOSITY_GAP: Hook(
            text="This AI tool just replaced my entire video production team. Here's the prompt...",
            framework=framework,
            technique="curiosity_gap",
            estimated_retention_impact=0.82
        ),
    }
    
    framework_beats = {
        FrameworkType.AIDA: [
            RetentionBeat("0:03-0:15", "Meet Alex. 19. Dropped out of college. Built a faceless empire.", "build_tension", "Split screen: dorm room → luxury apartment"),
            RetentionBeat("0:15-0:30", "His secret? Not the AI tools everyone talks about. It's the SCRIPT FRAMEWORK.", "deliver_value", "Text overlay: 'AIDA + Curiosity Gaps = 68% retention'"),
            RetentionBeat("0:30-0:45", "I reverse-engineered his top 50 videos. Same 4-beat pattern every time.", "proof", "Timeline showing beat structure"),
            RetentionBeat("0:45-1:00", "Beat 1: Hook with a question. Beat 2: Tease the answer. Beat 3: Deliver. Beat 4: CTA.", "deliver_value", "Animated beat diagram"),
            RetentionBeat("1:00-1:15", "The tools don't matter. MiniMax, Sora, Runway - they all work IF the script works.", "transition", "Tool logos fading in/out"),
            RetentionBeat("1:15-1:30", "I'm giving you his exact prompt templates free in the description. Steal them.", "payoff", "Arrow pointing to description"),
        ],
        FrameworkType.PAS: [
            RetentionBeat("0:03-0:20", "You spend 20 hours editing. Get 300 views. The algorithm buries you. Why?", "build_tension", "Analytics dashboard flatlining"),
            RetentionBeat("0:20-0:40", "It's not your niche. Not your thumbnail. It's the FIRST 3 SECONDS. You're boring people.", "agitate", "Red X over boring intros"),
            RetentionBeat("0:40-1:00", "Top 1% creators use PAS: Problem → Agitate → Solution. Watch me break it down.", "deliver_value", "PAS framework animation"),
            RetentionBeat("1:00-1:15", "Problem: 'Algorithm hates me.' Agitate: 'While competitors steal your audience.' Solution: 'This framework.'", "payoff", "Side-by-side comparison"),
            RetentionBeat("1:15-1:30", "Download my PAS script template. Next video hits different. Link in bio.", "payoff", "Download button animation"),
        ],
        FrameworkType.CURIOSITY_GAP: [
            RetentionBeat("0:03-0:15", "I found a prompt that makes MiniMax generate CONSISTENT characters. Every. Single. Time.", "tease", "Character consistency comparison grid"),
            RetentionBeat("0:15-0:35", "But there's a catch. The prompt has 3 hidden parameters nobody talks about.", "tease", "Blurred parameter fields"),
            RetentionBeat("0:35-0:55", "Parameter 1: Seed locking. Parameter 2: Reference image weight. Parameter 3: Temporal consistency.", "reveal", "Code snippets revealing"),
            RetentionBeat("0:55-1:10", "Here's the exact prompt structure. Copy-paste. Test in 30 seconds.", "payoff", "Full prompt on screen"),
            RetentionBeat("1:10-1:30", "Want my MiniMax H3 prompt library? 50 tested prompts. Free. Comment 'MINIMAX'.", "extension", "Comment prompt"),
        ],
    }
    
    cta = CTA(
        primary="Comment 'SCRIPT' and I'll DM you my exact prompt templates",
        secondary="Subscribe for weekly AI video breakdowns",
        placement="end",
        style="value_first"
    )
    
    titles = TitleIdeas(
        titles=[
            "The AI Script Framework That Got Me 68% Retention",
            "Stop Using AI Video Tools Wrong (Do This Instead)",
            "19-Year-Old's $15k/Month Faceless Channel Blueprint",
        ],
        thumbnail_concepts=[
            "Split screen: bored creator vs. viral analytics dashboard",
            "MiniMax H3 logo with 'CONSISTENT CHARACTERS' badge",
            "Person holding phone showing $15k revenue screenshot",
        ],
        predicted_ctr=[0.085, 0.072, 0.091]
    )
    
    # Build full script
    hook = framework_hooks[framework]
    beats = framework_beats[framework]
    
    script_parts = [hook.text]
    for beat in beats:
        script_parts.append(beat.content)
    script_parts.append(cta.primary)
    full_script = " ".join(script_parts)
    
    return ScriptVariant(
        framework=framework,
        hook=hook,
        beats=beats,
        cta=cta,
        title_ideas=titles,
        full_script=full_script,
        estimated_duration_seconds=90,
        word_count=len(full_script.split())
    )


if __name__ == "__main__":
    run_demo()