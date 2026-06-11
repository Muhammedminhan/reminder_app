# python:3.9-alpine3.16 reached end of life on 2024-05-23 — no more CVE patches.
# Upgraded to python:3.11-alpine3.21 (latest stable, supported until 2027-10).
FROM python:3.11-alpine3.21
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── System deps ───────────────────────────────────────────────────────────────
# xmlsec / SAML requires libxml2, libxslt, xmlsec; Node.js for frontend build.
RUN apk add --no-cache \
    netcat-openbsd gcc musl-dev \
    libxml2-dev libxslt-dev libffi-dev xmlsec-dev openssl-dev \
    build-base pkgconfig \
    nodejs npm

WORKDIR /reminder_app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt /reminder_app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Copy full source FIRST ────────────────────────────────────────────────────
# Must come before the frontend build so the build output lands inside the
# already-copied source tree and is not wiped by a later COPY.
# (.dockerignore excludes node_modules/, frontend/dist/, .git, etc.)
COPY . /reminder_app/

# ── Frontend build ────────────────────────────────────────────────────────────
# Builds the React app after source is in place so frontend/dist/ ends up at
# /reminder_app/frontend/dist/ — picked up by TEMPLATES['DIRS'] and
# STATICFILES_DIRS in settings.py for Django to serve via Whitenoise.
# VITE_* env vars are baked into the JS bundle at build time.
ARG VITE_API_BASE=http://localhost:8000
ARG VITE_CLIENT_ID=changeme
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_CLIENT_ID=${VITE_CLIENT_ID}

# Warn loudly if build args are still at their placeholder defaults.
# This catches CI/CD pipelines that forgot to pass --build-arg values.
RUN if [ "${VITE_CLIENT_ID}" = "changeme" ]; then \
      echo "WARNING: VITE_CLIENT_ID is 'changeme' — pass --build-arg VITE_CLIENT_ID=<your-oauth-client-id>"; \
    fi && \
    if [ "${VITE_API_BASE}" = "http://localhost:8000" ]; then \
      echo "WARNING: VITE_API_BASE is 'localhost:8000' — pass --build-arg VITE_API_BASE=https://your-cloudrun-url.run.app"; \
    fi

RUN cd /reminder_app/frontend && npm ci --silent && npm run build

# ── Runtime setup ─────────────────────────────────────────────────────────────
RUN mkdir -p /reminder_app/staticfiles

ENV DJANGO_SETTINGS_MODULE=reminder_app.settings
ENV PYTHONPATH=/reminder_app
ENV PORT=8080

RUN chmod +x /reminder_app/start.sh

EXPOSE 8080
CMD ["/reminder_app/start.sh"]
