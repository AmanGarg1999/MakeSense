#!/usr/bin/env python3
"""
Nightly Skill Rating Recalculation Job

Cron job to recalculate all user skill ratings from raw engagement evidence.
Run daily at 2 AM UTC via cron or scheduler.

Usage:
    python -m gamification.jobs.nightly_skill_update
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamification.skills import nightly_skill_recalculation, update_skill_taxonomy_from_content

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL environment variable required")
        sys.exit(1)

    taxonomy_result = {"error": "skipped"}

    logger.info("=" * 60)
    logger.info("Starting nightly gamification jobs")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    logger.info("=" * 60)

    # 1. Sync skill taxonomy from content
    logger.info("Step 1: Syncing skill taxonomy from content...")
    try:
        taxonomy_result = await update_skill_taxonomy_from_content(dsn)
        logger.info(f"Skill taxonomy sync complete: {taxonomy_result}")
    except Exception as e:
        logger.error(f"Skill taxonomy sync failed: {e}", exc_info=True)
        # Don't exit - continue with recalculation

    # 2. Recalculate all skill ratings
    logger.info("Step 2: Recalculating all skill ratings...")
    try:
        recalc_result = await nightly_skill_recalculation(dsn)
        logger.info(f"Skill recalculation complete: {recalc_result}")
    except Exception as e:
        logger.error(f"Skill recalculation failed: {e}", exc_info=True)
        sys.exit(1)

    # 3. Summary
    logger.info("=" * 60)
    logger.info("Nightly gamification jobs completed successfully")
    logger.info("=" * 60)

    # Output JSON for monitoring/alerting
    print(json.dumps({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "taxonomy_sync": taxonomy_result if 'taxonomy_result' in locals() else {"error": "skipped"},
        "skill_recalculation": recalc_result,
        "status": "success"
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())