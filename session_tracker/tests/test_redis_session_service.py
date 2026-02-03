import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def reset_singleton():
    from session_tracker.services.redis_session_service import RedisSessionService
    RedisSessionService._redis = None
    RedisSessionService._instance = None
    yield
    RedisSessionService._redis = None
    RedisSessionService._instance = None


@pytest.fixture
def mock_redis():
    mock = MagicMock()

    pipeline_mock = MagicMock()
    pipeline_mock.rpush = MagicMock(return_value=pipeline_mock)
    pipeline_mock.expire = MagicMock(return_value=pipeline_mock)
    pipeline_mock.hset = MagicMock(return_value=pipeline_mock)
    pipeline_mock.execute = AsyncMock(return_value=[1, True, True])

    mock.pipeline = MagicMock(return_value=pipeline_mock)
    mock.lrange = AsyncMock(return_value=[])
    mock.llen = AsyncMock(return_value=0)
    mock.hgetall = AsyncMock(return_value={})
    mock.delete = AsyncMock()
    mock.exists = AsyncMock(return_value=0)
    mock.ttl = AsyncMock(return_value=-1)
    return mock


@pytest.fixture
def service_with_mock(mock_redis):
    from session_tracker.services.redis_session_service import RedisSessionService
    RedisSessionService._redis = mock_redis
    return RedisSessionService(), mock_redis


@pytest.mark.asyncio
class TestRedisSessionService:
    async def test_append_events(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[1, 2, True, True])

        events = [{'type': 'click', 'timestamp': 1234567890}]
        result = await service.append_events('session-123', events)

        assert result == 2
        mock_redis.pipeline.assert_called()

    async def test_append_multiple_events(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[1, 2, 3, True, True])

        events = [
            {'type': 'click', 'timestamp': 1},
            {'type': 'scroll', 'timestamp': 2},
            {'type': 'input', 'timestamp': 3},
        ]
        await service.append_events('session-123', events)

        pipeline = mock_redis.pipeline.return_value
        assert pipeline.rpush.call_count == 3

    async def test_get_events(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.lrange = AsyncMock(return_value=[
            '{"type": "click", "timestamp": 1}',
            '{"type": "scroll", "timestamp": 2}',
        ])

        events = await service.get_events('session-123')

        assert len(events) == 2
        assert events[0]['type'] == 'click'
        assert events[1]['type'] == 'scroll'
        mock_redis.lrange.assert_called_once_with('session:session-123:events', 0, -1)

    async def test_get_events_empty(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.lrange = AsyncMock(return_value=[])

        events = await service.get_events('session-123')

        assert events == []

    async def test_get_events_count(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.llen = AsyncMock(return_value=42)

        count = await service.get_events_count('session-123')

        assert count == 42
        mock_redis.llen.assert_called_once_with('session:session-123:events')

    async def test_set_metadata(self, service_with_mock):
        service, mock_redis = service_with_mock

        metadata = {'site_id': 'site-abc', 'user_id': 'user-xyz'}
        await service.set_metadata('session-123', metadata)

        pipeline = mock_redis.pipeline.return_value
        pipeline.hset.assert_called_once()
        pipeline.expire.assert_called()

    async def test_get_metadata(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.hgetall = AsyncMock(return_value={
            'site_id': '"site-abc"',
            'user_id': 'user-xyz',
        })

        metadata = await service.get_metadata('session-123')

        assert metadata['site_id'] == 'site-abc'
        assert metadata['user_id'] == 'user-xyz'

    async def test_get_metadata_empty(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.hgetall = AsyncMock(return_value={})

        metadata = await service.get_metadata('session-123')

        assert metadata == {}

    async def test_delete_session(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.delete = AsyncMock()

        await service.delete_session('session-123')

        mock_redis.delete.assert_called_once_with(
            'session:session-123:events',
            'session:session-123:meta'
        )

    async def test_exists_true(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.exists = AsyncMock(return_value=1)

        result = await service.exists('session-123')

        assert result is True

    async def test_exists_false(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.exists = AsyncMock(return_value=0)

        result = await service.exists('session-123')

        assert result is False

    async def test_set_ttl(self, service_with_mock):
        service, mock_redis = service_with_mock

        await service.set_ttl('session-123', 3600)

        pipeline = mock_redis.pipeline.return_value
        assert pipeline.expire.call_count == 2

    async def test_get_ttl(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.ttl = AsyncMock(return_value=7200)

        ttl = await service.get_ttl('session-123')

        assert ttl == 7200
        mock_redis.ttl.assert_called_once_with('session:session-123:events')

    async def test_get_ttl_no_expiry(self, service_with_mock):
        service, mock_redis = service_with_mock
        mock_redis.ttl = AsyncMock(return_value=-1)

        ttl = await service.get_ttl('session-123')

        assert ttl == -1

    async def test_get_all_session_ids(self, service_with_mock):
        service, mock_redis = service_with_mock

        async def mock_scan_iter(*args, **kwargs):
            for key in ['session:abc:events', 'session:def:events', 'session:ghi:events']:
                yield key

        mock_redis.scan_iter = mock_scan_iter

        session_ids = await service.get_all_session_ids()

        assert len(session_ids) == 3
        assert 'abc' in session_ids
        assert 'def' in session_ids
        assert 'ghi' in session_ids

    async def test_get_all_session_ids_empty(self, service_with_mock):
        service, mock_redis = service_with_mock

        async def mock_scan_iter(*args, **kwargs):
            return
            yield

        mock_redis.scan_iter = mock_scan_iter

        session_ids = await service.get_all_session_ids()

        assert session_ids == []

    async def test_key_format_events(self, service_with_mock):
        service, _ = service_with_mock

        key = service._events_key('test-session')
        assert key == 'session:test-session:events'

    async def test_key_format_meta(self, service_with_mock):
        service, _ = service_with_mock

        key = service._meta_key('test-session')
        assert key == 'session:test-session:meta'

    async def test_refresh_ttl(self, service_with_mock):
        service, mock_redis = service_with_mock

        await service.refresh_ttl('session-123')

        pipeline = mock_redis.pipeline.return_value
        assert pipeline.expire.call_count == 2

    async def test_events_serialization(self, service_with_mock):
        service, mock_redis = service_with_mock
        complex_event = {
            'type': 'mutation',
            'data': {'nested': {'value': 123}},
            'timestamp': 1234567890
        }
        mock_redis.lrange = AsyncMock(return_value=[json.dumps(complex_event)])

        events = await service.get_events('session-123')

        assert events[0]['data']['nested']['value'] == 123
