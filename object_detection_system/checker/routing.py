from django.urls import path
from . import checker_consumers

urlpatterns = [
    # path('ws/checker/', checker_consumers.Checker.as_asgi(), name='checker'),
    path('checker/ws/time/', checker_consumers.CheckerServerTime.as_asgi(), name='time'),
    path('checker/ws/confirm/', checker_consumers.Confirm.as_asgi(), name='confirm'),
]