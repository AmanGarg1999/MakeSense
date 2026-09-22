import logging
from pathlib import Path

import asyncpg

from server.config import settings

logger = logging.getLogger(__name__)

pool = None

async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(dsn=settings.database_url)
        logger.info("Database connection pool created.")
        await run_migrations(pool)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_db():
    global pool
    if pool:
        await pool.close()
        logger.info("Database connection pool closed.")

async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_db() first.")
    return pool

async def run_migrations(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        # Create schema_migrations table if not exists
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Determine directories with migration files
        root_dir = Path(__file__).parent.parent
        migration_dirs = [
            root_dir / "gamification" / "migrations",
            root_dir / "server" / "migrations"
        ]
        
        migration_files = []
        for d in migration_dirs:
            if d.exists() and d.is_dir():
                for f in d.iterdir():
                    if f.suffix == ".sql":
                        migration_files.append(f)
        
        # Sort by filename
        migration_files.sort(key=lambda x: x.name)
        
        for file_path in migration_files:
            filename = file_path.name
            record = await conn.fetchrow('SELECT 1 FROM schema_migrations WHERE filename = $1', filename)
            if not record:
                logger.info(f"Applying migration: {filename}")
                sql = file_path.read_text(encoding='utf-8')
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute('INSERT INTO schema_migrations (filename) VALUES ($1)', filename)
                logger.info(f"Successfully applied {filename}")

async def execute(query: str, *args):
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        return await conn.execute(query, *args)

async def fetch(query: str, *args):
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query: str, *args):
    db_pool = await get_pool()
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(query, *args)
