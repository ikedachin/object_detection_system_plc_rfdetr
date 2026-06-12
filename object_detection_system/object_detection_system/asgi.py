"""
ASGI config for inventry_checker project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from get_imgs.routing import urlpatterns as get_imgs_urlpatterns
from checker.routing import urlpatterns as checker_urlpatterns
from training.routing import websocket_urlpatterns as training_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'object_detection_system.settings')

application = get_asgi_application()


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
            URLRouter(get_imgs_urlpatterns + checker_urlpatterns + training_urlpatterns),
    ),
})
