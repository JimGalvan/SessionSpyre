from django.urls import re_path
from .consumers import SessionConsumer, LiveStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/record-session/(?P<session_id>\w+)/$', SessionConsumer.as_asgi()),
    re_path(r'ws/live-status/$', LiveStatusConsumer.as_asgi()),
]
