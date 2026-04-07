from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Create a superuser from environment variables'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = os.getenv('SUPERUSER_NAME')
        password = os.getenv('SUPERUSER_PASSWORD')
        email = os.getenv('SUPERUSER_EMAIL', f'{username}@example.com')

        if username and password:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
            else:
                self.stdout.write(f"Superuser '{username}' already exists.")
        else:
            self.stdout.write("SUPERUSER_NAME and SUPERUSER_PASSWORD env vars are required.")
