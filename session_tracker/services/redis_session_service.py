import json
import logging
from typing import Optional

import redis.asyncio as redis
from django.conf import settings

logger = logging.getLogger(__name__)


class RedisSessionService:
    _instance: Optional['RedisSessionService'] = None
    _redis: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_redis(cls) -> redis.Redis:
        if cls._redis is None:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            cls._redis = redis.from_url(redis_url, decode_responses=True)
        return cls._redis

    @classmethod
    async def close(cls):
        if cls._redis:
            await cls._redis.close()
            cls._redis = None

    @staticmethod
    def _events_key(session_id: str) -> str:
        return f"session:{session_id}:events"

    @staticmethod
    def _meta_key(session_id: str) -> str:
        return f"session:{session_id}:meta"

    async def append_events(self, session_id: str, events: list) -> int:
        r = await self.get_redis()
        events_key = self._events_key(session_id)
        meta_key = self._meta_key(session_id)

        pipeline = r.pipeline()
        for event in events:
            pipeline.rpush(events_key, json.dumps(event))

        ttl = getattr(settings, 'REDIS_SESSION_TTL', 86400)
        pipeline.expire(events_key, ttl)
        pipeline.expire(meta_key, ttl)

        results = await pipeline.execute()
        return results[-3] if len(results) > 2 else results[0]

    async def get_events(self, session_id: str) -> list:
        r = await self.get_redis()
        key = self._events_key(session_id)

        raw_events = await r.lrange(key, 0, -1)
        return [json.loads(e) for e in raw_events]

    async def get_events_count(self, session_id: str) -> int:
        r = await self.get_redis()
        return await r.llen(self._events_key(session_id))

    async def set_metadata(self, session_id: str, metadata: dict) -> None:
        r = await self.get_redis()
        key = self._meta_key(session_id)

        string_metadata = {k: json.dumps(v) if not isinstance(v, str) else v
                          for k, v in metadata.items()}

        pipeline = r.pipeline()
        pipeline.hset(key, mapping=string_metadata)
        pipeline.expire(key, getattr(settings, 'REDIS_SESSION_TTL', 86400))
        await pipeline.execute()

    async def get_metadata(self, session_id: str) -> dict:
        r = await self.get_redis()
        data = await r.hgetall(self._meta_key(session_id))

        result = {}
        for k, v in data.items():
            try:
                result[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                result[k] = v
        return result

    async def delete_session(self, session_id: str) -> None:
        r = await self.get_redis()
        await r.delete(self._events_key(session_id), self._meta_key(session_id))

    async def exists(self, session_id: str) -> bool:
        r = await self.get_redis()
        return await r.exists(self._events_key(session_id)) > 0

    async def set_ttl(self, session_id: str, ttl_seconds: int) -> None:
        r = await self.get_redis()
        pipeline = r.pipeline()
        pipeline.expire(self._events_key(session_id), ttl_seconds)
        pipeline.expire(self._meta_key(session_id), ttl_seconds)
        await pipeline.execute()

    async def refresh_ttl(self, session_id: str) -> None:
        ttl = getattr(settings, 'REDIS_SESSION_TTL', 86400)
        await self.set_ttl(session_id, ttl)

    async def get_ttl(self, session_id: str) -> int:
        r = await self.get_redis()
        return await r.ttl(self._events_key(session_id))

    async def get_all_session_ids(self) -> list[str]:
        r = await self.get_redis()
        session_ids = []
        async for key in r.scan_iter(match="session:*:events"):
            session_id = key.split(":")[1]
            session_ids.append(session_id)
        return session_ids
