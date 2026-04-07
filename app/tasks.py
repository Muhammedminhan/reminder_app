from django.conf import settings
from twilio.rest import Client
import sendgrid
from sendgrid.helpers.mail import Email
from sendgrid.helpers.mail import To
from sendgrid.helpers.mail import Content
from sendgrid.helpers.mail import Mail
from decouple import config
from .constants import SENDER_NAME
from python_http_client.exceptions import HTTPError
import logging
import requests
from datetime import datetime, timedelta
from django.core.mail import send_mail
from .models import Reminder
from app.utils import _notify_slack_pending_reminder
from django.utils import timezone

logger = logging.getLogger(__name__)

def send_scheduled_email(reminder_id):
    from .models import Reminder

    try:
        reminder = Reminder.objects.get(id=reminder_id)

        if reminder.send == False:
            sg = sendgrid.SendGridAPIClient(api_key=config('SENDGRID_API_KEY'))

            if reminder.sender_email:
                SENDER_EMAIL = reminder.sender_email
            else:
                from .constants import SENDER_EMAIL as DEFAULT_SENDER_EMAIL
                SENDER_EMAIL = DEFAULT_SENDER_EMAIL

            from_email = Email(SENDER_EMAIL)
            email_list = reminder.receiver_email.split(",")
            for email in email_list:
                to_email = To(email)
                subject = reminder.title
                message = reminder.description
                content = Content("text/plain", message)
                mail = Mail(from_email, to_email, subject, content)

                try:
                    sg.client.mail.send.post(request_body=mail.get())
                except HTTPError as e:
                    logger.warning(e.to_dict())

            # Send SMS if phone number is provided
            if reminder.phone_no:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                sms_message = client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=reminder.phone_no
                )

                # wtsp_message = client.messages.create(
                #
                #     from_="whatsapp:+14155238886",
                #     body=message,
                #     to=f"whatsapp:{reminder.phone_no}"
                # )

            reminder.send = True
            reminder.save()
            # Removed immediate Slack notification; Slack notices are sent daily at 9 AM for pending reminders.
            return f"Email and SMS sent successfully."
    except Reminder.DoesNotExist:
        return "Reminder does not exist."
    except Exception as e:
        return f"An error occurred: {str(e)}"


# @shared_task
# def check_domain_verification(domain_id):
#     from .models import DomainVerification
#     from .utils import check_txt_record
#     try:
#         domain_verification = DomainVerification.objects.get(id=domain_id)
#         if not domain_verification.verified:
#             if check_txt_record(domain_verification):
#                 messages.success(f"Domain {domain_verification.domain} has been successfully verified!")
#             else:
#                 # Reschedule the task to check again after 1 hour
#                 check_domain_verification.apply_async((domain_id,), countdown=3600)
#     except DomainVerification.DoesNotExist:
#         pass

def check_domain_verification(domain_id):
    from .models import SendGridDomainAuth
    url = f"https://api.sendgrid.com/v3/whitelabel/domains/{domain_id}"
    headers = {
        "Authorization": f"Bearer {config('SENDGRID_API_KEY')}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        sendgrid_instance = SendGridDomainAuth.objects.get(domain_id=domain_id)
        sendgrid_instance.is_verified = data.get("valid", False)
        sendgrid_instance.save()
        # return data.get("valid", False)
    else:
        check_domain_verification.apply_async((domain_id,), countdown=3600)


def reset_sent_status():
    from .models import Reminder

    Reminder.objects.update(send=False)

def count_recipients(reminder):
    """Return the number of valid recipient emails for a reminder instance."""
    emails = [e.strip() for e in reminder.receiver_email.split(',') if e.strip()]
    return len(emails)

def get_total_emails_for_date(target_date):
    """Return total number of emails scheduled for a given date (date only, not datetime)."""
    reminders = Reminder.objects.filter(reminder_start_date__date=target_date, active=True, is_deleted=False)
    return sum(count_recipients(r) for r in reminders)

def check_and_notify_admin_for_email_threshold():
    """Check reminders scheduled for today and the next 7 days, notify admin if >=80 emails for any day."""
    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    logger.info(f"ADMIN_EMAIL: {admin_email}")
    if not admin_email:
        logger.warning("ADMIN_EMAIL not set in settings.")
        return
    today = datetime.now().date()
    threshold = 80
    alert_days = []
    for offset in range(0, 8):  # Today + next 7 days
        target_date = today + timedelta(days=offset)
        total_emails = get_total_emails_for_date(target_date)
        logger.info(f"Checking {target_date}: {total_emails} emails scheduled.")
        if total_emails >= threshold:
            alert_days.append((target_date, total_emails))
    if alert_days:
        subject = "High Email Volume Alert: Upcoming Days"
        message_lines = ["The following days have high scheduled email volume:"]
        for date, count in alert_days:
            message_lines.append(f"- {date}: {count} emails scheduled")
        message = "\n".join(message_lines)
        logger.info(f"Sending admin alert: {message}")
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [admin_email])
            logger.info(f"Admin notified for high volume days: {alert_days}")
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

def process_slack_pending_reminders():
    """Send Slack notifications at 9 AM for reminders that were sent and are still pending today.

    Filters reminders with:
    - send=True (email/SMS already sent)
    - completed=False (still pending)
    - active=True and not deleted
    - reminder_start_date is today (server local date)
    """
    try:
        now = timezone.localtime()
        today = now.date()
        # Select pending reminders for today
        qs = Reminder.objects.filter(
            active=True,
            is_deleted=False,
            send=True,
            completed=False,
            reminder_start_date__date=today,
        )
        count = 0
        for reminder in qs.iterator():
            try:
                _notify_slack_pending_reminder(reminder)
                count += 1
            except Exception as e:
                logger.warning(f"Slack notification failed for reminder {getattr(reminder,'id',None)}: {e}")
        logger.info(f"Processed Slack pending reminders for {today}: {count} notifications attempted.")
        return {"ok": True, "processed": count}
    except Exception as e:
        logger.error(f"process_slack_pending_reminders error: {e}")
        return {"ok": False, "error": str(e)}
