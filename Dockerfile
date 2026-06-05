# python:3.9-alpine3.16 reached end of life on 2024-05-23 — no more CVE patches.
# Upgraded to python:3.11-alpine3.21 (latest stable, supported until 2027-10).
FROM python:3.11-alpine3.21
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install deps
# xmlsec requires: libxml2-dev, xmlsec-dev, etc.
RUN apk add --no-cache netcat-openbsd gcc musl-dev libxml2-dev libxslt-dev libffi-dev xmlsec-dev openssl-dev build-base pkgconfig

WORKDIR /reminder_app

# Copy requirements first for better caching
COPY requirements.txt /reminder_app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY . /reminder_app/

# Create staticfiles and static directories
RUN mkdir -p /reminder_app/staticfiles
RUN mkdir -p /reminder_app/static

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=reminder_app.settings
ENV PYTHONPATH=/reminder_app
ENV PORT=8080

# Make startup scripts executable
RUN chmod +x /reminder_app/start.sh
RUN chmod +x /reminder_app/minimal_start.sh

# Expose port
EXPOSE 8080

# Use the full startup script for production
CMD ["/reminder_app/start.sh"]