# Session Storage Architecture: Redis + S3

## Overview

This document describes the architecture for storing rrweb session recordings using Redis for real-time buffering and Amazon S3 for long-term archival storage.

## Problem Statement

### Current Implementation

Sessions are stored directly in PostgreSQL using a `JSONField`:

```python
# models.py
class UserSession(models.Model):
    events = models.JSONField()
```

Events are appended using:

```python
# consumers.py
session.events.extend(events)
await sync_to_async(session.save)()
```

### Issues with Current Approach

| Issue | Impact |
|-------|--------|
| **Full JSON rewrite on every append** | Each batch of events rewrites the entire JSON blob. A session with 10,000 events rewrites all 10,000 on every new batch. |
| **High database load** | Frequent writes during active sessions stress PostgreSQL. |
| **Memory pressure** | Large sessions load entire event arrays into memory for replay. |
| **Storage costs** | PostgreSQL storage is expensive compared to object storage. |
| **No compression** | Raw JSON stored without compression. |

## Proposed Architecture

```
                         ┌─────────────────────────────────────┐
                         │          LIVE SESSION               │
Client (rrweb) ─────────▶│ Redis List: session:{id}:events    │───▶ Replay Viewers
   WebSocket             │ Redis Hash: session:{id}:meta      │     (real-time)
                         └──────────────┬──────────────────────┘
                                        │
                                        │ On disconnect / timeout
                                        ▼
                         ┌─────────────────────────────────────┐
                         │         ARCHIVED SESSION            │
                         │ S3: sessions/{site}/{session}.json.gz│
                         │ PostgreSQL: events_url (S3 ref)     │
                         └─────────────────────────────────────┘
```

### Components

#### 1. Redis (Live Session Buffer)

Used for active/live sessions:

- **Data Structure**: Redis List (`RPUSH` for O(1) appends)
- **Key Pattern**: `session:{session_id}:events`
- **Metadata**: Redis Hash at `session:{session_id}:meta`
- **TTL**: 24 hours (auto-cleanup for abandoned sessions)

```
session:abc123:events  →  [event1_json, event2_json, event3_json, ...]
session:abc123:meta    →  {site_id: "...", user_id: "...", created_at: "..."}
```

#### 2. Amazon S3 (Archived Sessions)

Used for completed sessions:

- **Bucket Structure**: `sessions/{site_id}/{year}/{month}/{session_id}.json.gz`
- **Compression**: Gzip (typically 70-80% size reduction for JSON)
- **Storage Class**: S3 Standard, with lifecycle policy to transition to Glacier after 90 days

#### 3. PostgreSQL (Metadata & References)

Stores session metadata and S3 references:

```python
class UserSession(models.Model):
    events = models.JSONField(null=True, blank=True)  # For small/legacy sessions
    events_url = models.URLField(null=True, blank=True)  # S3 URL for archived sessions
    events_count = models.IntegerField(default=0)  # Event count for display
    archived = models.BooleanField(default=False)  # Whether session is in S3
```

## Data Flow

### Recording Flow (Write Path)

```
1. Client connects via WebSocket
2. SessionConsumer receives events batch
3. Events appended to Redis list: RPUSH session:{id}:events
4. Last event broadcast to live viewers via Channels
5. Success response sent to client
```

### Session End Flow (Archival)

```
1. WebSocket disconnects OR 30-minute timeout
2. Background task triggered (Celery/Django-Q)
3. Fetch all events from Redis: LRANGE session:{id}:events 0 -1
4. Compress events to JSON.gz
5. Upload to S3: sessions/{site_id}/{year}/{month}/{session_id}.json.gz
6. Update PostgreSQL: set events_url, archived=True
7. Delete Redis keys: DEL session:{id}:events session:{id}:meta
```

### Replay Flow (Read Path)

```
1. User requests session replay
2. Check if session.archived:
   - If False: Load events from PostgreSQL JSONField (legacy) or Redis (live)
   - If True: Generate presigned S3 URL, fetch and decompress
3. Return events to rrweb player
```

### Live Replay Flow

```
1. User opens live session
2. Fetch existing events from Redis: LRANGE session:{id}:events 0 -1
3. Open WebSocket to LiveSessionConsumer
4. Receive new events in real-time via Channels
5. Append to rrweb player
```

## Configuration

### Environment Variables

```bash
# Redis (already configured for Channels)
REDIS_URL=redis://localhost:6379/0

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=sessionspyre-sessions
AWS_S3_REGION_NAME=us-east-1

# Feature flags
USE_REDIS_SESSION_BUFFER=true
USE_S3_SESSION_ARCHIVE=true
```

### Redis Memory Management

```python
# Recommended Redis configuration
REDIS_SESSION_CONFIG = {
    'events_ttl': 86400,  # 24 hours TTL for abandoned sessions
    'max_events_per_session': 50000,  # Safety limit
    'compression_threshold': 1000,  # Compress events larger than 1KB
}
```

### S3 Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "TransitionToGlacier",
      "Status": "Enabled",
      "Filter": {"Prefix": "sessions/"},
      "Transitions": [
        {"Days": 90, "StorageClass": "GLACIER"}
      ]
    },
    {
      "ID": "DeleteOldSessions",
      "Status": "Enabled",
      "Filter": {"Prefix": "sessions/"},
      "Expiration": {"Days": 365}
    }
  ]
}
```

## Cost Analysis

### Current (PostgreSQL Only)

| Sessions/Month | Avg Events | Storage | Estimated Cost |
|---------------|------------|---------|----------------|
| 10,000 | 5,000 | ~50 GB | $50-100/mo (managed DB) |

### Proposed (Redis + S3)

| Component | Usage | Estimated Cost |
|-----------|-------|----------------|
| Redis (ElastiCache) | 1 GB cache | ~$15/mo |
| S3 Standard | 50 GB | ~$1.15/mo |
| S3 Glacier (after 90d) | 150 GB | ~$0.60/mo |
| **Total** | | **~$17/mo** |

## Security Considerations

1. **S3 Bucket Policy**: Private bucket, access only via presigned URLs
2. **Presigned URL Expiry**: 1 hour expiry for replay URLs
3. **Redis Authentication**: Use Redis AUTH with strong password
4. **Encryption**: S3 server-side encryption (SSE-S3 or SSE-KMS)

## Rollback Strategy

The implementation is designed for gradual rollout:

1. **Phase 1**: Redis buffering with PostgreSQL fallback
2. **Phase 2**: S3 archival with PostgreSQL as backup
3. **Rollback**: Set `USE_REDIS_SESSION_BUFFER=false` to revert to direct PostgreSQL writes

## References

- [rrweb documentation](https://github.com/rrweb-io/rrweb)
- [Django Channels](https://channels.readthedocs.io/)
- [Redis Lists](https://redis.io/docs/data-types/lists/)
- [boto3 S3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
