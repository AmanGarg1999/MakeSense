"""Main pipeline orchestrator for viral script generation."""

import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from viral_script_pipeline.models.input_models import Topic, Story, ScrapedContent, SourceType
from viral_script_pipeline.models.output_models import (
    ScriptVariant, ScoredScriptVariant, PipelineResult, FrameworkType
)
from viral_script_pipeline.prompts import (
    build_generation_prompt,
    LLMClient,
    parse_generation_output
)
from viral_script_pipeline.scoring import score_script_variant, rank_variants


class ViralScriptPipeline:
    """Main pipeline for generating viral YouTube scripts from scraped topics."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        frameworks: Optional[List[FrameworkType]] = None,
        target_duration_seconds: int = 90,
        variants_per_framework: int = 1,
        output_dir: str = "./output"
    ):
        self.llm_client = llm_client or LLMClient()
        self.frameworks = frameworks or [
            FrameworkType.AIDA,
            FrameworkType.PAS,
            FrameworkType.CURIOSITY_GAP,
        ]
        self.target_duration_seconds = target_duration_seconds
        self.variants_per_framework = variants_per_framework
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_scripts_for_topic(
        self,
        topic: Topic,
        stories: List[Story],
        competitor_insights: Optional[List[str]] = None
    ) -> PipelineResult:
        """Generate script variants for a single topic."""
        
        all_variants = []
        
        for framework in self.frameworks:
            for variant_idx in range(self.variants_per_framework):
                # Build prompt
                prompt = build_generation_prompt(
                    framework=framework,
                    topic=topic,
                    stories=stories,
                    competitor_insights=competitor_insights,
                    target_duration_seconds=self.target_duration_seconds
                )
                
                # Generate script
                try:
                    response = self.llm_client.generate(prompt)
                    raw_output = response.text
                    
                    # Parse into ScriptVariant
                    variant = parse_generation_output(
                        raw_output=raw_output,
                        framework=framework,
                        topic=topic,
                        target_duration=self.target_duration_seconds
                    )
                    
                    all_variants.append(variant)
                    
                except Exception as e:
                    print(f"Error generating {framework.value} variant {variant_idx}: {e}")
                    continue
        
        # Score and rank variants
        scored_variants = rank_variants(all_variants)
        
        # Create pipeline result
        result = PipelineResult(
            topic=topic.topic,
            variants=scored_variants,
            input_context_summary=self._build_context_summary(topic, stories)
        )
        
        return result
    
    def generate_for_multiple_topics(
        self,
        topics: List[Topic],
        stories: List[Story],
        competitor_insights: Optional[List[str]] = None
    ) -> List[PipelineResult]:
        """Generate scripts for multiple topics."""
        results = []
        
        for topic in topics:
            print(f"Generating scripts for topic: {topic.topic}")
            topic_stories = self._filter_relevant_stories(topic, stories)
            result = self.generate_scripts_for_topic(
                topic=topic,
                stories=topic_stories,
                competitor_insights=competitor_insights
            )
            results.append(result)
        
        return results
    
    def run_from_scraped_content(
        self,
        scraped_content: ScrapedContent,
        max_topics: int = 5
    ) -> List[PipelineResult]:
        """Run pipeline from ScrapedContent object."""
        topics = scraped_content.get_topics_for_pipeline(limit=max_topics)
        all_stories = scraped_content.stories + scraped_content.competitor_videos
        competitor_insights = self._extract_competitor_insights(scraped_content.competitor_videos)
        
        return self.generate_for_multiple_topics(
            topics=topics,
            stories=all_stories,
            competitor_insights=competitor_insights
        )
    
    def save_results(self, results: List[PipelineResult], prefix: str = "viral_scripts"):
        """Save results to JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save combined results
        combined = {
            "generated_at": datetime.now().isoformat(),
            "pipeline_config": {
                "frameworks": [f.value for f in self.frameworks],
                "target_duration_seconds": self.target_duration_seconds,
                "variants_per_framework": self.variants_per_framework,
            },
            "results": [r.to_json() for r in results]
        }
        
        combined_path = self.output_dir / f"{prefix}_{timestamp}.json"
        with open(combined_path, 'w') as f:
            json.dump(combined, f, indent=2)
        
        # Save individual topic results
        for result in results:
            topic_safe = result.topic.replace(' ', '_').replace('/', '_')[:50]
            topic_path = self.output_dir / f"{prefix}_{topic_safe}_{timestamp}.json"
            with open(topic_path, 'w') as f:
                json.dump(result.to_json(), f, indent=2)
        
        print(f"Saved {len(results)} results to {self.output_dir}")
        return combined_path
    
    def _filter_relevant_stories(self, topic: Topic, stories: List[Story]) -> List[Story]:
        """Filter stories relevant to a topic."""
        return ScrapedContent(stories=stories).get_relevant_stories(topic, limit=3)
    
    def _extract_competitor_insights(self, competitor_videos: List[Story]) -> List[str]:
        """Extract insights from competitor videos."""
        insights = []
        for video in competitor_videos[:10]:
            if video.metrics:
                views = video.metrics.get('view_count', 0)
                likes = video.metrics.get('like_count', 0)
                if views > 0:
                    insights.append(
                        f"'{video.title}' got {views:,} views, "
                        f"{likes:,} likes (ratio: {likes/views:.2%})"
                    )
        return insights[:5]
    
    def _build_context_summary(self, topic: Topic, stories: List[Story]) -> str:
        """Build a summary of input context for the result."""
        parts = [
            f"Topic: {topic.topic}",
            f"Source: {topic.source.value}",
            f"Stories used: {len(stories)}",
        ]
        if topic.volume:
            parts.append(f"Volume: {topic.volume}")
        return " | ".join(parts)


async def run_pipeline_async(
    topics: List[Topic],
    stories: List[Story],
    frameworks: Optional[List[FrameworkType]] = None,
    **kwargs
) -> List[PipelineResult]:
    """Async version of pipeline execution."""
    pipeline = ViralScriptPipeline(frameworks=frameworks, **kwargs)
    
    # Run generations concurrently
    tasks = [
        asyncio.to_thread(
            pipeline.generate_scripts_for_topic,
            topic=topic,
            stories=pipeline._filter_relevant_stories(topic, stories)
        )
        for topic in topics
    ]
    
    results = await asyncio.gather(*tasks)
    return results


def create_pipeline_from_config(config: Dict[str, Any]) -> ViralScriptPipeline:
    """Factory function to create pipeline from config dict."""
    frameworks = None
    if "frameworks" in config:
        frameworks = [FrameworkType(f) for f in config["frameworks"]]
    
    llm_client = None
    if "llm_config" in config:
        llm_client = LLMClient(**config["llm_config"])
    
    return ViralScriptPipeline(
        llm_client=llm_client,
        frameworks=frameworks,
        target_duration_seconds=config.get("target_duration_seconds", 90),
        variants_per_framework=config.get("variants_per_framework", 1),
        output_dir=config.get("output_dir", "./output")
    )