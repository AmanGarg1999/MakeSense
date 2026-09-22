"""
Unit tests for the gamification engine.
Tests PointsRules, LevelThresholds, and GamificationEngine classes.
"""

import pytest
import asyncio
import asyncpg
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the gamification directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from gamification.engine import (
    PointsRules, 
    LevelThresholds, 
    GamificationEngine,
    process_user_events,
    load_points_rules
)

# ============================================================================
# PointsRules Tests
# ============================================================================

def test_points_rules_default_loading():
    """Test that PointsRules loads default rules when no file is present."""
    rules = PointsRules()
    
    # Test some known default values
    assert rules.get_points("course_completion") == 100
    assert rules.get_points("lesson_completion") == 20
    assert rules.get_points("question_answer_correct") == 10
    assert rules.get_points("question_answer_incorrect") == 5
    assert rules.get_points("streak_bonus") == 50
    assert rules.get_points("unknown_event") == 0

def test_points_rules_custom_rules():
    """Test PointsRules with custom rules."""
    custom_rules = {
        "test_event": 15,
        "another_event": 30
    }
    rules = PointsRules(custom_rules)
    
    assert rules.get_points("test_event") == 15
    assert rules.get_points("another_event") == 30
    assert rules.get_points("unknown_event") == 0

def test_points_rules_add_remove():
    """Test adding and removing points rules."""
    rules = PointsRules()
    
    # Add a new rule
    rules.add_rule("new_event", 25)
    assert rules.get_points("new_event") == 25
    
    # Update existing rule
    rules.add_rule("course_completion", 150)
    assert rules.get_points("course_completion") == 150
    
    # Remove a rule
    rules.remove_rule("lesson_completion")
    assert rules.get_points("lesson_completion") == 0

def test_load_points_rules_function():
    """Test the load_points_rules function."""
    # Test with non-existent file (should return defaults)
    rules = load_points_rules("non_existent_file.yaml")
    assert rules.get_points("course_completion") == 100

# ============================================================================
# LevelThresholds Tests
# ============================================================================

def test_level_thresholds_defaults():
    """Test LevelThresholds with default values."""
    thresholds = LevelThresholds()
    
    # Test level calculation from XP
    assert thresholds.get_level_from_xp(0) == 1
    assert thresholds.get_level_from_xp(50) == 1
    assert thresholds.get_level_from_xp(100) == 2
    assert thresholds.get_level_from_xp(200) == 2
    assert thresholds.get_level_from_xp(350) == 3
    assert thresholds.get_level_from_xp(500) == 3
    assert thresholds.get_level_from_xp(850) == 4
    assert thresholds.get_level_from_xp(1000) == 4
    assert thresholds.get_level_from_xp(1850) == 5
    assert thresholds.get_level_from_xp(2000) == 5
    assert thresholds.get_level_from_xp(3850) == 6
    assert thresholds.get_level_from_xp(3000) == 5  # Level 5 (Scholar) threshold is 1850, level 6 is 3850
    assert thresholds.get_level_from_xp(6850) == 7
    assert thresholds.get_level_from_xp(5000) == 6
    assert thresholds.get_level_from_xp(11850) == 8
    assert thresholds.get_level_from_xp(15000) == 8

def test_level_thresholds_info():
    """Test getting level information."""
    thresholds = LevelThresholds()
    
    # Test level 1 info
    info = thresholds.get_level_info(1)
    assert info is not None
    level_name, xp_threshold, xp_to_next, badge_icon = info
    assert level_name == 'Novice'
    assert xp_threshold == 0
    assert xp_to_next == 100
    assert badge_icon == '🌱'
    
    # Test level 5 info
    info = thresholds.get_level_info(5)
    assert info is not None
    level_name, xp_threshold, xp_to_next, badge_icon = info
    assert level_name == 'Scholar'
    assert xp_threshold == 1850
    assert xp_to_next == 2000
    assert badge_icon == '🎓'
    
    # Test invalid level
    assert thresholds.get_level_info(0) is None
    assert thresholds.get_level_info(9) is None

def test_level_thresholds_xp_methods():
    """Test XP-related methods."""
    thresholds = LevelThresholds()
    
    # Test XP for level
    assert thresholds.get_xp_for_level(1) == 0
    assert thresholds.get_xp_for_level(2) == 100
    assert thresholds.get_xp_for_level(5) == 1850
    assert thresholds.get_xp_for_level(8) == 11850
    
    # Test XP to next level
    assert thresholds.get_xp_to_next(1) == 100
    assert thresholds.get_xp_to_next(2) == 250
    assert thresholds.get_xp_to_next(5) == 2000
    assert thresholds.get_xp_to_next(8) == 10000  # Max level still has xp_to_next defined

def test_level_thresholds_custom():
    """Test LevelThresholds with custom thresholds."""
    custom_thresholds = [
        (1, 'Beginner', 0, 50, '🌱'),
        (2, 'Intermediate', 50, 150, '🚀'),
        (3, 'Expert', 200, 300, '💫')
    ]
    thresholds = LevelThresholds(custom_thresholds)
    
    assert thresholds.get_level_from_xp(0) == 1
    assert thresholds.get_level_from_xp(25) == 1
    assert thresholds.get_level_from_xp(50) == 2
    assert thresholds.get_level_from_xp(100) == 2
    assert thresholds.get_level_from_xp(200) == 3
    assert thresholds.get_level_from_xp(250) == 3
    assert thresholds.get_level_from_xp(500) == 3

# ============================================================================
# GamificationEngine Tests
# ============================================================================

@pytest.fixture
def mock_dsn():
    """Mock DSN for testing."""
    return "postgresql://test:test@localhost/test"

@pytest.fixture
def mock_pool():
    """Mock connection pool."""
    return AsyncMock(spec=asyncpg.Pool)

@pytest.fixture
def mock_connection():
    """Mock database connection."""
    return AsyncMock(spec=asyncpg.Connection)

@pytest.mark.asyncio
async def test_gamification_engine_init(mock_dsn):
    """Test GamificationEngine initialization."""
    engine = GamificationEngine(mock_dsn)
    assert engine.dsn == mock_dsn
    assert engine.pool is None
    assert isinstance(engine.points_rules, PointsRules)
    assert isinstance(engine.level_thresholds, LevelThresholds)

@pytest.mark.asyncio
async def test_gamification_engine_connect_close(mock_dsn, mock_pool):
    """Test connecting and closing the database pool."""
    engine = GamificationEngine(mock_dsn)
    
    with patch('asyncpg.create_pool', return_value=mock_pool):
        await engine.connect()
        assert engine.pool == mock_pool
    
    await engine.close()
    mock_pool.close.assert_called_once()
    assert engine.pool is None

@pytest.mark.asyncio
async def test_ensure_processed_events_table(mock_pool, mock_connection):
    """Test ensuring the processed events table exists."""
    engine = GamificationEngine("test")
    engine.pool = mock_pool
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    
    await engine._ensure_processed_events_table()
    
    mock_connection.execute.assert_called_once()
    call_args = mock_connection.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS processed_user_events" in call_args

@pytest.mark.asyncio
async def test_get_unprocessed_events(mock_pool, mock_connection):
    """Test fetching unprocessed events."""
    engine = GamificationEngine("test")
    engine.pool = mock_pool
    
    # Mock the connection and fetch result
    mock_rows = [
        Mock(event_id=1, event_type="lesson_complete", event_category="learning", 
             metadata={"test": True}, created_at="2023-01-01 10:00:00"),
        Mock(event_id=2, event_type="question_answer", event_category="assessment", 
             metadata={"correct": True}, created_at="2023-01-01 10:05:00")
    ]
    mock_connection.fetch.return_value = mock_rows
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    
    events = await engine._get_unprocessed_events(123, 1672531200.0)  # Timestamp
    
    assert len(events) == 2
    mock_connection.fetch.assert_called_once()
    call_args = mock_connection.fetch.call_args
    assert call_args[0][1] == 123  # user_id
    assert call_args[0][2] == 1672531200.0  # since_timestamp

@pytest.mark.asyncio
async def test_determine_source_type_and_points():
    """Test determining source type and points from events."""
    engine = GamificationEngine("test")
    
    # Test regular event mapping
    source_type, points = await engine._determine_source_type_and_points(
        "lesson_complete", {}
    )
    assert source_type == "lesson_completion"
    assert points == 20
    
    # Test question answer correct
    source_type, points = await engine._determine_source_type_and_points(
        "question_answer", {"correct": True}
    )
    assert source_type == "question_answer_correct"
    assert points == 10
    
    # Test question answer incorrect
    source_type, points = await engine._determine_source_type_and_points(
        "question_answer", {"correct": False}
    )
    assert source_type == "question_answer_incorrect"
    assert points == 5
    
    # Test unknown event type
    source_type, points = await engine._determine_source_type_and_points(
        "unknown_event", {}
    )
    assert source_type is None
    assert points == 0

@pytest.mark.asyncio
async def test_award_points(mock_pool, mock_connection):
    """Test awarding points to a user."""
    engine = GamificationEngine("test")
    engine.pool = mock_pool
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_connection.fetchval.return_value = 42  # Mock point ID
    
    point_id = await engine._award_points(
        mock_connection, 123, 10, "lesson_completion", 
        source_id=456, source_metadata={"lesson_id": 789},
        description="Completed lesson"
    )
    
    assert point_id == 42
    mock_connection.fetchval.assert_called_once()
    call_args = mock_connection.fetchval.call_args
    assert call_args[0][0] == "SELECT award_engagement_points($1, $2, $3, $4, $5, $6)"
    assert call_args[0][1] == 123  # user_id
    assert call_args[0][2] == 10   # points
    assert call_args[0][3] == "lesson_completion"  # source_type

@pytest.mark.asyncio
async def test_mark_event_as_processed(mock_pool, mock_connection):
    """Test marking an event as processed."""
    engine = GamificationEngine("test")
    engine.pool = mock_pool
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    
    await engine._mark_event_as_processed(mock_connection, 123, 456)
    
    mock_connection.execute.assert_called_once()
    call_args = mock_connection.execute.call_args[0][0]
    assert "INSERT INTO processed_user_events" in call_args
    assert "ON CONFLICT (user_id, event_id) DO UPDATE" in call_args

@pytest.mark.asyncio
async def test_process_user_events_no_events(mock_pool, mock_connection):
    """Test processing when there are no unprocessed events."""
    engine = GamificationEngine("test")
    engine.pool = mock_pool
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_connection.fetch.return_value = []  # No events
    mock_connection.fetchrow.return_value = {
        'total_xp': 150,
        'current_level': 2
    }
    
    result = await engine.process_user_events(123, 1672531200.0)
    
    assert result["user_id"] == 123
    assert result["events_processed"] == 0
    assert result["points_awarded"] == 0
    assert result["level_change"] == 0
    assert result["events"] == []

@pytest.mark.asyncio
async def test_process_user_events_with_events(mock_pool, mock_connection):
    """Test processing events with point awards."""
    engine = GamificationEngine("test")
    engine.pool = mock_pool
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    
    # Mock unprocessed events
    mock_events = [
        Mock(event_id=1, event_type="lesson_complete", event_category="learning", 
             metadata={"lesson_id": 101}, created_at="2023-01-01 10:00:00"),
        Mock(event_id=2, event_type="question_answer", event_category="assessment", 
             metadata={"correct": True, "question_id": 201}, created_at="2023-01-01 10:05:00"),
        Mock(event_id=3, event_type="streak_milestone", event_category="social", 
             metadata={"streak_days": 7}, created_at="2023-01-01 10:10:00")
    ]
    mock_connection.fetch.return_value = mock_events
    
    # Mock user state before processing
    mock_connection.fetchrow.side_effect = [
        # First call: user state before processing
        {'total_xp': 80, 'current_level': 1},
        # Second call: user state after processing (within transaction)
        {'total_xp': 80 + 20 + 10 + 50, 'current_level': 2}  # 20 + 10 + 50 = 80 points
    ]
    
    # Mock the award_engagement_points function to return point IDs
    mock_connection.fetchval.side_effect = [1001, 1002, 1003]  # Point IDs
    
    result = await engine.process_user_events(123, 1672531200.0)
    
    assert result["user_id"] == 123
    assert result["events_processed"] == 3
    assert result["points_awarded"] == 80  # 20 + 10 + 50
    assert result["level_change"] == 1     # From level 1 to 2
    assert result["old_xp"] == 80
    assert result["new_xp"] == 160
    assert result["old_level"] == 1
    assert result["new_level"] == 2
    assert len(result["events"]) == 3
    
    # Check that points were awarded correctly
    event_points = [e["points"] for e in result["events"] if not e.get("skipped", False)]
    assert sum(event_points) == 80
    
    # Verify database calls
    assert mock_connection.fetchval.call_count == 3  # Three point awards
    assert mock_connection.execute.call_count >= 3   # Three marks as processed

# ============================================================================
# Standalone Function Tests
# ============================================================================

@pytest.mark.asyncio
async def test_process_user_events_standalone():
    """Test the standalone process_user_events function."""
    with patch('gamification.engine.GamificationEngine') as mock_engine_class:
        # Setup mock engine
        mock_engine = AsyncMock()
        mock_engine.process_user_events.return_value = {
            "user_id": 123,
            "events_processed": 5,
            "points_awarded": 100,
            "level_change": 0,
            "events": []
        }
        mock_engine_class.return_value = mock_engine
        
        # Mock environment variable
        with patch.dict(os.environ, {"DATABASE_URL": "test_dsn"}):
            result = await process_user_events(123, 1672531200.0)
            
            assert result["user_id"] == 123
            assert result["events_processed"] == 5
            assert result["points_awarded"] == 100
            
            # Verify engine was created and used correctly
            mock_engine_class.assert_called_once_with("test_dsn")
            mock_engine.connect.assert_called_once()
            mock_engine.process_user_events.assert_called_once_with(123, 1672531200.0)
            mock_engine.close.assert_called_once()

# ============================================================================
# Integration Test (requires actual database - skip for unit tests)
# ============================================================================

def test_integration_placeholder():
    """Placeholder for integration test that would require actual database."""
    # This would be implemented with a test database
    # For now, we just verify the module structure is correct
    assert PointsRules is not None
    assert LevelThresholds is not None
    assert GamificationEngine is not None
    assert process_user_events is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])