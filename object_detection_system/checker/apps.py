from django.apps import AppConfig
import os
import sys


class CheckerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'checker'

    def ready(self):
        if "runserver" not in sys.argv:
            return
        if os.environ.get("OBJECT_DETECTION_SYSTEM_DISABLE_PLC_MONITOR") == "1":
            return
        if os.environ.get("RUN_MAIN") != "true" and "--noreload" not in sys.argv:
            return

        from checker.applications.plc_monitor import start_background_monitor

        start_background_monitor()
