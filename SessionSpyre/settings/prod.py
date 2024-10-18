import os

import dj_database_url

DEBUG = False

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv('REDIS_URL')],  # Use the Redis URL from Railway
        },
    },
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv('SECRET_KEY'))

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}

CSRF_TRUSTED_ORIGINS = [
    'https://sessionspyre-production.up.railway.app'
]

SCRIPT_URL = 'https://sessionspyre-clientjs.pages.dev/record.js'