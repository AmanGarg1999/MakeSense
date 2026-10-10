from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
import redis
import asyncio
import time
from prometheus_client import Counter, Gauge, start_http_server
import json
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
EVENTS_RECEIVED = Counter('events_received_total', 'Total number of events received')
EVENTS_PERSISTED = Counter('events_persisted_total', 'Total number of events persisted')
QUEUE_LAG = Gauge('queue_lag_seconds', 'Current lag in seconds of the event queue')

# Allowed event types
ALLOWED_EVENT_TYPES = {
    "course_start",
    "lesson_complete",
    "question_submit",
    "question_answer",
    "streak_milestone",
    # LL-04 delivery-dial session telemetry
    "segment_play",        # metadata: track_id, skill_tag, mode, mode_class, segment_kind
    "engagement_signal",   # metadata: pause|abandon|dwell + seconds
    "retrieval_result",    # metadata: correct|partial|incorrect, mode_class
    "mode_flip",           # metadata: reason, evidence (adaptive flip rule decision)
    # LL-08 interest-routing signals
    "interest_signal",     # metadata: domain, kind (search|content|track_start|track_abandon), weight
    "search",              # metadata: query, domain (inferred interest point)
    "track_start",         # metadata: track_id, skill_tag, goal_type
    "track_abandon",       # metadata: track_id, skill_tag
}

# Redis connection (assuming Redis is running on localhost:6379)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Batch processing configuration
BATCH_SIZE = 100
BATCH_INTERVAL = 0.5  # seconds

# In-memory batch for demonstration (in production, we'd use a proper queue)
event_batch = []
last_flush_time = time.time()

class UserInteractionEvent(BaseModel):
    user_id: str = Field(..., min_length=1)
    event_type: str
    metadata: Optional[Dict[str, Any]] = None
    session_id: str = Field(..., min_length=1)

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v):
        if v not in ALLOWED_EVENT_TYPES:
            raise ValueError(f'Event type must be one of {ALLOWED_EVENT_TYPES}')
        return v

async def flush_batch():
    """Flush the current batch to Redis stream."""
    global event_batch, last_flush_time
    if not event_batch:
        return

    try:
        # Add each event to the Redis stream
        for event in event_batch:
            redis_client.xadd('user_interaction_events', {
                'user_id': event['user_id'],
                'event_type': event['event_type'],
                'metadata': json.dumps(event['metadata']) if event['metadata'] else '',
                'session_id': event['session_id'],
                'timestamp': str(time.time())
            })
        
        # Update metrics
        EVENTS_PERSISTED.inc(len(event_batch))
        logger.info(f"Flushed {len(event_batch)} events to Redis stream")
        
        # Clear batch
        event_batch = []
        last_flush_time = time.time()
        
    except Exception as e:
        logger.error(f"Failed to flush batch to Redis: {e}")
        # In a production system, we might want to retry or send to a dead-letter queue

async def batch_processor():
    """Background task to flush batches based on size or time."""
    while True:
        await asyncio.sleep(0.1)  # Check every 100ms
        current_time = time.time()
        
        # Flush if batch size reached or interval elapsed
        if len(event_batch) >= BATCH_SIZE or (current_time - last_flush_time) >= BATCH_INTERVAL:
            await flush_batch()
        
        # Update queue lag metric (approximate)
        if event_batch:
            # Lag is time since oldest event in batch
            # For simplicity, we'll use the time since last flush as an approximation
            QUEUE_LAG.set(current_time - last_flush_time)
        else:
            QUEUE_LAG.set(0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Start Prometheus metrics server on port 8001
    start_http_server(8001)
    # Start batch processor
    asyncio.create_task(batch_processor())
    logger.info("Event tracker service started")
    yield
    # Shutdown (if needed)
    logger.info("Event tracker service shutting down")

app = FastAPI(title="User Interaction Event Tracker", lifespan=lifespan)

# LL-04 delivery-dial surface (mode decisions + session telemetry + bridges)
from app.delivery_routes import router as delivery_router
app.include_router(delivery_router)

# LL-08 interest-drift / future-paths / learning-mode surface
from app.interest_routes import router as interest_router
app.include_router(interest_router)

@app.post("/api/events")
async def track_event(event: UserInteractionEvent, background_tasks: BackgroundTasks):
    """Endpoint to receive user interaction events."""
    EVENTS_RECEIVED.inc()
    
    # Add event to batch
    event_batch.append(event.dict())
    
    # Immediately flush if batch is full (background_tasks can be used for async flush)
    if len(event_batch) >= BATCH_SIZE:
        background_tasks.add_task(flush_batch)
    
    return {"status": "accepted", "event_id": f"{event.user_id}-{int(time.time())}"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {e}")

# For testing purposes, we can also expose the batch size
@app.get("/metrics/batch")
async def batch_info():
    """Return current batch size for monitoring."""
    return {
        "batch_size": len(event_batch),
        "last_flush_seconds_ago": time.time() - last_flush_time
    }