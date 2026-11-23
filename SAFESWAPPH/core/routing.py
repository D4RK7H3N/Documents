from django.urls import re_path

from core.consumers import ChatConsumer, EscrowStatusConsumer

websocket_urlpatterns = [
    re_path(
        r'ws/chat/(?P<conversation_id>\d+)/$',
        ChatConsumer.as_asgi(),
    ),
    re_path(
        r'ws/escrow/(?P<trade_id>\d+)/$',
        EscrowStatusConsumer.as_asgi(),
    ),
]
