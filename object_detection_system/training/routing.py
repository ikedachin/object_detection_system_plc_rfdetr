from django.urls import re_path
from .consumers import RfdetrTrainingConsumer

websocket_urlpatterns = [
    re_path(r'ws/rfdetr_training/$', RfdetrTrainingConsumer.as_asgi()),
]
