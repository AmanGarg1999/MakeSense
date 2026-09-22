#!/usr/bin/env python3
"""
MakeSense Topic Categorization Module

Classifies topics into predefined taxonomy categories using keyword matching.
In production, this would call an LLM for more accurate classification.

Taxonomy:
- ML/AI
- Data Science
- Programming
- Creative Arts
- Business/Finance
- Personal Development
- Academic
- Other
"""

import re
from typing import List, Dict, Optional

# Category taxonomy with keywords for classification
CATEGORY_KEYWORDS = {
    "ML/AI": [
        "machine learning", "deep learning", "neural network", "ai", "artificial intelligence",
        "llm", "large language model", "transformer", "bert", "gpt", "computer vision",
        "nlp", "natural language processing", "reinforcement learning", "supervised learning",
        "unsupervised learning", "tensorflow", "pytorch", "keras", "hugging face", "generative ai",
        "diffusion", "stable diffusion", "midjourney", "dall-e", "chatgpt", "claude",
        "foundation model", "fine-tuning", "embedding", "vector database", "rag", "retrieval augmented",
        "agent", "langchain", "llama", "mistral", "gemini", "nemotron", "inference", "training",
        "model", "dataset", "token", "attention", "encoder", "decoder", "transformer architecture"
    ],
    "Data Science": [
        "data science", "data analysis", "data analytics", "pandas", "numpy", "statistics",
        "visualization", "matplotlib", "seaborn", "plotly", "tableau", "power bi", "excel",
        "sql", "database", "etl", "data pipeline", "data engineering", "big data", "spark",
        "hadoop", "kafka", "data warehouse", "data lake", "feature engineering", "exploratory",
        "descriptive statistics", "inferential statistics", "hypothesis testing", "regression",
        "classification", "clustering", "dimensionality reduction", "pca", "time series",
        "forecasting", "anomaly detection", "a/b testing", "experimentation", "dashboard"
    ],
    "Programming": [
        "programming", "coding", "software development", "python", "javascript", "typescript",
        "java", "c++", "c#", "go", "rust", "ruby", "php", "swift", "kotlin", "scala",
        "react", "vue", "angular", "node.js", "django", "flask", "fastapi", "spring",
        "express", "next.js", "remix", "svelte", "solid", "web development", "frontend",
        "backend", "full stack", "api", "rest", "graphql", "grpc", "microservices",
        "docker", "kubernetes", "devops", "ci/cd", "github", "git", "testing", "tdd",
        "design patterns", "clean code", "refactoring", "architecture", "system design",
        "algorithms", "data structures", "leetcode", "competitive programming"
    ],
    "Creative Arts": [
        "art", "design", "drawing", "painting", "illustration", "digital art", "photography",
        "video editing", "video production", "filmmaking", "animation", "motion graphics",
        "after effects", "premiere", "davinci resolve", "blender", "3d modeling", "cad",
        "graphic design", "ui design", "ux design", "figma", "sketch", "adobe", "photoshop",
        "illustrator", "indesign", "creative", "branding", "logo", "typography", "color theory",
        "composition", "music", "guitar", "piano", "drums", "bass", "violin", "instruments",
        "instrument", "songwriting", "singing", "chords", "musical", "audio", "sound design",
        "music production", "ableton", "logic", "pro tools", "podcast", "podcasting", "youtube",
        "twitch", "tiktok", "reels", "shorts", "storytelling", "writing", "blogging",
        "copywriting", "vlogging", "content creator", "creator economy", "audio production",
        "voice over", "recording", "microphone", "audio editing", "audacity", "anchor",
        "spotify", "apple podcasts", "rss feed", "episode", "show notes"
    ],
    "Business/Finance": [
        "business", "finance", "investing", "stock", "crypto", "cryptocurrency", "bitcoin",
        "ethereum", "trading", "portfolio", "wealth", "personal finance", "budgeting",
        "saving", "retirement", "401k", "ira", "etf", "mutual fund", "index fund",
        "real estate", "entrepreneurship", "startup", "venture capital", "funding",
        "business plan", "marketing", "digital marketing", "sales", "growth", "strategy",
        "management", "leadership", "product management", "project management", "agile",
        "scrum", "kanban", "okr", "kpi", "analytics", "conversion", "funnel",
        "customer acquisition", "ecommerce", "dropshipping", "amazon fba", "shopify",
        "freelancing", "consulting", "seo", "sem", "social media marketing", "content marketing",
        "email marketing", "affiliate marketing", "influencer marketing", "brand marketing"
    ],
    "Personal Development": [
        "personal development", "self improvement", "productivity", "habits", "routine",
        "goal setting", "time management", "focus", "deep work", "pomodoro", "mindfulness",
        "meditation", "mental health", "anxiety", "depression", "therapy", "cbt",
        "journaling", "gratitude", "exercise", "fitness", "nutrition", "diet", "sleep",
        "biohacking", "supplements", "longevity", "health", "wellness", "stress management",
        "work life balance", "motivation", "discipline", "consistency", "atomic habits",
        "learning how to learn", "memory", "speed reading", "note taking", "obsidian",
        "notion", "roam", "second brain", "zettelkasten", "pkm", "knowledge management"
    ],
    "Academic": [
        "academic", "research", "paper", "thesis", "dissertation", "phd", "master",
        "bachelor", "university", "college", "course", "study", "exam", "test",
        "mathematics", "calculus", "linear algebra", "probability", "statistics",
        "physics", "chemistry", "biology", "psychology", "sociology", "economics",
        "philosophy", "history", "literature", "linguistics", "computer science",
        "electrical engineering", "mechanical engineering", "civil engineering",
        "assignment", "homework", "project", "lab", "experiment", "theorem", "proof",
        "definition", "concept", "textbook", "lecture", "professor", "grade", "gpa"
    ],
    "Other": []
}

# Default category for unmatched topics
DEFAULT_CATEGORY = "Other"


def normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, remove punctuation."""
    return re.sub(r'[^\w\s]', '', text.lower()).strip()


def classify_topic(topic: str, use_llm: bool = False, llm_client=None) -> str:
    """
    Classify a single topic into one of the taxonomy categories.
    
    Args:
        topic: The topic string to classify
        use_llm: Whether to use LLM-based classification (not implemented yet)
        llm_client: Optional LLM client for future LLM integration
    
    Returns:
        Category name from the taxonomy
    """
    if use_llm and llm_client:
        # Future: LLM-based classification
        return _classify_with_llm(topic, llm_client)
    
    return _classify_with_keywords(topic)


def _classify_with_keywords(topic: str) -> str:
    """Classify topic using keyword matching against category keywords."""
    normalized_topic = normalize_text(topic)
    topic_words = set(normalized_topic.split())
    
    # Score each category
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "Other":
            continue
        
        score = 0
        matched_keywords = []
        for keyword in keywords:
            # Normalize keyword
            norm_keyword = normalize_text(keyword)
            keyword_words = set(norm_keyword.split())
            
            # Check for exact phrase match with word boundaries
            if re.search(r'\b' + re.escape(norm_keyword) + r'\b', normalized_topic):
                score += 5
                matched_keywords.append(f"{keyword}(phrase)")
            # Check for word overlap (ignore single-character tokens like 'c' to avoid accidental false matches)
            else:
                valid_overlap = {w for w in (keyword_words & topic_words) if len(w) > 1}
                if valid_overlap:
                    score += len(valid_overlap)
                    matched_keywords.append(f"{keyword}(words:{valid_overlap})")
        
        if score > 0:
            scores[category] = score
    
    # Return category with highest score
    if scores:
        result = max(scores.items(), key=lambda x: x[1])[0]
        return result
    
    return DEFAULT_CATEGORY


def _classify_with_llm(topic: str, llm_client) -> str:
    """
    Classify topic using LLM.
    Will use Gemini API when configured.
    """
    # TODO: Implement LLM-based classification
    # Would send a prompt like:
    # "Classify this topic into one of: ML/AI, Data Science, Programming, 
    # Creative Arts, Business/Finance, Personal Development, Academic, Other.
    # Topic: {topic}"
    return _classify_with_keywords(topic)


def classify_topics(topics: List[str], use_llm: bool = False, llm_client=None) -> Dict[str, str]:
    """
    Classify multiple topics into categories.
    
    Args:
        topics: List of topic strings
        use_llm: Whether to use LLM-based classification
        llm_client: Optional LLM client
    
    Returns:
        Dictionary mapping topic -> category
    """
    return {topic: classify_topic(topic, use_llm, llm_client) for topic in topics}


def get_all_categories() -> List[str]:
    """Return list of all category names in the taxonomy."""
    return list(CATEGORY_KEYWORDS.keys())


def validate_category(category: str) -> bool:
    """Check if a category is valid in the taxonomy."""
    return category in CATEGORY_KEYWORDS


# Example usage and testing
if __name__ == "__main__":
    test_topics = [
        "Machine Learning fundamentals",
        "Python for data analysis",
        "How to start a podcast",
        "Digital marketing basics",
        "Video editing for beginners",
        "Deep learning with PyTorch",
        "Personal finance and investing",
        "Productivity and time management",
        "Calculus for beginners",
        "React frontend development"
    ]
    
    print("Topic Classification Results:")
    print("=" * 60)
    for topic in test_topics:
        category = classify_topic(topic)
        print(f"  {topic:<40} -> {category}")
    
    print("\nAll categories:", get_all_categories())