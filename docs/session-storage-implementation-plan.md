# Session Storage Implementation Plan

> **Status**: Planning
> **Last Updated**: 2026-02-02
> **Target Completion**: TBD

## Overview

This document tracks the implementation of Redis + S3 session storage as described in [session-storage-architecture.md](./session-storage-architecture.md).

## Implementation Phases

### Phase 1: Redis Session Buffering

Buffer live session events in Redis instead of direct PostgreSQL writes.

| Task | Status | Notes |
|------|--------|-------|
| 1.1 Create Redis session service | ⬜ Pending | New service class for Redis operations |
| 1.2 Update SessionConsumer to use Redis | ⬜ Pending | Replace `session.events.extend()` with Redis RPUSH |
| 1.3 Add flush-to-PostgreSQL on disconnect | ⬜ Pending | Batch write events when session ends |
| 1.4 Update live replay to read from Redis | ⬜ Pending | Fetch existing events from Redis for live sessions |
| 1.5 Add Redis TTL for abandoned sessions | ⬜ Pending | 24-hour expiry for cleanup |
| 1.6 Add feature flag | ⬜ Pending | `USE_REDIS_SESSION_BUFFER` toggle |
| 1.7 Write tests for Redis service | ⬜ Pending | Unit tests for Redis operations |
| 1.8 Load testing | ⬜ Pending | Compare performance vs current approach |

### Phase 2: S3 Session Archival

Archive completed sessions to S3 for cost-effective long-term storage.

| Task | Status | Notes |
|------|--------|-------|
| 2.1 Add AWS dependencies | ⬜ Pending | `boto3`, `django-storages` |
| 2.2 Create S3 session service | ⬜ Pending | Upload/download/presigned URL generation |
| 2.3 Add model fields for S3 reference | ⬜ Pending | `events_url`, `archived`, `events_count` |
| 2.4 Create archival background task | ⬜ Pending | Celery/Django-Q task for async archival |
| 2.5 Update replay view for S3 sessions | ⬜ Pending | Fetch from S3 when `archived=True` |
| 2.6 Add compression (gzip) | ⬜ Pending | Compress before S3 upload |
| 2.7 Create migration script for existing sessions | ⬜ Pending | Migrate large sessions to S3 |
| 2.8 Add S3 lifecycle policy | ⬜ Pending | Glacier transition after 90 days |
| 2.9 Write tests for S3 service | ⬜ Pending | Unit tests with moto/localstack |

### Phase 3: Optimization & Cleanup

Performance improvements and legacy cleanup.

| Task | Status | Notes |
|------|--------|-------|
| 3.1 Add streaming replay for large sessions | ⬜ Pending | Stream events instead of loading all at once |
| 3.2 Add session size limits | ⬜ Pending | Max 50,000 events per session |
| 3.3 Add monitoring/metrics | ⬜ Pending | Track Redis memory, S3 uploads, latency |
| 3.4 Remove legacy JSONField dependency | ⬜ Pending | After migration complete |
| 3.5 Documentation updates | ⬜ Pending | Update CLAUDE.md and README |

---

## Detailed Task Breakdown

### 1.1 Create Redis Session Service

**File**: `session_tracker/services/redis_session_service.py`

```python
# Proposed interface
class RedisSessionService:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def append_events(self, session_id: str, events: list) -> int:
        """Append events to Redis list. Returns new length."""
        pass

    async def get_events(self, session_id: str) -> list:
        """Get all events for a session."""
        pass

    async def get_events_count(self, session_id: str) -> int:
        """Get event count without loading all events."""
        pass

    async def set_metadata(self, session_id: str, metadata: dict) -> None:
        """Store session metadata in Redis hash."""
        pass

    async def get_metadata(self, session_id: str) -> dict:
        """Get session metadata."""
        pass

    async def delete_session(self, session_id: str) -> None:
        """Delete session data from Redis."""
        pass

    async def set_ttl(self, session_id: str, ttl_seconds: int) -> None:
        """Set TTL on session keys."""
        pass
```

**Acceptance Criteria**:
- [ ] All methods implemented with proper error handling
- [ ] Async/await compatible for use in Channels consumers
- [ ] Connection pooling configured
- [ ] Unit tests with fakeredis

---

### 1.2 Update SessionConsumer to Use Redis

**File**: `session_tracker/consumers.py`

**Current code** (lines 163-164):
```python
session.events.extend(events)
await sync_to_async(session.save)()
```

**Proposed change**:
```python
if settings.USE_REDIS_SESSION_BUFFER:
    await self.redis_service.append_events(self.session_id, events)
else:
    # Fallback to current behavior
    session.events.extend(events)
    await sync_to_async(session.save)()
```

**Acceptance Criteria**:
- [ ] Events appended to Redis in O(1) time
- [ ] Feature flag controls behavior
- [ ] Existing WebSocket protocol unchanged
- [ ] Live broadcast still works

---

### 1.3 Add Flush-to-PostgreSQL on Disconnect

**File**: `session_tracker/consumers.py` (disconnect method)

**Proposed logic**:
```python
async def disconnect(self, close_code):
    if settings.USE_REDIS_SESSION_BUFFER:
        # Fetch all events from Redis
        events = await self.redis_service.get_events(self.session_id)

        # Batch write to PostgreSQL
        session = await sync_to_async(UserSession.objects.get)(id=self.session_id)
        session.events = events
        session.live = False
        await sync_to_async(session.save)()

        # Clean up Redis
        await self.redis_service.delete_session(self.session_id)

    # Existing disconnect logic...
```

**Acceptance Criteria**:
- [ ] All events persisted to PostgreSQL on clean disconnect
- [ ] Redis keys cleaned up after flush
- [ ] Handles reconnection within timeout window
- [ ] Error handling for partial failures

---

### 2.2 Create S3 Session Service

**File**: `session_tracker/services/s3_session_service.py`

```python
# Proposed interface
class S3SessionService:
    def __init__(self, bucket_name: str):
        self.bucket = bucket_name
        self.s3_client = boto3.client('s3')

    def upload_session(self, session_id: str, site_id: str, events: list) -> str:
        """Compress and upload events to S3. Returns S3 URL."""
        pass

    def download_session(self, s3_url: str) -> list:
        """Download and decompress events from S3."""
        pass

    def generate_presigned_url(self, s3_key: str, expiry: int = 3600) -> str:
        """Generate presigned URL for direct browser access."""
        pass

    def delete_session(self, s3_url: str) -> None:
        """Delete session from S3."""
        pass
```

**Acceptance Criteria**:
- [ ] Gzip compression implemented
- [ ] Proper S3 key structure: `sessions/{site_id}/{year}/{month}/{session_id}.json.gz`
- [ ] Presigned URLs with configurable expiry
- [ ] Unit tests with moto

---

### 2.3 Add Model Fields for S3 Reference

**File**: `session_tracker/models.py`

```python
class UserSession(models.Model):
    # Existing fields...
    events = models.JSONField(null=True, blank=True)  # Make nullable

    # New fields
    events_url = models.URLField(
        null=True,
        blank=True,
        help_text="S3 URL for archived session events"
    )
    events_count = models.IntegerField(
        default=0,
        help_text="Number of events in session"
    )
    archived = models.BooleanField(
        default=False,
        help_text="Whether session events are stored in S3"
    )
```

**Migration**: `0002_add_s3_session_fields.py`

**Acceptance Criteria**:
- [ ] Migration runs without data loss
- [ ] Backward compatible with existing sessions
- [ ] `get_events_json` property updated to handle both storage types

---

## Environment Setup

### Development

```bash
# Install Redis locally or use Docker
docker run -d -p 6379:6379 redis:7-alpine

# Install LocalStack for S3 testing
docker run -d -p 4566:4566 localstack/localstack

# Install dependencies
pip install redis boto3 django-storages fakeredis moto
```

### Production (AWS)

```bash
# Required environment variables
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_STORAGE_BUCKET_NAME=sessionspyre-sessions
AWS_S3_REGION_NAME=us-east-1
REDIS_URL=redis://your-elasticache-endpoint:6379

# Feature flags
USE_REDIS_SESSION_BUFFER=true
USE_S3_SESSION_ARCHIVE=true
```

---

## Testing Strategy

### Unit Tests

| Test Suite | Coverage |
|------------|----------|
| `test_redis_session_service.py` | Redis operations with fakeredis |
| `test_s3_session_service.py` | S3 operations with moto |
| `test_session_consumer.py` | Consumer with Redis integration |

### Integration Tests

| Test | Description |
|------|-------------|
| Full recording flow | WebSocket → Redis → PostgreSQL |
| Live replay | Redis events → rrweb player |
| Archived replay | S3 → decompress → rrweb player |
| Timeout handling | 30-min timeout triggers archival |

### Load Tests

| Scenario | Target |
|----------|--------|
| Concurrent sessions | 1,000 simultaneous recordings |
| Events per second | 100 events/sec per session |
| Large session replay | 50,000 events in < 5 seconds |

---

## Rollback Plan

### Phase 1 Rollback

```bash
# Disable Redis buffering
USE_REDIS_SESSION_BUFFER=false

# Events will write directly to PostgreSQL (original behavior)
```

### Phase 2 Rollback

```bash
# Disable S3 archival
USE_S3_SESSION_ARCHIVE=false

# Sessions remain in PostgreSQL JSONField
# Run migration to copy S3 sessions back to PostgreSQL if needed
```

---

## Progress Log

| Date | Update |
|------|--------|
| 2026-02-02 | Initial planning document created |
| 2026-02-02 | Phase 1 completed - Redis session buffering |
| 2026-02-02 | Phase 2 completed - S3 session archival |

---

## Open Questions

1. **Task queue**: Use Celery or Django-Q for background archival?
2. **Redis persistence**: Enable RDB/AOF for Redis crash recovery?
3. **S3 region**: Same region as Railway deployment?
4. **Compression**: Gzip vs Zstandard for better compression ratio?

---

## References

- [Architecture Document](./session-storage-architecture.md)
- [Django Channels Redis](https://channels.readthedocs.io/en/stable/topics/channel_layers.html)
- [boto3 S3 Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html)
