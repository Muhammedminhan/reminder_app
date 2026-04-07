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

# Check environment variables
echo "=== Environment Variables ==="
echo "DEBUG: ${DEBUG:-not set}"
echo "SECRET_KEY: ${SECRET_KEY:-not set}"
echo "DB_HOST: ${DB_HOST:-not set}"
echo "DB_NAME: ${DB_NAME:-not set}"
echo "DB_USER: ${DB_USER:-not set}"
echo "DB_PASSWORD: ${DB_PASSWORD:-not set}"
echo "SENDGRID_API_KEY: ${SENDGRID_API_KEY:-not set}"

# Check if SECRET_KEY is set (required for Django)
if [ -z "$SECRET_KEY" ]; then
    echo "WARNING: SECRET_KEY not set, using default"
    export SECRET_KEY="django-insecure-default-key-for-testing-only"
fi

# List files in current directory
echo "=== Current Directory Contents ==="
ls -la

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

python -c "import os; print('OS import OK')" || {
    echo "ERROR: OS import failed"
    exit 1
}

# Test Django settings
echo "=== Testing Django Settings ==="
python manage.py check --deploy || {
    echo "WARNING: Django check failed, but continuing..."
}

# Test database connection (skip if no DB_HOST)
if [ -n "$DB_HOST" ]; then
    echo "=== Testing Database Connection ==="
    python manage.py check --database default || {
        echo "WARNING: Database connection failed, but continuing..."
    }
else
    echo "=== Skipping Database Test (no DB_HOST) ==="
fi

# Run migrations (skip if no DB_HOST)
if [ -n "$DB_HOST" ]; then
    echo "=== Running Migrations ==="
    python manage.py migrate --noinput || {
        echo "WARNING: Migrations failed, but continuing..."
    }
else
    echo "=== Skipping Migrations (no DB_HOST) ==="
fi

# Collect static files
echo "=== Collecting Static Files ==="
python manage.py collectstatic --noinput --clear || {
    echo "WARNING: Static file collection failed, but continuing..."
}

# Create superuser if needed
echo "=== Checking Superuser ==="
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Creating superuser...')
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
" || {
    echo "WARNING: Superuser creation failed, but continuing..."
}

# Setup OAuth Application
echo "=== Setting Up OAuth Application ==="
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
django.setup()

from oauth2_provider.models import Application
from django.contrib.auth import get_user_model

# The credentials given to the frontend team
FRONTEND_CLIENT_ID = 'REDACTED_CLIENT_ID'
FRONTEND_CLIENT_SECRET = 'REDACTED_CLIENT_SECRET'

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

if not user:
    print('ERROR: No superuser found for OAuth app')
else:
    app, created = Application.objects.update_or_create(
        client_id=FRONTEND_CLIENT_ID,
        defaults={
            'name': 'NotifyHub Frontend',
            'client_secret': FRONTEND_CLIENT_SECRET,
            'client_type': Application.CLIENT_PUBLIC,
            'authorization_grant_type': Application.GRANT_PASSWORD,
            'user': user,
            'skip_authorization': True,
        }
    )
    if created:
        print(f'✓ OAuth application created: {app.name}')
    else:
        print(f'✓ OAuth application updated: {app.name}')
    print(f'✓ Client ID: {app.client_id}')
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

# Start the application
echo "=== Starting Gunicorn ==="
echo "Command: gunicorn reminder_app.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --error-logfile - --log-level debug --preload"

exec gunicorn reminder_app.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --preload