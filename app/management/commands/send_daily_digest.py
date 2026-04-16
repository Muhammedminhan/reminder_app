
from django.core.management.base import BaseCommand
from app.models import Reminder, Company, User
from app.slack import send_channel_message, send_dm_to_user
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send daily morning Slack notifications listing pending reminders'

    def handle(self, *args, **options):
        # find companies with daily digest enabled
        companies = Company.objects.filter(slack_daily_digest_enabled=True)
        if not companies.exists():
            self.stdout.write(self.style.WARNING('No companies have daily digest enabled.'))
            return

        for company in companies:
            # Get pending reminders for this company starting in the next 24 hours or already overdue
            now = timezone.now()
            next_24h = now + timedelta(days=1)
            
            pending = Reminder.objects.filter(
                company=company,
                completed=False,
                active=True,
                is_deleted=False,
                reminder_start_date__lte=next_24h
            ).order_by('reminder_start_date')

            if not pending.exists():
                logger.debug(f"No pending reminders for {company.name}")
                continue
                
            msg = f"☀️ *Morning Reminder Digest for {company.name}*\n"
            msg += f"Today is {now.strftime('%A, %b %d %Y')}\n\n"
            
            for r in pending:
                status = "🔴 OVERDUE" if r.reminder_start_date < now else "🕒 UPCOMING"
                msg += f"• *{r.title}* ({status})\n"
                msg += f"  - Due: {r.reminder_start_date.strftime('%I:%M %p')}\n"
                msg += f"  - To: {r.receiver_email}\n\n"
            
            msg += f"Check your dashboard for details: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'}"

            # Send to configured channels
            sent_count = 0
            if company.slack_digest_channels:
                for channel in company.slack_digest_channels.split(','):
                    channel = channel.strip()
                    if channel:
                        try:
                            send_channel_message(channel, msg)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send digest to channel {channel}: {e}")
            
            # Send to configured users
            if company.slack_digest_users:
                user_ids = [uid.strip() for uid in company.slack_digest_users.split(',') if uid.strip()]
                users = User.objects.filter(id__in=user_ids)
                for u in users:
                    if u.slack_user_id:
                        try:
                            send_dm_to_user(u.slack_user_id, msg)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send digest to user {u.username}: {e}")

            self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} digest messages for company: {company.name}'))

from django.conf import settings
