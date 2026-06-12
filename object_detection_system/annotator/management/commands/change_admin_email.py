from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Change admin user email address'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to update')
        parser.add_argument('email', type=str, help='New email address')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        
        try:
            user = User.objects.get(username=username)
            old_email = user.email
            user.email = email
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully changed email for user "{username}" '
                    f'from "{old_email}" to "{email}"'
                )
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating email: {str(e)}')
            )
