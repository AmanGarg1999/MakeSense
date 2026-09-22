#!/usr/bin/env python3
"""
Gamification Migration Runner

Applies all gamification migrations in order.
Run from project root: python -m gamification.migrations.run_migrations
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent

MIGRATION_FILES = [
    "001_gamification_schema.sql",
    "002_seed_data.sql",
]


async def run_migrations(dsn: str):
    """Run all migrations in order."""
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

    try:
        async with pool.acquire() as conn:
            # Create migration tracking table if not exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    checksum VARCHAR(64)
                )
            """)

            for migration_file in MIGRATION_FILES:
                migration_path = MIGRATIONS_DIR / migration_file

                if not migration_path.exists():
                    logger.error(f"Migration file not found: {migration_path}")
                    continue

                # Check if already applied
                applied = await conn.fetchval(
                    "SELECT 1 FROM schema_migrations WHERE migration_name = $1",
                    migration_file
                )

                if applied:
                    logger.info(f"Skipping already applied: {migration_file}")
                    continue

                logger.info(f"Applying migration: {migration_file}")

                # Read and execute migration
                sql_content = migration_path.read_text()

                try:
                    await conn.execute(sql_content)
                except Exception as e:
                    logger.error(f"Failed to apply {migration_file}: {e}")
                    raise

                # Record migration
                import hashlib
                checksum = hashlib.sha256(sql_content.encode()).hexdigest()
                await conn.execute("""
                    INSERT INTO schema_migrations (migration_name, checksum)
                    VALUES ($1, $2)
                """, migration_file, checksum)

                logger.info(f"Applied: {migration_file}")

            logger.info("All migrations completed successfully!")

            # Show applied migrations
            rows = await conn.fetch("""
                SELECT migration_name, applied_at FROM schema_migrations
                ORDER BY applied_at
            """)
            logger.info("Applied migrations:")
            for row in rows:
                logger.info(f"  - {row['migration_name']} at {row['applied_at']}")

    finally:
        await pool.close()


async def rollback_migration(dsn: str, migration_name: str):
    """Rollback a specific migration (if rollback SQL provided)."""
    logger.warning(f"Rollback requested for {migration_name}")
    logger.warning("Manual rollback required - no automatic rollback implemented")
    # In production, you'd have rollback SQL files or use pg_dump restore points


async def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL environment variable required")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        if len(sys.argv) < 3:
            logger.error("Usage: python -m gamification.migrations.run_migrations rollback <migration_name>")
            sys.exit(1)
        await rollback_migration(dsn, sys.argv[2])
    else:
        await run_migrations(dsn)


if __name__ == "__main__":
    asyncio.run(main())