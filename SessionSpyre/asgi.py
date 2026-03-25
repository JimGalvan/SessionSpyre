import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

# Use DJANGO_ENV environment variable to determine which settings to use
django_env = os.environ.get('DJANGO_ENV', 'prod')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'SessionSpyre.settings.{django_env}')

django.setup()

from session_tracker.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
