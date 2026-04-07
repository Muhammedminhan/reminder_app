from django.core.management.base import BaseCommand
from app.utils import process_scheduled_tasks, process_reminder_tasks


class Command(BaseCommand):
    help = 'Process all scheduled tasks and due reminders (with auto-start + completion workflow)'

    def handle(self, *args, **options):
        self.stdout.write('Processing scheduled tasks...')
        process_scheduled_tasks()
        self.stdout.write(self.style.SUCCESS('Scheduled tasks processed.'))
        self.stdout.write('Processing reminders...')
        stats = process_reminder_tasks()
        self.stdout.write(self.style.SUCCESS(
            f"Reminders: sent={stats.get('sent')} processed={stats.get('processed')} deactivated={stats.get('deactivated')} skipped_end_date={stats.get('skipped_end_date')}"))
