from django.core.management.base import BaseCommand
from annotator.models import Label


class Command(BaseCommand):
    help = 'Initialize default labels for RF-DETR annotation'

    def handle(self, *args, **options):
        default_labels = [
            {'name': 'person', 'color': '#FF0000'},
            {'name': 'car', 'color': '#00FF00'},
            {'name': 'bicycle', 'color': '#0000FF'},
            {'name': 'dog', 'color': '#FFFF00'},
            {'name': 'cat', 'color': '#FF00FF'},
        ]
        
        created_count = 0
        for label_data in default_labels:
            label, created = Label.objects.get_or_create(
                name=label_data['name'],
                defaults={'color': label_data['color']}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created label: {label.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Label already exists: {label.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new labels')
        )
