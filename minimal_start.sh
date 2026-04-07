#!/bin/sh

# Minimal startup script for debugging
set -e

echo "=== Minimal Container Startup Test ==="
echo "Timestamp: $(date)"
echo "Working directory: $(pwd)"

# Set default port
export PORT=${PORT:-8080}
echo "Using port: $PORT"

# Set default SECRET_KEY if not provided
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="django-insecure-default-key-for-testing-only"
    echo "Using default SECRET_KEY"
fi

# Test basic Python
echo "=== Testing Python ==="
python --version
python -c "print('Python is working')"

# Test Django import
echo "=== Testing Django Import ==="
python -c "import django; print(f'Django version: {django.get_version()}')"

# Test Django setup
echo "=== Testing Django Setup ==="
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
import django
django.setup()
print('Django setup successful')
"

# Test WSGI import
echo "=== Testing WSGI Import ==="
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
import django
django.setup()
from reminder_app.wsgi import application
print('WSGI application imported successfully')
"

# Start minimal server
echo "=== Starting Minimal Server ==="
echo "Starting gunicorn on port $PORT..."

exec gunicorn reminder_app.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug
