from django.core.management.base import BaseCommand
from django.conf import settings          # ← moved to top (was at bottom — NameError)
from django.utils import timezone
from datetime import timedelta
import logging

from app.models import Reminder, Company, User
from app.slack import send_channel_message, send_dm_to_user

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send daily morning Slack notifications listing pending reminders'

    def handle(self, *args, **options):
        companies = Company.objects.filter(slack_daily_digest_enabled=True)
        if not companies.exists():
            self.stdout.write(self.style.WARNING('No companies have daily digest enabled.'))
            return

        for company in companies:
            now = timezone.now()
            next_24h = now + timedelta(days=1)

            pending = Reminder.objects.filter(
                company=company,
                completed=False,
                active=True,
                is_deleted=False,
                send=False,           # ← exclude reminders already emailed out
                reminder_start_date__lte=next_24h,
            ).order_by('reminder_start_date')

            if not pending.exists():
                logger.debug(f"No pending reminders for {company.name}")
                continue

            # Build the dashboard URL from ALLOWED_HOSTS — settings is now imported
            # at the top of the file so this no longer raises NameError.
            host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
            dashboard_url = f"https://{host}"

            msg = f"☀️ *Morning Reminder Digest for {company.name}*\n"
            msg += f"Today is {now.strftime('%A, %b %d %Y')}\n\n"

            for r in pending:
                status = "🔴 OVERDUE" if r.reminder_start_date < now else "🕒 UPCOMING"
                msg += f"• *{r.title}* ({status})\n"
                msg += f"  - Due: {r.reminder_start_date.strftime('%I:%M %p')}\n"
                msg += f"  - To: {r.receiver_email}\n\n"

            msg += f"Check your dashboard: {dashboard_url}"

            sent_count = 0

            # ── Send to configured channels ───────────────────────────────────
            if company.slack_digest_channels:
                for channel in company.slack_digest_channels.split(','):
                    channel = channel.strip()
                    if channel:
                        try:
                            send_channel_message(channel, msg)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send digest to channel {channel}: {e}")

            # ── Send to configured users as DMs ───────────────────────────────
            # Fix: pass the User object to send_dm_to_user, NOT the slack_user_id
            # string.  send_dm_to_user() reads user.slack_user_id internally via
            # getattr — passing a raw string caused getattr to return None every
            # time and silently fell back to the fallback channel (or dropped).
            if company.slack_digest_users:
                user_ids = [uid.strip() for uid in company.slack_digest_users.split(',') if uid.strip()]
                users = User.objects.filter(id__in=user_ids)
                for u in users:
                    try:
                        send_dm_to_user(u, msg)   # ← pass User object, not u.slack_user_id
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send digest DM to user {u.username}: {e}")

            self.stdout.write(self.style.SUCCESS(
                f'Sent {sent_count} digest messages for company: {company.name}'
            ))
