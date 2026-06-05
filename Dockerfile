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

# ── Frontend build ────────────────────────────────────────────────────────────
# Build the React app so frontend/dist/index.html is available for Django's
# catch-all TemplateView and the compiled assets are picked up by collectstatic.
# VITE_* build-time env vars can be passed as --build-arg at image build time.
ARG VITE_API_BASE=http://localhost:8000
ARG VITE_CLIENT_ID=changeme
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_CLIENT_ID=${VITE_CLIENT_ID}

COPY frontend/package*.json /reminder_app/frontend/
RUN cd /reminder_app/frontend && npm ci --silent

COPY frontend/ /reminder_app/frontend/
RUN cd /reminder_app/frontend && npm run build

# ── Application code ──────────────────────────────────────────────────────────
COPY . /reminder_app/

# ── Runtime setup ─────────────────────────────────────────────────────────────
RUN mkdir -p /reminder_app/staticfiles

ENV DJANGO_SETTINGS_MODULE=reminder_app.settings
ENV PYTHONPATH=/reminder_app
ENV PORT=8080

RUN chmod +x /reminder_app/start.sh
RUN chmod +x /reminder_app/minimal_start.sh

EXPOSE 8080
CMD ["/reminder_app/start.sh"]
