from django.urls import re_path

from .consumers import SessionConsumer, LiveStatusConsumer, LiveSessionConsumer, SessionUpdatesConsumer

websocket_urlpatterns = [
    re_path(r'ws/record-session/(?P<session_id>\w+)/$', SessionConsumer.as_asgi()),
    re_path(r'ws/live-session/(?P<session_id>\w+)/$', LiveSessionConsumer.as_asgi()),
    re_path(r'ws/live-status/$', LiveStatusConsumer.as_asgi()),
    re_path(r'ws/session-updates/$', SessionUpdatesConsumer.as_asgi()),
]
