"""
WSGI config for SessionSpyre project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

# Use DJANGO_ENV environment variable to determine which settings to use
django_env = os.environ.get('DJANGO_ENV', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'SessionSpyre.settings.{django_env}')

application = get_wsgi_application()
application = WhiteNoise(application)
application.add_files('staticfiles', prefix='static/')
