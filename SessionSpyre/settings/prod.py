from .base import *
import environ
import os

# Initialize environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

DEBUG = True

# Reading .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(env('SECRET_KEY'))

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

CSRF_TRUSTED_ORIGINS = [
    'https://sessionspyre-production.up.railway.app'
]