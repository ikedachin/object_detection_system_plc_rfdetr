from django.core.management.base import BaseCommand

from checker.applications import plc_monitor


class Command(BaseCommand):
    help = 'Start the PLC monitor loop for checker'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting PLC monitor...'))
        plc_monitor.main()
