import environ

from .base import *

DEBUG = True

# Initialize environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Reading .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = str(env('SECRET_KEY'))

# ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
ALLOWED_HOSTS = ['*']

# Allows testing the dev server through an ngrok tunnel. Free-tier tunnels get a
# random *.ngrok-free.app subdomain each run; reserved domains on a paid plan get
# *.ngrok.app. NGROK_DOMAIN — the same variable docker-entrypoint.sh pins the
# tunnel to — covers a custom domain that matches neither wildcard.
CSRF_TRUSTED_ORIGINS = ['https://*.ngrok-free.app', 'https://*.ngrok.app']

_ngrok_domain = env('NGROK_DOMAIN', default='')
if _ngrok_domain:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_ngrok_domain}')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}
