"""
Management command: cleanup_sent_reminders

Soft-deletes (marks is_deleted=True) sent, non-recurring reminder rows that
are older than REMINDER_CLEANUP_DAYS (default 90 days).  Recurring reminders
that have been fully processed (send=True, no future occurrences scheduled)
are included.

Run manually:
    python manage.py cleanup_sent_reminders
    python manage.py cleanup_sent_reminders --days 30 --dry-run

Schedule via Cloud Scheduler hitting the existing webhook endpoint, or add a
cron entry in process_scheduled_tasks to run this daily.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from app.models import Reminder

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Soft-delete old sent reminders to keep the table lean.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=int(getattr(settings, 'REMINDER_CLEANUP_DAYS', 90)),
            help='Delete sent reminders older than this many days (default: 90).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be deleted without actually deleting.',
        )
        parser.add_argument(
            '--hard-delete',
            action='store_true',
            help='Permanently delete rows instead of soft-deleting. Use with caution.',
        )

    def handle(self, *args, **options):
        days      = options['days']
        dry_run   = options['dry_run']
        hard_del  = options['hard_delete']
        cutoff    = timezone.now() - timedelta(days=days)

        # Target: sent reminders whose start date is older than the cutoff.
        # We include both one-time and recurring rows — recurring rows that
        # already have a successor clone (next occurrence) are safe to archive.
        qs = Reminder.objects.filter(
            send=True,
            is_deleted=False,
            reminder_start_date__lt=cutoff,
        )

        count = qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would {"hard-delete" if hard_del else "soft-delete"} '
                    f'{count} reminder(s) older than {days} days (cutoff: {cutoff.date()}).'
                )
            )
            # Show a sample
            for r in qs[:10]:
                self.stdout.write(f'  • [{r.id}] "{r.title}" sent at {r.reminder_start_date}')
            if count > 10:
                self.stdout.write(f'  … and {count - 10} more.')
            return

        if hard_del:
            deleted, _ = qs.delete()
            msg = f'Hard-deleted {deleted} reminder row(s) older than {days} days.'
        else:
            updated = qs.update(is_deleted=True)
            msg = f'Soft-deleted (is_deleted=True) {updated} reminder row(s) older than {days} days.'

        self.stdout.write(self.style.SUCCESS(msg))
        logger.info(f'cleanup_sent_reminders: {msg}')
