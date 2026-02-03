import gzip
import json
import pytest
from unittest.mock import patch, MagicMock

import boto3
from moto import mock_aws

pytestmark = pytest.mark.django_db


@pytest.fixture
def aws_credentials():
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def s3_bucket(aws_credentials):
    with mock_aws():
        conn = boto3.client('s3', region_name='us-east-1')
        conn.create_bucket(Bucket='test-bucket')
        yield conn


@pytest.fixture
def s3_service(s3_bucket):
    from session_tracker.services.s3_session_service import S3SessionService
    S3SessionService._client = None
    S3SessionService._instance = None

    with patch('session_tracker.services.s3_session_service.settings') as mock_settings:
        mock_settings.AWS_ACCESS_KEY_ID = 'testing'
        mock_settings.AWS_SECRET_ACCESS_KEY = 'testing'
        mock_settings.AWS_S3_REGION_NAME = 'us-east-1'
        mock_settings.AWS_STORAGE_BUCKET_NAME = 'test-bucket'
        mock_settings.S3_SESSION_PREFIX = 'sessions'

        service = S3SessionService()
        service._client = s3_bucket
        yield service, s3_bucket


class TestS3SessionService:
    def test_get_s3_key_format(self, s3_service):
        service, _ = s3_service

        key = service.get_s3_key('site-123', 'session-456')

        assert key.startswith('sessions/site-123/')
        assert key.endswith('/session-456.json.gz')
        assert 'session-456.json.gz' in key

    def test_upload_session(self, s3_service):
        service, client = s3_service
        events = [
            {'type': 'click', 'timestamp': 1},
            {'type': 'scroll', 'timestamp': 2},
        ]

        s3_key = service.upload_session('session-123', 'site-456', events)

        assert 'session-123.json.gz' in s3_key
        response = client.get_object(Bucket='test-bucket', Key=s3_key)
        compressed = response['Body'].read()
        decompressed = gzip.decompress(compressed).decode('utf-8')
        assert json.loads(decompressed) == events

    def test_upload_session_metadata(self, s3_service):
        service, client = s3_service
        events = [{'type': 'test'}]

        s3_key = service.upload_session('session-123', 'site-456', events)

        response = client.head_object(Bucket='test-bucket', Key=s3_key)
        assert response['Metadata']['session_id'] == 'session-123'
        assert response['Metadata']['site_id'] == 'site-456'
        assert response['Metadata']['events_count'] == '1'

    def test_download_session(self, s3_service):
        service, client = s3_service
        events = [{'type': 'click'}, {'type': 'scroll'}]

        s3_key = service.upload_session('session-123', 'site-456', events)
        downloaded = service.download_session(s3_key)

        assert downloaded == events

    def test_download_session_preserves_nested_data(self, s3_service):
        service, _ = s3_service
        events = [{
            'type': 'mutation',
            'data': {'nested': {'deep': {'value': 123}}}
        }]

        s3_key = service.upload_session('session-123', 'site-456', events)
        downloaded = service.download_session(s3_key)

        assert downloaded[0]['data']['nested']['deep']['value'] == 123

    def test_generate_presigned_url(self, s3_service):
        service, _ = s3_service
        events = [{'type': 'test'}]
        s3_key = service.upload_session('session-123', 'site-456', events)

        url = service.generate_presigned_url(s3_key, expiry=3600)

        assert 'test-bucket' in url
        assert s3_key.replace('/', '%2F') in url or s3_key in url

    def test_delete_session(self, s3_service):
        service, client = s3_service
        events = [{'type': 'test'}]
        s3_key = service.upload_session('session-123', 'site-456', events)

        service.delete_session(s3_key)

        with pytest.raises(client.exceptions.NoSuchKey):
            client.get_object(Bucket='test-bucket', Key=s3_key)

    def test_session_exists_true(self, s3_service):
        service, _ = s3_service
        events = [{'type': 'test'}]
        s3_key = service.upload_session('session-123', 'site-456', events)

        assert service.session_exists(s3_key) is True

    def test_session_exists_false(self, s3_service):
        service, _ = s3_service

        assert service.session_exists('nonexistent/key.json.gz') is False

    def test_compression_reduces_size(self, s3_service):
        service, client = s3_service
        events = [{'type': 'click', 'data': 'x' * 1000} for _ in range(100)]

        s3_key = service.upload_session('session-123', 'site-456', events)

        response = client.get_object(Bucket='test-bucket', Key=s3_key)
        compressed_size = response['ContentLength']
        uncompressed_size = len(json.dumps(events).encode('utf-8'))

        assert compressed_size < uncompressed_size * 0.5

    def test_upload_empty_events(self, s3_service):
        service, _ = s3_service

        s3_key = service.upload_session('session-123', 'site-456', [])
        downloaded = service.download_session(s3_key)

        assert downloaded == []

    def test_upload_large_session(self, s3_service):
        service, _ = s3_service
        events = [{'type': f'event_{i}', 'timestamp': i} for i in range(10000)]

        s3_key = service.upload_session('session-123', 'site-456', events)
        downloaded = service.download_session(s3_key)

        assert len(downloaded) == 10000
        assert downloaded[9999]['type'] == 'event_9999'
