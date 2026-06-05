"""
Management command: createsuperuser_auto

Creates a Django superuser from environment variables.  Used by start.sh on
first deploy / fresh database.

Environment variables (consistent with start.sh):
    DJANGO_SUPERUSER_USERNAME   — login username
    DJANGO_SUPERUSER_PASSWORD   — login password
    DJANGO_SUPERUSER_EMAIL      — email address (optional, defaults to username@example.com)

Previously this command read SUPERUSER_NAME / SUPERUSER_PASSWORD, which did
not match the variables set by start.sh (DJANGO_SUPERUSER_USERNAME /
DJANGO_SUPERUSER_PASSWORD), so the command silently did nothing when called.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a superuser from environment variables (DJANGO_SUPERUSER_* vars)'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email    = os.environ.get(
            'DJANGO_SUPERUSER_EMAIL',
            f'{username}@example.com' if username else '',
        )

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    'DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD '
                    'must both be set. Skipping superuser creation.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' already exists — skipping.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
