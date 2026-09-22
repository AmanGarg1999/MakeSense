#!/usr/bin/env python3
"""
MakeSense Content Generation Pipeline

Placeholder script that reads topics from data/topics.json and simulates
content generation for each topic. In production, this would call LLMs,
create structured learning materials, etc.

Supports multi-format export: Markdown (source), HTML (rendered), PDF (download)
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Import categorization module
sys.path.insert(0, str(Path(__file__).parent))
from categorize import classify_topic, get_all_categories

# Paths
REPO_ROOT = Path(__file__).parent.parent
TOPICS_FILE = REPO_ROOT / "data" / "topics.json"
FEEDBACK_FILE = REPO_ROOT / "data" / "feedback.json"
OUTPUT_DIR = REPO_ROOT / "generated-content"
LOG_FILE = REPO_ROOT / "logs" / "generation.log"
TEMPLATE_FILE = REPO_ROOT / "templates" / "content-template.html"

# Chromium path for PDF generation
CHROMIUM_PATHS = [
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/snap/bin/chromium",
]

def find_chromium():
    """Find available Chromium/Chrome executable."""
    for path in CHROMIUM_PATHS:
        if Path(path).exists():
            return path
    return None

CHROMIUM_EXEC = find_chromium()

def setup_logging():
    """Ensure log directory exists."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def log_message(message: str):
    """Log message to both console and file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def load_topics():
    """Load topics from JSON file."""
    if not TOPICS_FILE.exists():
        log_message(f"Topics file not found at {TOPICS_FILE}")
        return []

    try:
        with open(TOPICS_FILE, "r") as f:
            data = json.load(f)
        log_message(f"Loaded {len(data)} topic submissions")
        return data
    except json.JSONDecodeError as e:
        log_message(f"Error parsing topics.json: {e}")
        return []

def load_feedback():
    """Load feedback from JSON file."""
    if not FEEDBACK_FILE.exists():
        log_message(f"Feedback file not found at {FEEDBACK_FILE}")
        return []

    try:
        with open(FEEDBACK_FILE, "r") as f:
            data = json.load(f)
        log_message(f"Loaded {len(data)} feedback items")
        return data
    except json.JSONDecodeError as e:
        log_message(f"Error parsing feedback.json: {e}")
        return []

def get_feedback_summary(feedback_data: list, topic: str, submission_id: str) -> dict:
    """Get feedback summary for a specific topic/submission."""
    relevant_feedback = [
        f for f in feedback_data
        if f.get("topic") == topic and f.get("submission_id") == submission_id
    ]

    up_count = sum(1 for f in relevant_feedback if f.get("feedback_type") == "up")
    down_count = sum(1 for f in relevant_feedback if f.get("feedback_type") == "down")
    total = len(relevant_feedback)

    # Get recent comments (last 5)
    comments = [f.get("comment") for f in relevant_feedback if f.get("comment")]
    recent_comments = comments[-5:] if comments else []

    return {
        "up_votes": up_count,
        "down_votes": down_count,
        "total_votes": total,
        "score": up_count - down_count,
        "recent_comments": recent_comments
    }

def load_template():
    """Load the HTML template."""
    if not TEMPLATE_FILE.exists():
        log_message(f"Template file not found at {TEMPLATE_FILE}")
        return None
    return TEMPLATE_FILE.read_text()

def render_html(template: str, **kwargs) -> str:
    """Render HTML template with provided variables."""
    html = template
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return html

def markdown_to_html(markdown_content: str) -> str:
    """Convert markdown to HTML using pandoc."""
    try:
        result = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html", "--no-highlight"],
            input=markdown_content,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout
        else:
            log_message(f"Pandoc error: {result.stderr}")
            return markdown_content  # fallback
    except Exception as e:
        log_message(f"Pandoc conversion failed: {e}")
        return markdown_content  # fallback

def html_to_pdf(html_file: Path, pdf_file: Path) -> bool:
    """Convert HTML file to PDF using Chromium headless."""
    if not CHROMIUM_EXEC:
        log_message("No Chromium/Chrome executable found for PDF generation")
        return False

    try:
        result = subprocess.run(
            [
                CHROMIUM_EXEC,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--print-to-pdf={pdf_file}",
                f"file://{html_file.absolute()}"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and pdf_file.exists() and pdf_file.stat().st_size > 0:
            log_message(f"PDF generated via Chromium: {pdf_file} ({pdf_file.stat().st_size} bytes)")
            return True
        else:
            log_message(f"Chromium PDF generation failed: {result.stderr}")
            return False
    except Exception as e:
        log_message(f"PDF generation failed: {e}")
        return False

def generate_content_for_topic(topic_submission: dict, feedback_data: list, template: str) -> dict:
    """
    Placeholder content generation for a single topic submission.
    In production, this would:
    1. Call an LLM to create structured learning content
    2. Generate markdown/HTML/PDF materials
    3. Create exercises, quizzes, etc.
    """
    submission_id = topic_submission.get("id", "unknown")
    name = topic_submission.get("name", "Anonymous")
    topics = topic_submission.get("topics", [])
    timestamp = topic_submission.get("timestamp", datetime.now().isoformat())

    log_message(f"Processing submission {submission_id} from {name} with {len(topics)} topics")

    generated_items = []

    for i, topic in enumerate(topics):
        # Classify the topic into a category
        category = classify_topic(topic)

        # Create a safe filename
        safe_topic = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic)
        safe_topic = safe_topic[:50].strip().replace(" ", "-").lower()

        # Get feedback summary for this topic
        feedback_summary = get_feedback_summary(feedback_data, topic, submission_id)

        # Generate markdown content
        content_md = f"""# Learning Content: {topic}

**Generated for:** {name}
**Submission ID:** {submission_id}
**Requested:** {timestamp}
**Generated:** {datetime.now().isoformat()}
**Topic Index:** {i + 1}/{len(topics)}
**Category:** {category}
**Content File:** {safe_topic}.md

---

## Overview

This is a placeholder for learning content about **{topic}**.

In a production pipeline, this would contain:
- Structured lesson plans
- Interactive exercises
- Code examples (for technical topics)
- Quizzes and assessments
- Further reading resources

## Proposed Structure

1. **Introduction** - What is {topic} and why does it matter?
2. **Fundamentals** - Core concepts and terminology
3. **Hands-on Practice** - Step-by-step exercises
4. **Real-world Applications** - How this applies in practice
5. **Next Steps** - Where to go deeper

## Status

✅ Topic received and queued for content generation
⏳ Content generation in progress (placeholder)
⬜ Content review and quality assurance
⬜ Published to learning platform

---

## Feedback Summary

**Community Feedback:** {feedback_summary['up_votes']} 👍 / {feedback_summary['down_votes']} 👎 (Score: {feedback_summary['score']:+d})"""

        # Add feedback-informed improvements if there's feedback
        if feedback_summary['total_votes'] > 0:
            content_md += """## Feedback-Informed Improvements

Based on community feedback, this version includes:

"""
            if feedback_summary['down_votes'] > feedback_summary['up_votes']:
                content_md += "- **More practical examples** - Users requested more hands-on content\n"
                content_md += "- **Clearer explanations** - Simplified technical jargon based on feedback\n"
                content_md += "- **Additional resources** - Added further reading links\n"
            elif feedback_summary['up_votes'] > feedback_summary['down_votes']:
                content_md += "- **Expanded popular sections** - Enhanced areas users found most helpful\n"
                content_md += "- **Deeper dives** - Added advanced topics based on positive reception\n"
            else:
                content_md += "- **Balanced improvements** - Addressed mixed feedback with comprehensive updates\n"

            if feedback_summary['recent_comments']:
                content_md += "\n**Recent User Comments:**\n"
                for comment in feedback_summary['recent_comments']:
                    content_md += f"- \"{comment}\"\n"

            content_md += "\n"

        content_md += f"""---

## Feedback

**Was this content helpful?**

<div class="feedback-buttons" data-content-file="{submission_id}-{i+1}-{safe_topic}.md" data-topic="{topic}" data-submission-id="{submission_id}">
    <button class="feedback-btn thumbs-up" data-feedback="up" title="Helpful">👍 Helpful</button>
    <button class="feedback-btn thumbs-down" data-feedback="down" title="Not helpful">👎 Not Helpful</button>
</div>
<div class="feedback-message" style="display: none;"></div>

---

*This content was automatically generated by the MakeSense pipeline.*
*Pipeline version: 1.0.0*"""

        # Write markdown file
        md_file = OUTPUT_DIR / f"{submission_id}-{i+1}-{safe_topic}.md"
        md_file.write_text(content_md)

        # Convert markdown to HTML for content body
        content_html = markdown_to_html(content_md)

        # Generate HTML file using template
        generated_at = datetime.now().isoformat()
        html_content = render_html(
            template,
            title=f"Learning Content: {topic}",
            generated_at=generated_at,
            category=category,
            submission_id=submission_id,
            content=content_html,
            markdown_url=f"{submission_id}-{i+1}-{safe_topic}.md",
            pdf_url=f"{submission_id}-{i+1}-{safe_topic}.pdf",
            content_file=f"{submission_id}-{i+1}-{safe_topic}.md",
            topic=topic
        )
        html_file = OUTPUT_DIR / f"{submission_id}-{i+1}-{safe_topic}.html"
        html_file.write_text(html_content)

        # Generate PDF file using Chromium
        pdf_file = OUTPUT_DIR / f"{submission_id}-{i+1}-{safe_topic}.pdf"
        pdf_success = html_to_pdf(html_file, pdf_file)

        generated_items.append({
            "topic": topic,
            "category": category,
            "file": str(md_file.relative_to(REPO_ROOT)),
            "html_file": str(html_file.relative_to(REPO_ROOT)),
            "pdf_file": str(pdf_file.relative_to(REPO_ROOT)) if pdf_success else None,
            "status": "placeholder_generated"
        })

        log_message(f"  Generated: {topic} -> {md_file.name}, {html_file.name}" + (f", {pdf_file.name}" if pdf_success else ""))

    return {
        "submission_id": submission_id,
        "name": name,
        "generated_count": len(generated_items),
        "items": generated_items
    }

def main():
    """Main entry point."""
    log_message("=" * 60)
    log_message("MakeSense Content Generation Pipeline Started")
    log_message("=" * 60)

    setup_logging()

    # Check for Chromium
    if not CHROMIUM_EXEC:
        log_message("WARNING: No Chromium/Chrome found. PDF generation will be skipped.")
    else:
        log_message(f"Using Chromium for PDF: {CHROMIUM_EXEC}")

    # Load HTML template
    template = load_template()
    if not template:
        log_message("ERROR: Could not load HTML template. Exiting.")
        return 1

    topics = load_topics()

    if not topics:
        log_message("No topics to process. Exiting.")
        return 0

    # Process only pending submissions
    pending = [t for t in topics if t.get("status") == "pending"]
    log_message(f"Found {len(pending)} pending submissions out of {len(topics)} total")

    if not pending:
        log_message("No pending submissions. Exiting.")
        return 0

    all_results = []

    # Load feedback data once
    feedback_data = load_feedback()

    for submission in pending:
        try:
            result = generate_content_for_topic(submission, feedback_data, template)
            all_results.append(result)

            # Update status in memory (in production, would update the JSON file)
            submission["status"] = "processing"
            submission["generated_at"] = datetime.now().isoformat()
            submission["generated_items"] = result["items"]
            # Add categories array at submission level for filtering
            submission["categories"] = list(set(item["category"] for item in result["items"]))

        except Exception as e:
            log_message(f"Error processing submission {submission.get('id')}: {e}")
            submission["status"] = "error"
            submission["error"] = str(e)

    # Write updated topics back (with status changes)
    try:
        with open(TOPICS_FILE, "w") as f:
            json.dump(topics, f, indent=2)
        log_message(f"Updated topics.json with {len(pending)} processed submissions")
    except Exception as e:
        log_message(f"Error writing updated topics.json: {e}")

    # Summary
    total_generated = sum(r["generated_count"] for r in all_results)
    log_message("=" * 60)
    log_message(f"Pipeline Complete: {len(all_results)} submissions processed, {total_generated} content items generated")
    log_message("=" * 60)

    # Output summary for GitHub Actions
    print(f"::notice::Processed {len(all_results)} submissions, generated {total_generated} content items")

    return 0

if __name__ == "__main__":
    sys.exit(main())