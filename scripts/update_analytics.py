#!/usr/bin/env python3
"""
Update analytics metrics for MakeSense.
Tracks submissions per week, generation success rate, user satisfaction, and content views.
"""
import json
import os
import datetime
from collections import defaultdict
from typing import Dict, Any

def load_json(filepath: str, default: Any = None) -> Any:
    """Load JSON file, return default if file doesn't exist or is invalid."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}

def save_json(filepath: str, data: Any) -> None:
    """Save data to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def update_submissions_per_week(topics_data: list) -> Dict[str, int]:
    """Calculate submissions per week from topics.json."""
    weekly_counts: Dict[str, int] = defaultdict(int)
    for submission in topics_data:
        timestamp_str = submission.get('timestamp')
        if timestamp_str:
            try:
                # Parse timestamp and get week starting Monday
                dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Get year and week number (Monday as first day of week)
                year, week, _ = dt.isocalendar()
                week_key = f"{year}-W{week:02d}"
                weekly_counts[week_key] += 1
            except ValueError:
                continue
    return dict(weekly_counts)

def update_generation_success_rate() -> Dict[str, Any]:
    """Get generation success rate from workflow runs.
    For MVP, we'll simulate by checking if there's a status file or default to 0.
    In a real implementation, we would use the GitHub API to get workflow run status.
    """
    # Placeholder: In a real scenario, we would fetch workflow runs for content-generator.yml
    # For now, we'll return a default structure
    return {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "rate": 0.0
    }

def update_user_satisfaction(feedback_data: list) -> Dict[str, Any]:
    """Calculate user satisfaction ratio from feedback data."""
    upvotes = sum(1 for f in feedback_data if f.get('rating') == 'up')
    downvotes = sum(1 for f in feedback_data if f.get('rating') == 'down')
    total = upvotes + downvotes
    ratio = upvotes / total if total > 0 else 0.0
    return {
        "upvotes": upvotes,
        "downvotes": downvotes,
        "ratio": ratio
    }

def update_content_views() -> Dict[str, Any]:
    """Get content views.
    For MVP, we'll return 0. In a real implementation, this would be updated
    via a client-side script that triggers a workflow_dispatch to increment a counter.
    """
    return {
        "total": 0,
        "by_content": {}
    }

def generate_markdown_report(analytics: dict) -> str:
    """Generate a markdown report from analytics data."""
    submissions_per_week = analytics.get('submissions_per_week', {})
    generation_success_rate = analytics.get('generation_success_rate', {})
    user_satisfaction = analytics.get('user_satisfaction', {})
    content_views = analytics.get('content_views', {})
    last_updated = analytics.get('last_updated', '')

    # Format last updated
    try:
        last_updated_dt = datetime.datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        formatted_last_updated = last_updated_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        formatted_last_updated = last_updated

    # Submissions per week table
    submissions_rows = []
    if submissions_per_week:
        for week, count in sorted(submissions_per_week.items(), reverse=True)[:4]:  # Last 4 weeks
            submissions_rows.append(f"| {week} | {count} |")
    else:
        submissions_rows.append("| No data | 0 |")

    submissions_table = (
        "| Week | Submissions |\n"
        "|------|-------------|\n"
        + "\n".join(submissions_rows)
    )

    # Generation success rate
    total = generation_success_rate.get('total', 0)
    successful = generation_success_rate.get('successful', 0)
    failed = generation_success_rate.get('failed', 0)
    rate = generation_success_rate.get('rate', 0.0)
    success_rate_percent = rate * 100

    # User satisfaction
    upvotes = user_satisfaction.get('upvotes', 0)
    downvotes = user_satisfaction.get('downvotes', 0)
    ratio = user_satisfaction.get('ratio', 0.0)

    # Content views
    total_views = content_views.get('total', 0)
    unique_content = len(content_views.get('by_content', {}))

    markdown = f"""# MakeSense Analytics Report

*Last updated: {formatted_last_updated}*

## Submissions per Week
{submissions_table}

## Generation Success Rate
- **Total Runs**: {total}
- **Successful**: {successful}
- **Failed**: {failed}
- **Success Rate**: {success_rate_percent:.1f}%

## User Satisfaction
- **Upvotes**: {upvotes}
- **Downvotes**: {downvotes}
- **Satisfaction Ratio**: {ratio:.2f}

## Content Views
- **Total Views**: {total_views}
- **Unique Content Pieces Viewed**: {unique_content}

---
*This report is generated automatically by the MakeSense analytics system.*
"""
    return markdown

def main() -> None:
    # Paths: script is in <base_dir>/scripts/update_analytics.py
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    topics_path = os.path.join(data_dir, 'topics.json')
    feedback_path = os.path.join(data_dir, 'feedback.json')
    analytics_path = os.path.join(data_dir, 'analytics.json')
    reports_dir = os.path.join(base_dir, 'reports')
    report_path = os.path.join(reports_dir, 'analytics-report.md')
    
    # Load data
    topics_data = load_json(topics_path, [])
    feedback_data = load_json(feedback_path, [])
    analytics = load_json(analytics_path, {
        "submissions_per_week": {},
        "generation_success_rate": {"total": 0, "successful": 0, "failed": 0, "rate": 0.0},
        "user_satisfaction": {"upvotes": 0, "downvotes": 0, "ratio": 0.0},
        "content_views": {"total": 0, "by_content": {}},
        "last_updated": ""
    })
    
    # Update metrics
    analytics["submissions_per_week"] = update_submissions_per_week(topics_data)
    analytics["generation_success_rate"] = update_generation_success_rate()
    analytics["user_satisfaction"] = update_user_satisfaction(feedback_data)
    analytics["content_views"] = update_content_views()
    analytics["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Save analytics
    save_json(analytics_path, analytics)
    print(f"Analytics updated and saved to {analytics_path}")

    # Ensure reports directory exists
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate and save markdown report
    markdown_report = generate_markdown_report(analytics)
    with open(report_path, 'w') as f:
        f.write(markdown_report)
    print(f"Markdown report generated and saved to {report_path}")

if __name__ == "__main__":
    main()