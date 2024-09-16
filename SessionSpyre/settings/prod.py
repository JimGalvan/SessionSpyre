from .base import *
import os

DEBUG = True

# Reading .os.getenv file
# environ.Env.read_env(os.path.join(BASE_DIR, '.os.getenv'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv('SECRET_KEY'))

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', default='localhost'),
        'PORT': os.getenv('DB_PORT', default='5432'),
    }
}

CSRF_TRUSTED_ORIGINS = [
    'https://sessionspyre-production.up.railway.app'
]