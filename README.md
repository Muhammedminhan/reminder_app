# NotifyHub

Enterprise reminder and notification platform built on Django + React, deployable to Google Cloud Run.

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, DRF, Graphene-Django (GraphQL) |
| Auth | Django OAuth Toolkit (Authorization Code + PKCE), Google OAuth2, SAML SSO |
| Frontend | React 18, Apollo Client, Vite |
| Database | PostgreSQL (Cloud SQL) / SQLite (local dev) |
| Cache | Redis / Cloud Memorystore |
| Storage | Google Cloud Storage (media), WhiteNoise (static) |
| Notifications | SendGrid (email), Twilio (SMS), Slack |
| Deployment | Cloud Run, Docker, Gunicorn (gthread) |

---

## Quick Start (Local)

```bash
cp .env.example .env          # fill in SECRET_KEY, DB_*, REDIS_URL at minimum
docker-compose up db redis -d
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_permissions --create-roles
python manage.py createsuperuser
python manage.py runserver    # backend on :8000

cd frontend && npm install && npm run dev   # frontend on :5173
```

---

## Docker Build

```bash
docker build \
  --build-arg VITE_API_BASE=https://your-backend-url \
  --build-arg VITE_CLIENT_ID=your-oauth-client-id \
  -t notifyhub .
```

---

## Cloud Run

Set all variables from `.env.example` in your Cloud Run service.
Critical ones: `SECRET_KEY`, `ALLOWED_HOSTS`, `DB_*`, `WEBHOOK_TOKEN`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `BACKEND_URL`, `FRONTEND_URL`,
`CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `GCS_BUCKET_NAME`.

---

## Project Structure

```
app/              Django app — models, views, GraphQL schema, tasks, Slack
frontend/src/     React app — lib/api.js, lib/apollo.js, pages/
reminder_app/     Django project settings + URLs
docs/             API guides, Postman collections
tests/            Test suite
Dockerfile        Multi-stage: Python deps → frontend build → collectstatic
start.sh          Container entrypoint (migrate → setup_permissions → gunicorn)
.env.example      All 24 env vars documented with REQUIRED/OPTIONAL labels
```

---

## Running Tests

```bash
python manage.py test app
```
