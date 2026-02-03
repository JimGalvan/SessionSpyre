import environ
from .base import *

import os
import dj_database_url

# Initialize environ
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    DATABASE_URL=(str, ''),
    REDIS_URL=(str, ''),
)

# Reading .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

DEBUG = env('DEBUG', default=False)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [env('REDIS_URL')],  # Use the Redis URL from environment
        },
    },
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': dj_database_url.config(default=env('DATABASE_URL'))
}

CSRF_TRUSTED_ORIGINS = [
    'https://sessionspyre-production.up.railway.app'
]

SCRIPT_URL = 'https://sessionspyre-clientjs.pages.dev/record.js'

USE_REDIS_SESSION_BUFFER = env.bool('USE_REDIS_SESSION_BUFFER', default=True)
REDIS_SESSION_TTL = env.int('REDIS_SESSION_TTL', default=86400)
REDIS_SESSION_MAX_EVENTS = env.int('REDIS_SESSION_MAX_EVENTS', default=50000)
REDIS_URL = env('REDIS_URL')

USE_S3_SESSION_ARCHIVE = env.bool('USE_S3_SESSION_ARCHIVE', default=True)
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
S3_SESSION_PREFIX = env('S3_SESSION_PREFIX', default='sessions')