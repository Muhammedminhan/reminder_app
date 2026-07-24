# Codebase Audit Report — NotifyHub / reminder_app

**Original audit date:** 2026-06-12
**Last updated:** 2026-07-24
**Scope:** Django backend (`app/`, `reminder_app/`), deployment config (Dockerfile, start.sh, cloudbuild.yaml), frontend env config. Excludes `.venv`, `node_modules`, `staticfiles`, migrations.
**Method:** Three parallel review passes (security, correctness, configuration/deployment), with key findings independently re-verified against the source; followed by multi-pass iterative fix-and-re-audit cycles.

> **Important:** This document was significantly out of date as of 2026-07-24. The original version listed 3 Critical and 9 High findings, the majority of which had already been resolved in subsequent commits. Any reader of the prior revision would have misjudged the app's real security posture in both directions. This revision reflects the **actual current state** of the codebase.

---

## Current status summary

| Severity | Original count | Fixed | Remaining open |
|----------|---------------|-------|----------------|
| Critical | 3 | 2 | 1 (C1 — local secrets / git config) |
| High | 9 | 9 | 0 |
| Medium | 9 | 5 | 4 (M4, M5, M7, M8) |
| Low | 7 | 3 | 4 (L1, L3, L4, L6) |

---

## CRITICAL

### C1. Live production secrets in local `.env` and git remote URLs — **STILL OPEN**
- **Files:** `.env`, `frontend/.env`, `.git/config`
- `.env` contains a real SendGrid API key, Twilio Account SID + Auth Token, Google OAuth client ID + secret, and the Django `SECRET_KEY` in plaintext. While not committed, this directory lives in `Downloads/`. The original audit also flagged GitHub personal access tokens embedded in `.git/config` remote URLs (`https://Muhammedminhan:ghp_...@github.com/...`); the remote URLs in the current repo use plain HTTPS with no embedded token, but the credential situation should be verified independently.
- **Fix:**
  1. Rotate all credentials that may have been exposed: SendGrid key, Twilio auth token, Google OAuth client secret, Django `SECRET_KEY`.
  2. Verify `.git/config` contains no embedded PATs: `git remote -v` should show plain `https://github.com/...` URLs with no credentials. If tokens are present, remove them: `git remote set-url origin https://github.com/Muhammedminhan/reminder_app.git` and use `gh auth login` or macOS keychain instead.
  3. Use GCP Secret Manager for production values rather than `.env` files.

### C2. OAuth client secret in frontend bundle — **FIXED**
- `VITE_CLIENT_SECRET` has been removed from `frontend/.env.example`. The OAuth application is now registered as a `CLIENT_PUBLIC` client using PKCE (`GRANT_AUTHORIZATION_CODE`); no client secret is stored or required. The `GRANT_PASSWORD` flow (which could bypass MFA) has been explicitly disabled via `ALLOWED_GRANT_TYPES`.

### C3. Weak fallback secrets / silent insecure deployment — **FIXED**
- `SECRET_KEY` now has no default and raises `ImproperlyConfigured` when unset in any environment. `ALLOWED_HOSTS` is required and validated at startup (`start.sh` aborts if unset). `DEBUG=True` is blocked on Cloud Run (`K_SERVICE` check). `JWT_SIGNING_KEY` is required in production with the same fail-fast pattern.

---

## HIGH

### H1. Naive datetime in email-threshold check — **FIXED**
- `app/tasks.py` now uses `timezone.now().date()` throughout. Verified: no remaining `datetime.now()` calls in task processing code.

### H2. SAML ACS issuer check failed open — **FIXED** (2026-07-24)
- The issuer cross-check was present but contained two silent bypass paths: if `get_last_response_in_xml()` returned `None`, or if the `<Issuer>` element was absent/empty, the check was skipped and authentication continued. A crafted SAML response without an `<Issuer>` element could bypass tenant binding.
- **Fix applied:** The check now **fails closed** at every step. A missing XML blob, absent `<Issuer>` element, empty issuer text, or any mismatch all result in an immediate `403`. An exception during XML parsing also results in a `403` (not a pass-through).

### H3. SAML JIT provisioning: no email-domain allowlist — **FIXED**
- JIT provisioning now validates that the asserted email's domain exactly matches `company.domain`. A mismatch produces a `403` with a warning log entry. If `company.domain` is not configured, the endpoint fails closed rather than allowing all domains.
- Additionally, existing users are cross-checked: a user whose `company_id` doesn't match the ACS `company_id` is rejected even after a valid SAML assertion.

### H4. Password-reset token reuse race condition — **FIXED**
- The one-time-use nonce is now stored as a SHA-256 hash in cache (opaque random token, not email-in-URL). Token consumption uses `cache.add()` (Redis `SET NX`) as an atomic claim gate so concurrent requests cannot both consume the same nonce.

### H5. SAML metadata falls back to `http://localhost:8000` — **FIXED**
- `app/sso.py` now raises `ValueError("Cannot determine SAML base URL: set BACKEND_URL env var or ALLOWED_HOSTS.")` instead of silently constructing a localhost URL. The error surfaces at SSO-metadata request time, not silently at login time.

### H6. No rate limiting on webhook endpoints — **FIXED**
- All four webhook endpoints now go through `_check_webhook_auth()`, which enforces per-IP rate limiting (10 requests/min) in addition to token authentication. The webhook token is required to be a high-entropy env var; `start.sh` validates it is set before launch.

### H7. Docker container runs as root — **FIXED**
- `Dockerfile` creates a non-root `django` user and switches to it before the `CMD` directive. Gunicorn now runs as an unprivileged user.

### H8. No Docker `HEALTHCHECK` — **FIXED**
- `Dockerfile` includes a `HEALTHCHECK` against `/health/`. Cloud Run startup and liveness probes are documented in `cloudbuild.yaml`.

### H9. `DEBUG=True` allowed in production — **FIXED**
- `settings.py` raises `ImproperlyConfigured` if `DEBUG=True` when `K_SERVICE` is set (Cloud Run). `start.sh` also checks and aborts. The local `.env.example` documents `DEBUG=True` as a local-only value.

---

## MEDIUM

### M1. Soft-delete not atomic — **FIXED**
- `Reminder.delete()` now uses `Reminder.objects.filter(pk=self.pk, is_deleted=False).update(is_deleted=True)` and returns the correct update count.

### M2. N+1 queries in GraphQL reminder listings — **FIXED**
- `resolve_reminders` now uses `.prefetch_related('visible_to_groups', 'attachments', 'slack_users')`.

### M3. Unclamped `limit` on GraphQL queries — **FIXED**
- All limit-accepting resolvers (including `resolve_audit_logs`) now clamp: `limit = max(1, min(int(limit or 50), 1000))`.

### M4. Silent failure when `custom_repeat_days` is malformed — **STILL OPEN**
- **File:** `app/utils.py` (`_schedule_next_reminder`)
- `int(d) for d in days.split(',')` can raise `ValueError` on bad data, swallowed by a broad `except Exception`, causing the reminder to silently stop recurring.
- **Fix:** Validate the day list explicitly (integers 0–6, non-empty) at write time and log a specific error naming the reminder ID on failure.

### M5. CSV/TXT uploads bypass content validation — **STILL OPEN**
- **File:** `app/views.py` (attachment upload handler)
- `.txt`/`.csv` are allowed with no content inspection: binary payloads can be uploaded under a `.txt` name, and CSV formula injection (`=`, `+`, `@`, `-` prefixes) is possible if files are later opened in spreadsheet software.
- **Fix:** Reject null bytes in text uploads; sanitize or reject formula-prefixed CSV cells.

### M6. Inconsistent timezone conventions — **FIXED**
- `app/tasks.py` now consistently uses `timezone.now()` for instants. `H1` fix resolved the primary instance; the remaining mixed usage has been unified.

### M7. Rate limiting silently disabled when cache is down — **STILL OPEN**
- **File:** `app/views.py` (all rate-limit blocks)
- If Redis is unavailable, `cache.get()` returns `None` (counter reads as 0) and rate limiting is silently bypassed across all endpoints. The signup rate-limit block wraps the entire check in `except Exception: pass`, meaning a cache error is indistinguishable from a clean request.
- **Fix:** Treat a cache error in any rate-limit check as "throttled" (fail closed), or use a DB-backed fallback for critical endpoints (login, MFA, password reset).

### M8. Attachment upload rejects superusers — **STILL OPEN**
- **File:** `app/views.py` (attachment upload)
- Superusers with `company=None` receive a `400` on upload, although they can create reminders. The asymmetric permission is undocumented.
- **Fix:** Allow superusers to specify a company context on upload, or document the limitation in the API.

### M9. Dead Celery code — **FIXED**
- `check_domain_verification` and other Celery task remnants have been removed. The module comment clarifying that background tasks now use Cloud Tasks is present.

---

## LOW

### L1. Full password-reset links written to logs in DEBUG — **STILL OPEN**
- **File:** `app/views.py` (forgot_password)
- Full reset URLs (containing the nonce) are logged when `DEBUG=True`. Log only the user ID and a hashed token reference.

### L2. Bare `except Exception: pass` around role lookup — **FIXED**
- The specific silently-swallowed exceptions that could hide corrupted-data errors have been replaced with logged failures. The most critical cases (`_get_oauth_user`, JWT blacklist in `reset_password`) now call `logger.exception()` / `logger.warning(..., exc_info=True)` so failures are visible in monitoring.

### L3. Redundant model import inside method — **STILL OPEN**
- **File:** `app/models.py` — `from .models import UserRole` inside a method body in the same module.

### L4. `Reminder.is_active()` is unused — **STILL OPEN**
- **File:** `app/models.py` — method is never called by task processing; docstring doesn't match behavior.

### L5. Unpinned pip in Dockerfile — **FIXED**
- Dockerfile now pins the pip version for reproducible builds.

### L6. Stale commented-out credentials in `.env` — **STILL OPEN**
- Old Postgres DSN with a placeholder password and a `xoxb-your-token-here` Slack token should be removed to reduce noise when auditing the env file.

### L7. `VITE_CLIENT_SECRET` in `frontend/.env.example` — **FIXED** (see C2)

---

## X-Forwarded-For consolidation — **FIXED** (2026-07-24)
The IP extraction one-liner (`request.META.get('HTTP_X_FORWARDED_FOR', ...).split(',')[-1].strip()`) was copy-pasted verbatim across 8 rate-limit blocks with no centralised validation. Replaced with a single `_get_client_ip(request)` helper that documents the Cloud Run proxy model and the reason for using the rightmost XFF entry.

---

## Google OAuth code-in-URL leakage — **FIXED** (2026-07-24)
The OAuth callback previously issued a one-time code in the redirect URL (`?code=` then `#code=`). Either form appeared in Django/nginx access logs via the `Location` response header. Replaced with a PKCE-style nonce binding:
- Frontend generates a 32-byte random nonce via `crypto.getRandomValues()`, hashes it with `crypto.subtle.digest('SHA-256')`, stores the raw nonce only in `sessionStorage`, and navigates to `/google/login/?nonce=<hash>`.
- Backend stores the token keyed by the nonce hash and redirects to `{FRONTEND_URL}/login` with no code in the URL.
- Frontend reads the raw nonce from `sessionStorage` and POSTs it to `/google/token-exchange/`.
- Exchange is atomic via `cache.add()` (Redis `SET NX`).

---

## Persistent good practices (confirmed current)

- `.env`, `db.sqlite3`, `media/`, and `staticfiles/` are not tracked in git.
- Security headers (HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`), `SECURE_REFERRER_POLICY`, `Permissions-Policy`, and a strict `Content-Security-Policy` are all configured.
- JWT rotation + blacklist active; access tokens are revoked on password reset.
- GraphQL introspection disabled outside `DEBUG`.
- AES-256-GCM encryption for field-level secrets (`app/encryption.py`) with tamper-detection tests.
- Consistent tenant scoping across all GraphQL resolvers (`company` filter on every multi-tenant queryset).
- MFA (TOTP) enforced at login; per-challenge attempt counter prevents brute-force even with IP rotation.
- OAuth2 password grant disabled; only `authorization_code`, `refresh_token`, and `client_credentials` are permitted.
- Cloud SQL connection-budget math documented inline (worker × thread count vs. max connections).
