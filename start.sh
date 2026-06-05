#!/bin/sh

# Exit on any error
set -e

echo "=== NotifyHub Container Startup ==="
echo "Timestamp: $(date)"
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Django version: $(python -c 'import django; print(django.get_version())')"

# Check if we're in Cloud Run
if [ -n "$K_SERVICE" ]; then
    echo "Running in Cloud Run service: $K_SERVICE"
fi

# Set default port if not provided
export PORT=${PORT:-8080}
echo "Using port: $PORT"

# ── Environment sanity checks (values are NOT printed to avoid leaking secrets) ──
echo "=== Environment Variable Presence Check ==="
echo "DEBUG set:              $([ -n "$DEBUG" ]            && echo YES || echo NO)"
echo "SECRET_KEY set:         $([ -n "$SECRET_KEY" ]       && echo YES || echo NO)"
echo "DB_HOST set:            $([ -n "$DB_HOST" ]          && echo YES || echo NO)"
echo "DB_NAME set:            $([ -n "$DB_NAME" ]          && echo YES || echo NO)"
echo "DB_USER set:            $([ -n "$DB_USER" ]          && echo YES || echo NO)"
echo "DB_PASSWORD set:        $([ -n "$DB_PASSWORD" ]      && echo YES || echo NO)"
echo "SENDGRID_API_KEY set:   $([ -n "$SENDGRID_API_KEY" ] && echo YES || echo NO)"
echo "REDIS_URL set:          $([ -n "$REDIS_URL" ]        && echo YES || echo NO)"
echo "ALLOWED_HOSTS set:      $([ -n "$ALLOWED_HOSTS" ]    && echo YES || echo NO)"

# ── Abort if critical secrets are missing ──
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY is not set. Refusing to start."
    exit 1
fi

if [ -z "$ALLOWED_HOSTS" ]; then
    echo "ERROR: ALLOWED_HOSTS is not set. All requests would return 400. Refusing to start."
    exit 1
fi

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    echo "ERROR: manage.py not found!"
    exit 1
fi

# Test basic Python imports
echo "=== Testing Python Imports ==="
python -c "import django; print('Django import OK')" || {
    echo "ERROR: Django import failed"
    exit 1
}

# Test Django settings
echo "=== Testing Django Settings ==="
python manage.py check || {
    echo "WARNING: Django check failed, but continuing..."
}

# Run migrations
if [ -n "$DB_HOST" ]; then
    echo "=== Running Migrations ==="
    python manage.py migrate --noinput || {
        echo "ERROR: Migrations failed"
        exit 1
    }
else
    echo "=== Skipping Migrations (no DB_HOST) ==="
fi

# Collect static files
echo "=== Collecting Static Files ==="
python manage.py collectstatic --noinput --clear || {
    echo "WARNING: Static file collection failed, but continuing..."
}

# ── Create superuser from env vars — never use a hardcoded default password ──
echo "=== Checking Superuser ==="
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(is_superuser=True).exists():
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email    = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

    if not username or not password:
        print('WARNING: No superuser exists and DJANGO_SUPERUSER_USERNAME/'
              'DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation.')
    else:
        User.objects.create_superuser(username, email or '', password)
        print('Superuser created from environment variables.')
else:
    print('Superuser already exists.')
" || {
    echo "WARNING: Superuser check failed, but continuing..."
}

# ── Set up OAuth application from env vars only — no hardcoded credentials ──
echo "=== Setting Up OAuth Application ==="
python manage.py shell -c "
import os
from oauth2_provider.models import Application
from django.contrib.auth import get_user_model

client_id     = os.environ.get('OAUTH_CLIENT_ID')
client_secret = os.environ.get('OAUTH_CLIENT_SECRET')

if not client_id or not client_secret:
    print('WARNING: OAUTH_CLIENT_ID or OAUTH_CLIENT_SECRET not set — skipping OAuth app setup.')
else:
    User = get_user_model()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print('WARNING: No superuser found — skipping OAuth app setup.')
    else:
        app, created = Application.objects.update_or_create(
            client_id=client_id,
            defaults={
                'name': 'NotifyHub Frontend',
                'client_secret': client_secret,
                'client_type': Application.CLIENT_PUBLIC,
                'authorization_grant_type': Application.GRANT_PASSWORD,
                'user': user,
                'skip_authorization': True,
            }
        )
        print('OAuth application %s.' % ('created' if created else 'updated'))
" || {
    echo "WARNING: OAuth setup failed, but continuing..."
}

# Test WSGI application
echo "=== Testing WSGI Application ==="
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
import django
django.setup()
from reminder_app.wsgi import application
print('WSGI application loaded successfully')
" || {
    echo "ERROR: WSGI application failed to load"
    exit 1
}

# ── Start Gunicorn with sensible worker count ──
# Use gthread worker for better concurrency on Cloud Run without extra RAM.
WORKERS=${GUNICORN_WORKERS:-2}
THREADS=${GUNICORN_THREADS:-4}

echo "=== Starting Gunicorn (workers=$WORKERS, threads=$THREADS) ==="

exec gunicorn reminder_app.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --worker-class gthread \
    --workers "$WORKERS" \
    --threads "$THREADS" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload
