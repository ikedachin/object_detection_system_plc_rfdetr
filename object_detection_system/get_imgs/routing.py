from django.urls import path
from . import get_imgs_consumers

urlpatterns = [
    # path('ws/checker/', get_imgs_consumers.Checker.as_asgi(), name='checker'),
    path('get_imgs/ws/time/', get_imgs_consumers.ServerTime.as_asgi(), name='time'),
    path('get_imgs/ws/camera/', get_imgs_consumers.CameraConsumer.as_asgi(), name='camera'),
    path('get_imgs/ws/snap/', get_imgs_consumers.Snap.as_asgi(), name='snap'),
    # 追加: ルート直下のWebSocketパスにも対応
    path('ws/camera/', get_imgs_consumers.CameraConsumer.as_asgi(), name='camera_ws_root'),
]
