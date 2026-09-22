"""Input data models for the viral script generation pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SourceType(Enum):
    """Types of content sources."""
    YOUTUBE_TRENDING = "youtube_trending"
    GOOGLE_TRENDS = "google_trends"
    TWITTER_X = "twitter_x"
    NEWS_SITE = "news_site"
    YOUTUBE_CHANNEL = "youtube_channel"
    COMPETITOR_VIDEO = "competitor_video"


@dataclass
class Topic:
    """A trending topic discovered by scrapers."""
    source: SourceType
    topic: str
    volume: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    url: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Convert to a string for prompt inclusion."""
        parts = [f"Topic: {self.topic}"]
        if self.volume:
            parts.append(f"Volume: {self.volume}")
        if self.url:
            parts.append(f"Source URL: {self.url}")
        return " | ".join(parts)


@dataclass
class Story:
    """A story/content piece extracted from a source."""
    source_url: str
    title: str
    content: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.now)

    def to_prompt_context(self, max_content_chars: int = 2000) -> str:
        """Convert to a string for prompt inclusion."""
        content_preview = self.content[:max_content_chars]
        if len(self.content) > max_content_chars:
            content_preview += "..."
        
        parts = [
            f"Title: {self.title}",
            f"Source: {self.source_url}",
            f"Content: {content_preview}",
        ]
        if self.author:
            parts.append(f"Author: {self.author}")
        if self.published_at:
            parts.append(f"Published: {self.published_at.isoformat()}")
        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags)}")
        if self.metrics:
            parts.append(f"Metrics: {self.metrics}")
        return "\n".join(parts)


@dataclass
class ScrapedContent:
    """Container for all scraped data for a pipeline run."""
    topics: List[Topic] = field(default_factory=list)
    stories: List[Story] = field(default_factory=list)
    competitor_videos: List[Story] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=datetime.now)

    def get_topics_for_pipeline(self, limit: int = 5) -> List[Topic]:
        """Get top topics for script generation, sorted by volume."""
        sorted_topics = sorted(
            self.topics,
            key=lambda t: t.volume or 0,
            reverse=True
        )
        return sorted_topics[:limit]

    def get_relevant_stories(self, topic: Topic, limit: int = 3) -> List[Story]:
        """Get stories relevant to a topic (simple keyword matching)."""
        topic_keywords = set(topic.topic.lower().split())
        relevant = []
        for story in self.stories:
            story_text = (story.title + " " + story.content).lower()
            if any(kw in story_text for kw in topic_keywords):
                relevant.append(story)
        return relevant[:limit]