import os
from decouple import config

# ── Default sender identity ───────────────────────────────────────────────────
# These are used as fallbacks when a reminder has no custom sender_email /
# sender_name set.  Override both via environment variables so the correct
# SendGrid-authenticated domain is used in every environment.
#
# Required SendGrid setup: the domain in SENDER_EMAIL must be authenticated
# in your SendGrid account (Settings → Sender Authentication).
#
# Environment variables:
#   DEFAULT_SENDER_EMAIL  — e.g. "notifications@yourdomain.com"
#   DEFAULT_SENDER_NAME   — e.g. "NotifyHub"

SENDER_EMAIL = config('DEFAULT_SENDER_EMAIL', default=os.environ.get('DEFAULT_SENDER_EMAIL', 'notifications@notifyhub.app'))
SENDER_NAME  = config('DEFAULT_SENDER_NAME',  default=os.environ.get('DEFAULT_SENDER_NAME',  'NotifyHub'))

rem_fields = ['company', 'send']
