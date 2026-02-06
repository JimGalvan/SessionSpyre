# Session Storage Implementation Plan

> **Status**: Phase 1 & 2 Complete - S3 Archival Enabled
> **Last Updated**: 2026-02-05
> **Target Completion**: Phase 3 TBD

## Overview

This document tracks the implementation of Redis + S3 session storage as described in [session-storage-architecture.md](./session-storage-architecture.md).

## Implementation Phases

### Phase 1: Redis Session Buffering ✅

Buffer live session events in Redis instead of direct PostgreSQL writes.

| Task | Status | Notes |
|------|--------|-------|
| 1.1 Create Redis session service | ✅ Done | `services/redis_session_service.py` - singleton with connection pooling |
| 1.2 Update SessionConsumer to use Redis | ✅ Done | `consumers.py:199-200` - uses Redis RPUSH via service |
| 1.3 Add flush-to-PostgreSQL on disconnect | ✅ Done | `consumers.py:112-142` - `flush_redis_to_postgres()` method |
| 1.4 Update live replay to read from Redis | ✅ Done | `session_views.py:27-31` - fetches from Redis for live sessions |
| 1.5 Add Redis TTL for abandoned sessions | ✅ Done | 24-hour TTL + `flush_abandoned_sessions` management command |
| 1.6 Add feature flag | ✅ Done | `USE_REDIS_SESSION_BUFFER` in settings (enabled) |
| 1.7 Write tests for Redis service | ✅ Done | `tests/test_redis_session_service.py` - 20+ unit tests |
| 1.8 Load testing | ⬜ Pending | Compare performance vs current approach |

### Phase 2: S3 Session Archival ✅

Archive completed sessions to S3 for cost-effective long-term storage.

| Task | Status | Notes |
|------|--------|-------|
| 2.1 Add AWS dependencies | ✅ Done | `boto3` installed and configured |
| 2.2 Create S3 session service | ✅ Done | `services/s3_session_service.py` - upload/download/presigned URLs |
| 2.3 Add model fields for S3 reference | ✅ Done | `events_s3_key`, `archived`, `events_count` on UserSession |
| 2.4 Create archival background task | ✅ Done | `flush_abandoned_sessions` command handles archival |
| 2.5 Update replay view for S3 sessions | ✅ Done | `session_views.py:33-35` - fetches from S3 when archived |
| 2.6 Add compression (gzip) | ✅ Done | `s3_session_service.py:49` - gzip before upload |
| 2.7 Add S3 lifecycle policy | ✅ Done | S3 bucket created with credentials configured |
| 2.8 Write tests for S3 service | ✅ Done | `tests/test_s3_session_service.py` - uses moto |

### Phase 3: Optimization & Cleanup

Performance improvements and legacy cleanup.

| Task | Status | Notes |
|------|--------|-------|
| 3.1 Add streaming replay for large sessions | ⬜ Pending | Stream events instead of loading all at once |
| 3.2 Add session size limits | ⬜ Pending | Max 50,000 events per session |
| 3.3 Add monitoring/metrics | ⬜ Pending | Track Redis memory, S3 uploads, latency |
| 3.4 Remove legacy JSONField dependency | ⬜ Pending | After S3 archival proven stable |
| 3.5 Documentation updates | ⬜ Pending | Update CLAUDE.md and README |

---

## Detailed Task Breakdown

### 1.1 Create Redis Session Service ✅

**File**: `session_tracker/services/redis_session_service.py`

Implemented as singleton with async Redis client. Key methods:
- `append_events()` - RPUSH with pipeline for batch operations
- `get_events()` / `get_events_count()` - LRANGE / LLEN
- `set_metadata()` / `get_metadata()` - HSET / HGETALL
- `delete_session()` - cleanup both events and meta keys
- `set_ttl()` / `refresh_ttl()` / `get_ttl()` - TTL management
- `get_all_session_ids()` - SCAN for abandoned session cleanup

**Acceptance Criteria**:
- [x] All methods implemented with proper error handling
- [x] Async/await compatible for use in Channels consumers
- [x] Connection pooling via singleton pattern
- [x] Unit tests (20+ tests in `test_redis_session_service.py`)

---

### 1.2 Update SessionConsumer to Use Redis ✅

**File**: `session_tracker/consumers.py`

Redis service initialized in `__init__` when feature flag enabled:
```python
self.redis_service = RedisSessionService() if getattr(django_settings, 'USE_REDIS_SESSION_BUFFER', False) else None
```

Events appended via Redis when active (line 199-200):
```python
if self.redis_service:
    await self.redis_service.append_events(self.session_id, events)
```

**Acceptance Criteria**:
- [x] Events appended to Redis in O(1) time
- [x] Feature flag controls behavior
- [x] Existing WebSocket protocol unchanged
- [x] Live broadcast still works

---

### 1.3 Add Flush-to-PostgreSQL on Disconnect ✅

**File**: `session_tracker/consumers.py` (`flush_redis_to_postgres` method, lines 112-142)

Handles both PostgreSQL-only and S3 archival paths based on `USE_S3_SESSION_ARCHIVE` flag.

**Acceptance Criteria**:
- [x] All events persisted to PostgreSQL/S3 on clean disconnect
- [x] Redis keys cleaned up after flush
- [x] Error handling for partial failures
- [ ] Handles reconnection within timeout window (handled by TTL instead)

---

### 2.2 Create S3 Session Service ✅

**File**: `session_tracker/services/s3_session_service.py`

Implemented as singleton with boto3 client. Key methods:
- `upload_session()` - gzip compress and upload with metadata
- `download_session()` - download and decompress
- `generate_presigned_url()` - for direct browser access
- `delete_session()` - cleanup
- `session_exists()` - HEAD check

**Acceptance Criteria**:
- [x] Gzip compression implemented
- [x] Proper S3 key structure: `sessions/{site_id}/{year}/{month}/{session_id}.json.gz`
- [x] Presigned URLs with configurable expiry
- [x] Unit tests with moto (15+ tests in `test_s3_session_service.py`)

---

### 2.3 Add Model Fields for S3 Reference ✅

**File**: `session_tracker/models.py`

```python
class UserSession(models.Model):
    # ...existing fields...
    events = models.JSONField(null=True, blank=True)
    events_s3_key = models.CharField(max_length=512, null=True, blank=True)
    events_count = models.IntegerField(default=0)
    archived = models.BooleanField(default=False)
```

**Acceptance Criteria**:
- [x] Migration runs without data loss
- [x] Backward compatible with existing sessions
- [x] Replay view updated to fetch from S3 when `archived=True`

---

## Environment Setup

### Current Configuration (`base.py`)

```python
# Redis buffering (ENABLED)
USE_REDIS_SESSION_BUFFER = True
REDIS_SESSION_TTL = 86400  # 24 hours
REDIS_SESSION_MAX_EVENTS = 50000
REDIS_URL = 'redis://localhost:6379/0'

# S3 archival (ENABLED)
USE_S3_SESSION_ARCHIVE = True
AWS_ACCESS_KEY_ID = '...'       # Configured
AWS_SECRET_ACCESS_KEY = '...'   # Configured
AWS_STORAGE_BUCKET_NAME = 'test-sessionspyre'
AWS_S3_REGION_NAME = 'us-west-2'
S3_SESSION_PREFIX = 'sessions'
```

### Development

```bash
# Install Redis locally or use Docker
docker run -d -p 6379:6379 redis:7-alpine

# Run tests with moto (no real AWS needed)
pytest session_tracker/tests/test_s3_session_service.py
pytest session_tracker/tests/test_redis_session_service.py
```

### How It Works Now

Sessions are:
1. Buffered in Redis during recording
2. Compressed (gzip) and uploaded to S3 on disconnect
3. Fetched from S3 for replay when `archived=True`

---

## Testing Strategy

### Unit Tests ✅

| Test Suite | Status | Coverage |
|------------|--------|----------|
| `test_redis_session_service.py` | ✅ Done | 20+ tests with mock Redis |
| `test_s3_session_service.py` | ✅ Done | 15+ tests with moto |
| `test_session_consumer.py` | ⬜ Pending | Consumer with Redis integration |

### Integration Tests (Manual)

| Test | Status | Description |
|------|--------|-------------|
| Full recording flow | ✅ Working | WebSocket → Redis → PostgreSQL/S3 |
| Archived replay | ✅ Working | S3 → decompress → rrweb player |
| Live replay from Redis | ✅ Working | Redis events → rrweb player |
| Abandoned session flush | ✅ Working | `flush_abandoned_sessions` command |

### Load Tests ⬜

| Scenario | Target | Status |
|----------|--------|--------|
| Concurrent sessions | 1,000 simultaneous recordings | ⬜ Pending |
| Events per second | 100 events/sec per session | ⬜ Pending |
| Large session replay | 50,000 events in < 5 seconds | ⬜ Pending |

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
| 2026-02-02 | Phase 1 implemented - Redis session buffering |
| 2026-02-02 | Phase 2 implemented - S3 session archival |
| 2026-02-05 | S3 bucket created and credentials configured |
| 2026-02-05 | Status audit - verified implementation, updated task statuses |
| 2026-02-05 | Enabled `USE_S3_SESSION_ARCHIVE=True` - full system active |

---

## Remaining Work

### Phase 3 (Nice to Have)
- Load testing to validate performance improvements
- Streaming replay for very large sessions
- Session size limits
- Monitoring/metrics

---

## Resolved Questions

1. ~~**Task queue**: Use Celery or Django-Q for background archival?~~ → Using management command `flush_abandoned_sessions` (can be run via cron/scheduler)
2. ~~**Compression**: Gzip vs Zstandard?~~ → Using gzip (standard, good compression)
3. ~~**S3 bucket setup**~~ → Bucket created, credentials in settings

---

## References

- [Architecture Document](./session-storage-architecture.md)
- [Django Channels Redis](https://channels.readthedocs.io/en/stable/topics/channel_layers.html)
- [boto3 S3 Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html)
