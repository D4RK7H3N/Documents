import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safeswap.settings')

django_asgi = get_asgi_application()

import core.routing as core_routing

application = ProtocolTypeRouter({
    'http': django_asgi,
    'websocket': AuthMiddlewareStack(
        URLRouter(core_routing.websocket_urlpatterns)
    ),
})
