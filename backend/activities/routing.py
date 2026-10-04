from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/gravity/$', consumers.GravityMapConsumer.as_asgi()),
    re_path(r'^ws/gravity/session/(?P<session_id>[0-9a-f-]+)/$', consumers.GravitySessionConsumer.as_asgi()),
]
