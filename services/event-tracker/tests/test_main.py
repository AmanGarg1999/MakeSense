import pytest
import asyncio
from starlette.testclient import TestClient
from unittest.mock import Mock, patch
import json
import sys
import os

# Add the parent directory of the current file (i.e., services/event-tracker) to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import main
from app.main import app, ALLOWED_EVENT_TYPES

@pytest.fixture
def client():
    """Create a test client for the app."""
    return TestClient(app)

def reset_globals():
    """Reset global state between tests."""
    main.event_batch = []
    main.last_flush_time = 0

@pytest.fixture(autouse=True)
def setup_teardown():
    reset_globals()
    yield
    reset_globals()

def test_health_endpoint(client):
    """Test the health check endpoint."""
    with patch('app.main.redis_client') as mock_redis:
        mock_redis.ping.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"] == "connected"

def test_health_endpoint_redis_down(client):
    """Test health check when Redis is down."""
    with patch('app.main.redis_client') as mock_redis:
        mock_redis.ping.side_effect = Exception("Connection failed")
        response = client.get("/health")
        assert response.status_code == 503

def test_track_event_valid(client):
    """Test tracking a valid event."""
    with patch('app.main.redis_client') as mock_redis:
        mock_redis.ping.return_value = True
        mock_redis.xadd.return_value = "12345"
        
        event_data = {
            "user_id": "user123",
            "event_type": "course_start",
            "metadata": {"source": "homepage"},
            "session_id": "session456"
        }
        
        response = client.post("/api/events", json=event_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "event_id" in data

def test_track_event_invalid_type(client):
    """Test tracking an event with invalid type."""
    event_data = {
        "user_id": "user123",
        "event_type": "invalid_event",
        "metadata": {},
        "session_id": "session456"
    }
    
    response = client.post("/api/events", json=event_data)
    assert response.status_code == 422  # Validation error

def test_track_event_missing_fields(client):
    """Test tracking an event with missing required fields."""
    event_data = {
        "user_id": "user123",
        # missing event_type
        "metadata": {},
        "session_id": "session456"
    }
    
    response = client.post("/api/events", json=event_data)
    assert response.status_code == 422

def test_allowed_event_types(client):
    """Test that all allowed event types are accepted."""
    with patch('app.main.redis_client') as mock_redis:
        mock_redis.ping.return_value = True
        mock_redis.xadd.return_value = "12345"
        
        for event_type in ALLOWED_EVENT_TYPES:
            event_data = {
                "user_id": "user123",
                "event_type": event_type,
                "metadata": {},
                "session_id": "session456"
            }
            
            response = client.post("/api/events", json=event_data)
            assert response.status_code == 200, f"Failed for event type: {event_type}"

def test_batch_flushing(client):
    """Test that events are batched and flushed correctly."""
    with patch('app.main.redis_client') as mock_redis:
        mock_redis.ping.return_value = True
        mock_redis.xadd.return_value = "12345"
        
        # Add events up to batch size
        for i in range(100):  # BATCH_SIZE is 100
            event_data = {
                "user_id": f"user{i}",
                "event_type": "lesson_complete",
                "metadata": {"index": i},
                "session_id": f"session{i}"
            }
            
            response = client.post("/api/events", json=event_data)
            assert response.status_code == 200
        
        # Verify xadd was called (batch flushed)
        assert mock_redis.xadd.call_count >= 1

@pytest.mark.asyncio
async def test_flush_batch():
    """Test the flush_batch function directly."""
    with patch('app.main.redis_client') as mock_redis:
        mock_redis.xadd.return_value = "12345"
        
        # Add some events to batch
        main.event_batch.extend([
            {
                "user_id": "user1",
                "event_type": "course_start",
                "metadata": {"test": True},
                "session_id": "session1"
            },
            {
                "user_id": "user2",
                "event_type": "question_submit",
                "metadata": {"question_id": "q1"},
                "session_id": "session2"
            }
        ])
        
        await main.flush_batch()
        
        # Verify events were added to Redis stream
        assert mock_redis.xadd.call_count == 2
        # Verify batch was cleared
        assert len(main.event_batch) == 0