import gzip
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class S3SessionService:
    _instance: Optional['S3SessionService'] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
            )
        return cls._client

    @staticmethod
    def get_s3_key(site_id: str, session_id: str) -> str:
        now = datetime.now(timezone.utc)
        prefix = getattr(settings, 'S3_SESSION_PREFIX', 'sessions')
        return f"{prefix}/{site_id}/{now.year}/{now.month:02d}/{session_id}.json.gz"

    @property
    def bucket_name(self) -> str:
        return getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')

    def upload_session(self, session_id: str, site_id: str, events: list) -> str:
        client = self.get_client()
        s3_key = self.get_s3_key(site_id, session_id)

        json_data = json.dumps(events)
        compressed = gzip.compress(json_data.encode('utf-8'))

        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed,
                ContentType='application/gzip',
                ContentEncoding='gzip',
                Metadata={
                    'session_id': session_id,
                    'site_id': site_id,
                    'events_count': str(len(events))
                }
            )
            logger.info(f"Uploaded session {session_id} to S3: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload session {session_id} to S3: {e}")
            raise

    def download_session(self, s3_key: str) -> list:
        client = self.get_client()

        try:
            response = client.get_object(Bucket=self.bucket_name, Key=s3_key)
            compressed = response['Body'].read()
            json_data = gzip.decompress(compressed).decode('utf-8')
            return json.loads(json_data)
        except ClientError as e:
            logger.error(f"Failed to download session from S3 {s3_key}: {e}")
            raise

    def generate_presigned_url(self, s3_key: str, expiry: int = 3600) -> str:
        client = self.get_client()

        try:
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiry
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise

    def delete_session(self, s3_key: str) -> None:
        client = self.get_client()

        try:
            client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted session from S3: {s3_key}")
        except ClientError as e:
            logger.error(f"Failed to delete session from S3 {s3_key}: {e}")
            raise

    def session_exists(self, s3_key: str) -> bool:
        client = self.get_client()

        try:
            client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
