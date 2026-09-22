"""
Engagement points calculation and leveling engine.

Implements:
1. PointsRules class with configurable weights per event_type
2. LevelThresholds class loading XP boundaries from config
3. Function `process_user_events(user_id, since_timestamp)` that aggregates new events, 
   computes delta_points, updates UserLevel and EngagementPoints ledger atomically
4. Idempotency via event_id deduplication
"""

import asyncio
import asyncpg
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import yaml
import json

logger = logging.getLogger(__name__)

# ============================================================================
# Points Rules Engine
# ============================================================================

@dataclass
class PointsRules:
    """Configurable points weighting system for different event types."""
    rules: Dict[str, int]
    
    def __init__(self, rules: Optional[Dict[str, int]] = None):
        if rules is None:
            self.rules = self._load_default_rules()
        else:
            self.rules = rules
    
    def _load_default_rules(self) -> Dict[str, int]:
        """Load default points rules."""
        return {
            "course_completion": 100,
            "lesson_completion": 20,
            "question_answer_correct": 10,
            "question_answer_incorrect": 5,
            "streak_bonus": 50,
            "daily_login": 5,
            "peer_help": 15,
            "content_contribution": 25,
            "review_completion": 15,
            "achievement_unlock": 0,
            "referral_bonus": 50,
            "manual_adjustment": 0,
        }
    
    def get_points(self, event_type: str) -> int:
        """Get points for a given event type.
        
        Args:
            event_type: The type of event (e.g., 'lesson_completion')
            
        Returns:
            Points awarded for the event type, 0 if not found
        """
        return self.rules.get(event_type, 0)
    
    def add_rule(self, event_type: str, points: int):
        """Add or update a points rule."""
        self.rules[event_type] = points
        logger.info(f"Added points rule: {event_type} = {points}")
    
    def remove_rule(self, event_type: str):
        """Remove a points rule."""
        if event_type in self.rules:
            del self.rules[event_type]
            logger.info(f"Removed points rule: {event_type}")

# ============================================================================
# Configuration Loading
# ============================================================================

def load_points_rules(config_path: str = "gamification/config/points_rules.yaml") -> PointsRules:
    """Load points rules from YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            rules = yaml.safe_load(f)
        logger.info(f"Loaded points rules from {config_path}")
        return PointsRules(rules)
    except FileNotFoundError:
        logger.warning(f"Points rules file not found at {config_path}, using defaults")
        # Default points rules
        return PointsRules()  # Will use _load_default_rules
    except Exception as e:
        logger.error(f"Error loading points rules: {e}")
        raise

# ============================================================================
# Level Thresholds Engine
# ============================================================================

@dataclass
class LevelThresholds:
    """Loads and manages XP thresholds for level progression."""
    thresholds: List[Tuple[int, str, int, str, str]]  # (level_id, level_name, xp_threshold, xp_to_next, badge_icon)
    _thresholds_dict: Dict[int, Tuple] = None
    
    def __init__(self, thresholds: Optional[List[Tuple]] = None):
        if thresholds is None:
            self.thresholds = self._load_default_thresholds()
        else:
            self.thresholds = thresholds
        self._build_thresholds_dict()
    
    def _load_default_thresholds(self) -> List[Tuple]:
        """Load default thresholds from the user_levels table.
        
        In a real implementation, this would query the database.
        For now, we return the hardcoded values from the schema.
        """
        return [
            (1, 'Novice', 0, 100, '🌱'),
            (2, 'Explorer', 100, 250, '🧭'),
            (3, 'Learner', 350, 500, '📚'),
            (4, 'Practitioner', 850, 1000, '⚡'),
            (5, 'Scholar', 1850, 2000, '🎓'),
            (6, 'Expert', 3850, 3000, '💎'),
            (7, 'Master', 6850, 5000, '🏆'),
            (8, 'Grandmaster', 11850, 10000, '👑'),
        ]
    
    def _build_thresholds_dict(self):
        """Build internal lookup dictionary for fast level calculation."""
        self._thresholds_dict = {level_id: (level_name, xp_threshold, xp_to_next, badge_icon) 
                                for level_id, level_name, xp_threshold, xp_to_next, badge_icon in self.thresholds}
    
    def get_level_from_xp(self, total_xp: int) -> int:
        """Calculate level based on total XP.
        
        Args:
            total_xp: Total experience points
            
        Returns:
            Level ID (1-8)
        """
        # Find the highest level where xp_threshold <= total_xp
        level = 1  # Default to level 1
        for level_id, _, xp_threshold, _, _ in self.thresholds:
            if xp_threshold <= total_xp:
                level = level_id
            else:
                break
        return level
    
    def get_level_info(self, level_id: int) -> Optional[Tuple]:
        """Get level information by level ID.
        
        Args:
            level_id: Level identifier
            
        Returns:
            Tuple of (level_name, xp_threshold, xp_to_next, badge_icon) or None
        """
        return self._thresholds_dict.get(level_id)
    
    def get_xp_for_level(self, level_id: int) -> int:
        """Get the XP threshold for a given level.
        
        Args:
            level_id: Level identifier
            
        Returns:
            XP threshold for the level
        """
        info = self._thresholds_dict.get(level_id)
        if info:
            return info[1]  # xp_threshold
        return 0
    
    def get_xp_to_next(self, level_id: int) -> int:
        """Get XP needed to reach next level.
        
        Args:
            level_id: Current level identifier
            
        Returns:
            XP needed to reach next level
        """
        info = self._thresholds_dict.get(level_id)
        if info:
            return info[2]  # xp_to_next
        return 0

# ============================================================================
# Gamification Engine
# ============================================================================

class GamificationEngine:
    """Main engine for processing user events and updating gamification state."""
    
    def __init__(self, dsn: str):
        """Initialize the gamification engine.
        
        Args:
            dsn: Database connection string
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self.points_rules = PointsRules()
        self.level_thresholds = LevelThresholds()
        self._event_type_mapping = {
            # Map interaction event types to engagement points source types
            "course_start": "course_completion",
            "lesson_complete": "lesson_completion", 
            "question_submit": None,  # Special handling needed - check metadata
            "question_answer": None,  # Special handling needed - check metadata
            "streak_milestone": "streak_bonus",
            "daily_login": "daily_login",
            "peer_help": "peer_help",
            "content_contribution": "content_contribution",
            "review_completion": "review_completion",
        }
    
    async def connect(self):
        """Establish database connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
            logger.info("Database connection pool established")
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
    
    async def _ensure_processed_events_table(self):
        """Ensure the processed events tracking table exists."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_user_events (
                    user_id BIGINT NOT NULL,
                    event_id BIGINT NOT NULL,
                    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (user_id, event_id)
                )
            """)
            logger.debug("Ensured processed_user_events table exists")
    
    async def _get_unprocessed_events(self, user_id: int, since_timestamp: float) -> List[asyncpg.Record]:
        """Fetch unprocessed interaction events for a user since a timestamp.
        
        Args:
            user_id: User identifier
            since_timestamp: Unix timestamp to fetch events after
            
        Returns:
            List of unprocessed event records
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.pool.acquire() as conn:
            # Join with processed_user_events to find unprocessed events
            rows = await conn.fetch("""
                SELECT uie.id AS event_id, uie.event_type, uie.event_category, 
                       uie.metadata, uie.created_at
                FROM user_interaction_events uie
                LEFT JOIN processed_user_events pue 
                    ON uie.id = pue.event_id AND uie.user_id = pue.user_id
                WHERE uie.user_id = $1 
                  AND uie.created_at >= to_timestamp($2)
                  AND pue.event_id IS NULL
                ORDER BY uie.created_at ASC
            """, user_id, since_timestamp)
            return rows
    
    async def _determine_source_type_and_points(self, event_type: str, metadata: dict) -> Tuple[Optional[str], int]:
        """Determine the engagement points source type and points for an interaction event.
        
        Args:
            event_type: Interaction event type
            metadata: Event metadata JSONB
            
        Returns:
            Tuple of (source_type, points) where source_type may be None for events that don't award points
        """
        # Handle special cases first
        if event_type in ["question_submit", "question_answer"]:
            # Check if the answer was correct
            is_correct = metadata.get("correct", False)
            if is_correct:
                source_type = "question_answer_correct"
            else:
                source_type = "question_answer_incorrect"
            points = self.points_rules.get_points(source_type)
            return source_type, points
        
        # Handle regular mapping
        source_type = self._event_type_mapping.get(event_type)
        if source_type is None:
            logger.warning(f"No mapping found for event type: {event_type}")
            return None, 0
            
        points = self.points_rules.get_points(source_type)
        return source_type, points
    
    async def _award_points(self, conn: asyncpg.Connection, user_id: int, points: int, 
                           source_type: str, source_id: Optional[int] = None,
                           source_metadata: Optional[dict] = None, 
                           description: Optional[str] = None) -> int:
        """Award engagement points to a user using the database function.
        
        Args:
            conn: Database connection
            user_id: User identifier
            points: Points to award (can be negative)
            source_type: Source type for the points
            source_id: Optional source ID
            source_metadata: Optional source metadata
            description: Optional description
            
        Returns:
            The ID of the created engagement points record
        """
        if points == 0:
            logger.debug(f"Skipping zero points award for user {user_id}")
            return 0
            
        # Use the existing database function
        point_id = await conn.fetchval("""
            SELECT award_engagement_points($1, $2, $3, $4, $5, $6)
        """, user_id, points, source_type, source_id, 
             json.dumps(source_metadata) if source_metadata else '{}', 
             description)
        return point_id
    
    async def _mark_event_as_processed(self, conn: asyncpg.Connection, user_id: int, event_id: int):
        """Mark an interaction event as processed.
        
        Args:
            conn: Database connection
            user_id: User identifier
            event_id: Event identifier
        """
        await conn.execute("""
            INSERT INTO processed_user_events (user_id, event_id, processed_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id, event_id) DO UPDATE SET
                processed_at = NOW()
        """, user_id, event_id)
    
    async def process_user_events(self, user_id: int, since_timestamp: float) -> dict:
        """Process new interaction events for a user and update gamification state.
        
        Args:
            user_id: User identifier
            since_timestamp: Unix timestamp to process events after
            
        Returns:
            Dictionary with processing results
        """
        if not self.pool:
            await self.connect()
        
        await self._ensure_processed_events_table()
        
        # Fetch unprocessed events
        events = await self._get_unprocessed_events(user_id, since_timestamp)
        if not events:
            logger.info(f"No unprocessed events found for user {user_id} since {since_timestamp}")
            return {
                "user_id": user_id,
                "events_processed": 0,
                "points_awarded": 0,
                "level_change": 0,
                "events": []
            }
        
        logger.info(f"Processing {len(events)} unprocessed events for user {user_id}")
        
        # Process events in a single transaction
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                total_points = 0
                processed_events = []
                
                # Get current user state before processing
                user_before = await conn.fetchrow("""
                    SELECT total_xp, current_level FROM users WHERE id = $1
                """, user_id)
                
                if not user_before:
                    raise ValueError(f"User {user_id} not found")
                
                old_level = user_before['current_level']
                old_xp = user_before['total_xp']
                
                for event in events:
                    event_id = event['event_id']
                    event_type = event['event_type']
                    metadata = event['metadata'] or {}
                    
                    # Determine source type and points
                    source_type, points = await self._determine_source_type_and_points(event_type, metadata)
                    
                    if points == 0:
                        logger.debug(f"Event {event_id} ({event_type}) awards 0 points, skipping")
                        # Still mark as processed to avoid reprocessing
                        await self._mark_event_as_processed(conn, user_id, event_id)
                        processed_events.append({
                            "event_id": event_id,
                            "event_type": event_type,
                            "points": 0,
                            "source_type": source_type,
                            "skipped": True
                        })
                        continue
                    
                    # Award points
                    point_id = await self._award_points(
                        conn, user_id, points, source_type,
                        source_metadata=metadata,
                        description=f"Points from {event_type} event"
                    )
                    
                    # Mark event as processed
                    await self._mark_event_as_processed(conn, user_id, event_id)
                    
                    total_points += points
                    processed_events.append({
                        "event_id": event_id,
                        "event_type": event_type,
                        "points": points,
                        "source_type": source_type,
                        "point_id": point_id,
                        "skipped": False
                    })
                    
                    logger.debug(f"Awarded {points} points for event {event_id} ({event_type})")
                
                # Get updated user state after processing
                user_after = await conn.fetchrow("""
                    SELECT total_xp, current_level FROM users WHERE id = $1
                """, user_id)
                
                new_level = user_after['current_level']
                new_xp = user_after['total_xp']
                level_change = new_level - old_level
                
                logger.info(f"User {user_id}: {len(events)} events processed, "
                           f"{total_points} points awarded, level changed from {old_level} to {new_level}")
                
                return {
                    "user_id": user_id,
                    "events_processed": len(events),
                    "points_awarded": total_points,
                    "level_change": level_change,
                    "old_xp": old_xp,
                    "new_xp": new_xp,
                    "old_level": old_level,
                    "new_level": new_level,
                    "events": processed_events
                }

# ============================================================================
# Standalone Function for External Use
# ============================================================================

async def process_user_events(user_id: int, since_timestamp: float, dsn: Optional[str] = None) -> dict:
    """Standalone function to process user events.
    
    Args:
        user_id: User identifier
        since_timestamp: Unix timestamp to process events after
        dsn: Database connection string (optional, uses DATABASE_URL env var if not provided)
        
    Returns:
        Dictionary with processing results
    """
    if dsn is None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise ValueError("DATABASE_URL environment variable not set and no dsn provided")
    
    engine = GamificationEngine(dsn)
    try:
        await engine.connect()
        result = await engine.process_user_events(user_id, since_timestamp)
        return result
    finally:
        await engine.close()

# ============================================================================
# Initialization Helper
# ============================================================================

async def initialize_gamification_engine(dsn: str) -> GamificationEngine:
    """Initialize and return a configured gamification engine.
    
    Args:
        dsn: Database connection string
        
    Returns:
        Initialized GamificationEngine instance
    """
    engine = GamificationEngine(dsn)
    await engine.connect()
    await engine._ensure_processed_events_table()
    return engine

if __name__ == "__main__":
    # For testing or direct execution
    import asyncio
    import sys
    
    async def main():
        if len(sys.argv) < 3:
            print("Usage: python -m gamification.engine <user_id> <since_timestamp>")
            sys.exit(1)
        
        user_id = int(sys.argv[1])
        since_timestamp = float(sys.argv[2])
        dsn = os.getenv("DATABASE_URL")
        
        if not dsn:
            print("ERROR: DATABASE_URL environment variable not set")
            sys.exit(1)
        
        result = await process_user_events(user_id, since_timestamp, dsn)
        print(f"Processing result: {result}")
    
    asyncio.run(main())