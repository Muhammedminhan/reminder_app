# Codebase Audit Report — NotifyHub / reminder_app

**Date:** 2026-06-12
**Scope:** Django backend (`app/`, `reminder_app/`), deployment config (Dockerfile, start.sh, cloudbuild.yaml), frontend env config. Excludes `.venv`, `node_modules`, `staticfiles`, migrations.
**Method:** Three parallel review passes (security, correctness, configuration/deployment), with key findings independently re-verified against the source.

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 3 |
| High     | 9 |
| Medium   | 9 |
| Low      | 7 |

**Good news first:** `.env` and `frontend/.env` are correctly **not tracked in git** (verified with `git ls-files` — only the `.env.example` files are committed). Security headers (HSTS, nosniff, X-Frame-Options DENY), JWT token rotation + blacklist, and GraphQL introspection disabling in production are all correctly configured.

---

## CRITICAL

### C1. Live production secrets in local `.env` and in git remote URLs
- **Files:** `.env`, `frontend/.env`, `.git/config`
- `.env` contains a real SendGrid API key, Twilio Account SID + Auth Token, Google OAuth client ID + secret, and the Django `SECRET_KEY` in plaintext. While not committed, this directory has been shared/zipped (it lives in `Downloads/`), and the git remote URLs in `.git/config` embed **GitHub personal access tokens in plaintext** (e.g. `https://Muhammedminhan:ghp_...@github.com/...`). Anyone with a copy of this directory gets working credentials for GitHub, SendGrid, Twilio, and Google OAuth.
- **Fix:**
  1. Revoke and rotate all of these now: the SendGrid key, Twilio auth token, Google OAuth secret, both GitHub PATs, and the Django `SECRET_KEY`.
  2. Remove tokens from remote URLs: `git remote set-url origin https://github.com/Muhammedminhan/reminder_app.git` and use a credential helper (`gh auth login` or macOS keychain) instead.
  3. Use a secret manager (GCP Secret Manager, since this deploys to Cloud Run) for production values.

### C2. OAuth client secret exposed in the frontend bundle
- **File:** `frontend/.env` (`VITE_CLIENT_SECRET=...`), also documented in `frontend/.env.example`
- All `VITE_*` variables are baked into the JavaScript bundle and shipped to every browser. A client secret in a SPA is public by definition. The PKCE flow already configured in `start.sh` makes the secret unnecessary.
- **Fix:** Delete `VITE_CLIENT_SECRET` from `frontend/.env` and `frontend/.env.example`; ensure the OAuth application is registered as a **public** client using PKCE; rotate the exposed secret.

### C3. Weak fallback secrets allow silent insecure deployment
- **Files:** `reminder_app/settings.py:30` (`SECRET_KEY` default `'change-me-please'`); `.env:35` (`WEBHOOK_TOKEN=secret-token-123-change-this-in-prod`); `settings.py:421-429` (field-encryption key derived from `SECRET_KEY` when unset)
- If env vars are missing in production, the app boots with a guessable `SECRET_KEY` (forgeable sessions, CSRF tokens, password-reset tokens) and a guessable webhook token (anyone can trigger reminder/task processing). The Fernet field-encryption key falls back to a hash of `SECRET_KEY`, so compromising one compromises encrypted Jira tokens too.
- **Fix:** Fail fast — remove the defaults and raise `ImproperlyConfigured` when `DEBUG=False` and any of `SECRET_KEY`, `WEBHOOK_TOKEN`, `FIELD_ENCRYPTION_KEY` is unset or equals a known placeholder.

---

## HIGH

### H1. Naive datetime in email-threshold check (timezone bug)
- **File:** `app/tasks.py:88` — `today = datetime.now().date()` (verified present)
- Uses naive system-local time while `reminder_start_date` is timezone-aware. Near midnight or on servers not in the project timezone, the daily email-threshold count is computed for the wrong day, producing missed or false admin alerts.
- **Fix:** `today = timezone.now().date()` (or `timezone.localdate()` if the intent is local-day semantics — pick one convention and apply it everywhere; see also M6).

### H2. SAML ACS multi-tenant IDOR risk
- **File:** `app/views.py:807+` (`sso_acs(request, company_id)`)
- The Assertion Consumer Service is selected purely by the `company_id` in the URL. A SAML response can be posted to another company's ACS endpoint, and JIT provisioning will create the user inside that company's tenant.
- **Fix:** Bind each company's SSO settings to its expected IdP entity ID and validate the response issuer against it; reject responses whose issuer doesn't match the company's configured IdP.

### H3. SAML JIT provisioning creates accounts with no email-domain restriction
- **File:** `app/views.py:830-865`
- Any email asserted by the IdP results in an auto-created account in the company, with no allowed-domain check and no admin notification.
- **Fix:** Restrict JIT provisioning to the company's verified email domains (the codebase already has an owner-domain concept — `setup_owner_domain.py`); log and alert on each JIT creation.

### H4. Password-reset token reuse race condition
- **File:** `app/views.py:1092-1114`
- One-time-use enforcement is `cache.get()` then `cache.set()` — not atomic, and dependent on Redis being up. Two concurrent requests can both consume the same token; with the local-memory cache fallback the token is effectively reusable.
- **Fix:** Use an atomic primitive — `cache.add(used_key, True, 3600)` returns False if the key exists (atomic in Redis), or persist consumed tokens in the database inside a transaction.

### H5. SAML metadata falls back to `http://localhost:8000`
- **File:** `app/sso.py:38-44`
- If the host can't be determined, the SP entity ID / ACS URL is generated as plain-HTTP localhost — silently broken (and non-HTTPS) SSO metadata in production.
- **Fix:** Raise an error instead of falling back; require an explicit configured base URL.

### H6. No rate limiting on webhook endpoints
- **File:** `app/views.py` (`process_tasks_webhook`, `process_reminders_webhook`, `fallback_notification_webhook`, `process_slack_pending_reminders_webhook`)
- Token-only auth with no throttle. A leaked/weak token (see C3) allows unbounded triggering of email sends and task processing — spam and resource-exhaustion DoS.
- **Fix:** Add per-IP rate limiting (same cache pattern already used for login) and use a high-entropy token.

### H7. Docker container runs as root
- **File:** `Dockerfile`
- No `USER` directive; gunicorn runs as root. A container escape or RCE gets root in the container.
- **Fix:** Create an unprivileged user and add `USER django` before `CMD`.

### H8. No Docker `HEALTHCHECK`
- **File:** `Dockerfile`
- The app exposes `/health/` (in `reminder_app/urls.py`) but the image defines no healthcheck, weakening rolling-deploy and crash-recovery behavior outside Cloud Run's own probes.
- **Fix:** Add `HEALTHCHECK ... CMD wget -q --spider http://localhost:8080/health/ || exit 1` (and configure Cloud Run startup/liveness probes against `/health/`).

### H9. `DEBUG=True` in the local `.env`
- **File:** `.env:3`
- If this file (or its values) is ever reused for a deployment, Django serves full stack traces, settings, and SQL to users, and several security settings (`SECURE_SSL_REDIRECT`, secure cookies) silently relax because they default off when `DEBUG=True`.
- **Fix:** Keep `DEBUG=False` as the default everywhere except an explicitly local override; add a startup assertion that refuses `DEBUG=True` when running under Cloud Run (`K_SERVICE` env var present).

---

## MEDIUM

### M1. Soft-delete is not atomic and reports fake results
- **File:** `app/models.py:202-206` (`Reminder.delete`)
- Check-then-save race on `is_deleted`, and the method always returns `(1, {...})` regardless of what happened.
- **Fix:** `updated = Reminder.objects.filter(pk=self.pk, is_deleted=False).update(is_deleted=True)` and return the real count.

### M2. N+1 queries in GraphQL reminder listings
- **File:** `app/schema.py` (`resolve_reminders` ~line 495)
- `select_related('company', 'created_by')` is present but M2M fields (`visible_to_groups`, `attachments`, `slack_users`) are resolved per-reminder.
- **Fix:** Add `.prefetch_related('visible_to_groups', 'attachments', 'slack_users')`.

### M3. Unvalidated `limit` arguments on GraphQL queries
- **File:** `app/schema.py` (e.g. `resolve_audit_logs` ~line 823)
- Caller-supplied `limit` is used directly in a queryset slice with no cap — `limit=999999` is a cheap DoS.
- **Fix:** Clamp: `limit = max(1, min(int(limit or 50), 1000))` on every limit-taking resolver.

### M4. Silent failure when `custom_repeat_days` is malformed
- **File:** `app/utils.py:1162` (inside `_schedule_next_reminder`)
- `int(d) for d in days.split(',')` raises `ValueError` on bad data; the broad `except Exception` at the end of the function swallows it, so the reminder silently stops recurring.
- **Fix:** Validate the day list explicitly (integers 0–6, non-empty) and log a specific error naming the reminder ID.

### M5. CSV/TXT uploads bypass content validation
- **File:** `app/views.py:630-683` (magic-byte validation)
- `.txt`/`.csv` are allowed with no content check: binary payloads can be uploaded with a `.txt` name, and CSV formula injection (`=`, `+`, `@`, `-` prefixes) is possible if files are re-exported to spreadsheet users.
- **Fix:** Reject null bytes in text uploads; sanitize or flag formula-prefixed CSV cells.

### M6. Inconsistent timezone conventions across task processing
- **Files:** `app/tasks.py:120` uses `timezone.localtime()`; most of the codebase uses `timezone.now()`; `tasks.py:88` uses naive `datetime.now()` (H1)
- Date-boundary queries (`reminder_start_date__date=today`) select different reminder sets depending on which convention runs. For a scheduling app this is a correctness landmine.
- **Fix:** Standardize on one convention (`timezone.now()` for instants, `timezone.localdate()` for "today") and document it.

### M7. Rate limiting silently disabled when cache is down
- **File:** `app/views.py:372-379` (login throttle)
- The login limiter trusts `cache.get()`; with Redis unavailable (or LocMem across multiple workers) brute-force protection quietly disappears. `X-Forwarded-For` is also trusted without proxy validation.
- **Fix:** Treat cache failure as throttled (fail closed) or add a DB-backed fallback; only honor `X-Forwarded-For` from the known proxy.

### M8. Attachment upload rejects superusers
- **File:** `app/views.py:732-737`
- Superusers with `company=None` get a 400 on upload, although they can create reminders — asymmetric permissions.
- **Fix:** Let superusers specify a company context on upload, or document the limitation.

### M9. Dead code: `check_domain_verification` calls `.apply_async` on a plain function
- **File:** `app/tasks.py:48-63`
- Never called anywhere; if it were, line 63 would crash (`AttributeError` — it's not a Celery task). The module comment says Celery tasks were removed but this remnant stayed.
- **Fix:** Delete the function.

---

## LOW

- **L1.** `app/views.py:1037-1039` — full password-reset links are written to logs when `DEBUG=True`. Log only a token hash.
- **L2.** `app/views.py:590-593` — bare `except Exception: pass` around role lookup hides corrupted-data errors; catch specifically and log.
- **L3.** `app/models.py:296` — redundant `from .models import UserRole` inside a method in the same module; remove.
- **L4.** `app/models.py:158-160` — `Reminder.is_active()` is unused (processing reads the `active` field directly) and its docstring doesn't match its behavior; rename to `is_before_end_date()` or wire it into processing.
- **L5.** `Dockerfile:19` — `pip install --upgrade pip` unpinned → non-reproducible builds; pin the pip version.
- **L6.** `.env` — stale commented-out Postgres DSN (with an old password) and placeholder Slack token (`xoxb-your-token-here`); clean up.
- **L7.** `frontend/.env.example:5` — documents `VITE_CLIENT_SECRET` as a value to set (see C2); remove the line.

---

## Verified non-issues / things done right

- `.env`, `db.sqlite3`, `media/`, and `staticfiles/` are **not** tracked in git (only `staticfiles/` sits untracked in the working tree — keep it that way).
- `_ensure_sender_name` exists at `app/utils.py:1345` — a draft finding that it was missing was checked and discarded.
- Security headers, HSTS, JWT rotation + blacklist, and production GraphQL introspection blocking are correctly configured in `settings.py`.
- All `app/*.py` files compile cleanly (`py_compile` passed); no syntax errors.

## Remediation priority

1. **Today:** Rotate every credential in C1/C2 (SendGrid, Twilio, Google OAuth, both GitHub PATs, `SECRET_KEY`); strip tokens from git remote URLs.
2. **Before next deploy:** C3 (fail-fast on placeholder secrets), H1 (timezone bug), H4 (reset-token race), H7/H8 (Docker user + healthcheck), H9 (DEBUG).
3. **This sprint:** H2/H3 (SAML tenant isolation + JIT restrictions), H5, H6, and the Medium items.
