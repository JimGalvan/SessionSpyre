from django.urls import re_path
from .consumers import SessionConsumer

websocket_urlpatterns = [
    re_path(r'ws/record-session/(?P<session_id>\w+)/$', SessionConsumer.as_asgi()),
]
