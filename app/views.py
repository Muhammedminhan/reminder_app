import uuid
from django.shortcuts import redirect, reverse
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .utils import process_scheduled_tasks, process_reminder_tasks
from django.utils import timezone
from .sso import SAMLHelper
from django.shortcuts import render, redirect, get_object_or_404
from .models import Reminder, Company, User, CompanySSOSettings
from .models import Reminder, SendGridDomainAuth
from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import authenticate
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import secrets
import requests
import logging
import json
import base64

logger = logging.getLogger(__name__)


def login_redirect(request):
    try:
        domain_auth = SendGridDomainAuth.objects.filter(user=request.user).first()
        if not domain_auth or not domain_auth.domain:
            return redirect('admin:app_sendgriddomainauth_add')

        # Extract the current company domain from the request host
        current_host = request.get_host()  # e.g., notifyhub.unilever.com
        # Remove the 'notifyhub.' prefix if present
        if current_host.startswith('notifyhub.'):
            current_company_domain = current_host[len('notifyhub.'):]
        else:
            current_company_domain = current_host

        # If the user's domain does not match the current company domain, redirect
        if current_company_domain != domain_auth.domain:
            correct_url = f"https://notifyhub.{domain_auth.domain}"
            return redirect(correct_url)

        # Otherwise, allow access as normal
        from decouple import config
        brand_prefix = config('SUBDOMAIN_BRAND_PREFIX', default='notifyhub')
        subdomain_url = f"https://{brand_prefix}.{domain_auth.domain}"
        return redirect(subdomain_url)
    except Exception:
        return redirect('admin:index')


@csrf_exempt
@require_http_methods(["POST"])
def process_tasks_webhook(request):
    """
    Webhook endpoint for processing scheduled tasks
    OWASP: Authenticated via X-Webhook-Token header.
    """
    token = request.headers.get('X-Webhook-Token')
    expected = getattr(settings, 'WEBHOOK_TOKEN', None)
    if expected and token != expected:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        process_scheduled_tasks()
        return JsonResponse({"status": "success", "message": "Tasks processed successfully"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def process_reminders_webhook(request):
    """
    Webhook endpoint for processing reminder tasks
    OWASP: Authenticated via X-Webhook-Token header.
    """
    token = request.headers.get('X-Webhook-Token')
    expected = getattr(settings, 'WEBHOOK_TOKEN', None)
    if expected and token != expected:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        result = process_reminder_tasks()
        return JsonResponse({
            "status": "success", 
            "message": f"Processed {result['processed']} reminders, {result['sent']} emails sent, {result['skipped_end_date']} skipped (past end date)"
        })
    except Exception as e:
        logger.error(f"Error processing reminders: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for Cloud Run
    """
    return JsonResponse({"status": "healthy", "timestamp": timezone.now().isoformat()})


@csrf_exempt
@require_http_methods(["POST"])
def fallback_notification_webhook(request):
    """
    Webhook endpoint for triggering fallback notification logic.
    Can be called by Cloud Scheduler or external cron jobs.
    """
    from .tasks import check_and_notify_admin_for_email_threshold
    try:
        check_and_notify_admin_for_email_threshold()
        return JsonResponse({"status": "success", "message": "Fallback notification logic executed."})
    except Exception as e:
        logger.error(f"Error in fallback notification webhook: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def signup(request):
    """
    REST endpoint for user signup with reCAPTCHA and rate limiting
    """
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        captcha_token = data.get('captcha_token')

        if not all([username, email, password]):
            return JsonResponse({
                'ok': False,
                'code': 'MISSING_FIELDS',
                'message': 'Username, email, and password are required'
            }, status=400)

        # Rate limiting
        if getattr(settings, 'RATE_LIMIT_ENABLED', True):
            try:
                # Use X-Forwarded-For for proxy-aware IP detection
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
                key = f"rl:signup:{ip}"
                attempts = cache.get(key, 0)
                if attempts >= getattr(settings, 'RATE_LIMIT_SIGNUP_PER_MINUTE', 3):
                    return JsonResponse({
                        'ok': False,
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Too many signup attempts, try again later'
                    }, status=429)
                cache.set(key, attempts + 1, timeout=60)
            except Exception:
                pass

        # --- Input Validation (OWASP: length limits, type checks) ---
        if len(username) > 150:
            return JsonResponse({'ok': False, 'code': 'INVALID_INPUT', 'message': 'Username too long (max 150 chars)'}, status=400)
        if len(email) > 254:
            return JsonResponse({'ok': False, 'code': 'INVALID_INPUT', 'message': 'Email too long (max 254 chars)'}, status=400)
        if len(password) < 8:
            return JsonResponse({'ok': False, 'code': 'INVALID_INPUT', 'message': 'Password must be at least 8 characters'}, status=400)
        if len(password) > 256:
            return JsonResponse({'ok': False, 'code': 'INVALID_INPUT', 'message': 'Password too long (max 256 chars)'}, status=400)
        # Basic email format check
        import re as _re
        if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return JsonResponse({'ok': False, 'code': 'INVALID_INPUT', 'message': 'Invalid email format'}, status=400)

        # reCAPTCHA verification if enabled
        if getattr(settings, 'RECAPTCHA_ENABLED', False):
            secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
            if not secret:
                return JsonResponse({
                    'ok': False,
                    'code': 'CAPTCHA_CONFIG_ERROR',
                    'message': 'Captcha verification misconfigured'
                }, status=500)
            if not captcha_token:
                return JsonResponse({
                    'ok': False,
                    'code': 'CAPTCHA_REQUIRED',
                    'message': 'Captcha token required'
                }, status=400)
            try:
                resp = requests.post(
                    'https://www.google.com/recaptcha/api/siteverify',
                    data={'secret': secret, 'response': captcha_token}, timeout=5
                )
                data = resp.json()
                if not data.get('success'):
                    return JsonResponse({
                        'ok': False,
                        'code': 'CAPTCHA_FAILED',
                        'message': 'Captcha verification failed'
                    }, status=400)
            except Exception:
                return JsonResponse({
                    'ok': False,
                    'code': 'CAPTCHA_FAILED',
                    'message': 'Captcha verification failed'
                }, status=400)
        
        # Create user
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'ok': False,
                'code': 'USERNAME_TAKEN',
                'message': 'Username already exists'
            }, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'ok': False,
                'code': 'EMAIL_TAKEN',
                'message': 'Email already exists'
            }, status=400)
        
        # Create a default company for the user
        from .models import Company
        company, created = Company.objects.get_or_create(
            name=f"{username}'s Company",
            defaults={'email': email}
        )
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            company=company
        )


        # Create default TOTP device and return provisioning info so frontend can show QR immediately
        otpauth_payload = {}
        try:
            from django_otp.plugins.otp_totp.models import TOTPDevice
            device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)
            try:
                secret_b32 = base64.b32encode(device.bin_key).decode('ascii').replace('=', '')
            except Exception:
                secret_b32 = base64.b32encode(device.key).decode('ascii').replace('=', '')
            otpauth_uri = _build_otpauth_uri(user.username, 'NotifyHub', secret_b32)
            otpauth_payload = {'otpauth_uri': otpauth_uri, 'secret': secret_b32}
            try:
                import qrcode
                import io
                img = qrcode.make(otpauth_uri)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                data_url = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
                otpauth_payload['qrcode_data_url'] = data_url
            except Exception:
                pass
        except Exception:
            logger.warning("TOTP device provisioning failed during signup", exc_info=True)

        response_payload = {
            'ok': True,
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'mfa': {
                'enrollment_required': True,
                **otpauth_payload
            }
        }

        return JsonResponse(response_payload, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'ok': False,
            'code': 'INVALID_JSON',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return JsonResponse({
            'ok': False,
            'code': 'INTERNAL_ERROR',
            'message': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def robots_txt(request):
    allow = getattr(settings, 'ALLOW_INDEXING', False)
    sandbox = getattr(settings, 'IS_SANDBOX', False)
    if sandbox:
        allow = False  # force block for sandbox
    if not allow:
        body = "User-agent: *\nDisallow: /\n"
    else:
        disallows = ['admin', 'adrian-holovaty', 'graphql', 'o', 'health']
        lines = ["User-agent: *"] + [f"Disallow: /{d}" for d in disallows]
        body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type='text/plain')


# ---- MFA (Password + TOTP) minimal endpoints ----

def _has_totp_enabled(user):
    try:
        from django_otp import devices_for_user  # type: ignore
        # Any confirmed TOTP device counts
        # Only require MFA if the user has a CONFIRMED device
        for dev in devices_for_user(user, confirmed=True):
            try:
                if getattr(dev, 'throttling_failure_count', None) is not None:
                    # Looks like a proper OTP device
                    return True
            except Exception:
                return True
        return False
    except Exception:
        # django-otp not installed or error; treat as not enabled
        return False

def _get_oauth_user(request):
    """
    Resolve authenticated user from OAuth2 Bearer token, similar to GraphQL helper.
    """
    try:
        from oauth2_provider.models import AccessToken
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        else:
            token = request.GET.get('token')

        with open('/tmp/auth_debug.log', 'a') as f:
            import datetime
            f.write(f"{datetime.datetime.now()} - Auth Check. Header: {auth_header[:20]}..., Token extracted: {token[:10] if token else 'None'}...\n")

        if token:
            at = AccessToken.objects.filter(token=token).first()
            if at:
                with open('/tmp/auth_debug.log', 'a') as f:
                    f.write(f"Match found! User: {at.user.username}\n")
                return at.user
            else:
                with open('/tmp/auth_debug.log', 'a') as f:
                    f.write(f"Token NOT found in DB: {token[:10]}...\n")
    except Exception as e:
        with open('/tmp/auth_debug.log', 'a') as f:
            f.write(f"Auth Error: {str(e)}\n")
    return None

def _build_otpauth_uri(username, issuer, secret_base32):
    """
    Build a standard otpauth:// URL the frontend can turn into a QR code.
    """
    from urllib.parse import quote
    label = f"{issuer}:{username}"
    return f"otpauth://totp/{quote(label)}?secret={secret_base32}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


@csrf_exempt
@require_http_methods(["POST"])
def login_password(request):
    """
    Step 1: verify username/password.
    Returns mfa_required and a short-lived challenge_id when TOTP is enabled.
    
    OWASP: Rate limited per IP (5 attempts/min). Inputs sanitized and length-bounded.
    """
    # --- Rate Limiting ---
    if getattr(settings, 'RATE_LIMIT_ENABLED', True):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
        rl_key = f"rl:login:{ip}"
        attempts = cache.get(rl_key, 0)
        limit = getattr(settings, 'RATE_LIMIT_LOGIN_PER_MINUTE', 5)
        if attempts >= limit:
            return JsonResponse({'ok': False, 'message': 'Too many login attempts, please try again later.'}, status=429)
        cache.set(rl_key, attempts + 1, 60)

    try:
        data = json.loads(request.body or "{}")
        username = str(data.get('username') or '').strip()
        password = str(data.get('password') or '')

        # --- Input Validation ---
        if not username or not password:
            return JsonResponse({'ok': False, 'message': 'username and password required'}, status=400)
        if len(username) > 150 or len(password) > 256:
            return JsonResponse({'ok': False, 'message': 'Input exceeds maximum allowed length'}, status=400)

        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({'ok': False, 'message': 'invalid credentials'}, status=401)
        if not user.is_active:
            return JsonResponse({'ok': False, 'message': 'user is inactive'}, status=403)
        if _has_totp_enabled(user):
            # Issue a short-lived challenge id
            challenge_id = secrets.token_urlsafe(16)
            cache.set(f"mfa:challenge:{challenge_id}", {'user_id': user.id}, timeout=120)
            return JsonResponse({'ok': True, 'mfa_required': True, 'mfa_challenge_id': challenge_id})
        # No MFA required
        return JsonResponse({'ok': True, 'mfa_required': False})
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'invalid json'}, status=400)
    except Exception as e:
        logger.error(f"login_password error: {e}")
        return JsonResponse({'ok': False, 'message': 'internal error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mfa_verify(request):
    """
    Step 2: verify TOTP against the challenge.
    On success, returns a short-lived mfa_token to be presented when requesting /o/token/.

    OWASP: Rate limited per IP (10 attempts/min) to prevent brute-force of TOTP codes.
    """
    # --- Rate Limiting ---
    if getattr(settings, 'RATE_LIMIT_ENABLED', True):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
        rl_key = f"rl:mfa_verify:{ip}"
        attempts = cache.get(rl_key, 0)
        if attempts >= 10:
            return JsonResponse({'ok': False, 'message': 'Too many attempts, please try again later.'}, status=429)
        cache.set(rl_key, attempts + 1, 60)

    try:
        data = json.loads(request.body or "{}")
        challenge_id = str(data.get('mfa_challenge_id') or '').strip()
        totp_code = str(data.get('totp_code', '')).strip()

        # --- Input Validation ---
        if not challenge_id or not totp_code:
            return JsonResponse({'ok': False, 'message': 'mfa_challenge_id and totp_code required'}, status=400)
        if len(challenge_id) > 64 or len(totp_code) > 8:
            return JsonResponse({'ok': False, 'message': 'Input exceeds maximum allowed length'}, status=400)
        if not totp_code.isdigit():
            return JsonResponse({'ok': False, 'message': 'totp_code must be numeric'}, status=400)

        entry = cache.get(f"mfa:challenge:{challenge_id}")
        if not entry or not entry.get('user_id'):
            return JsonResponse({'ok': False, 'message': 'challenge expired or invalid'}, status=400)
        user_id = entry['user_id']
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return JsonResponse({'ok': False, 'message': 'user not found'}, status=404)
        # Verify with django-otp
        try:
            from django_otp import devices_for_user  # type: ignore
            verified = False
            for device in devices_for_user(user, confirmed=True):
                try:
                    if device.verify_token(totp_code):
                        verified = True
                        break
                except Exception:
                    continue
            if not verified:
                return JsonResponse({'ok': False, 'message': 'invalid code'}, status=401)
        except Exception:
            return JsonResponse({'ok': False, 'message': 'TOTP not available on server'}, status=400)
        # Success: issue short-lived mfa_token
        signer = TimestampSigner()
        raw = secrets.token_urlsafe(24)
        signed = signer.sign(f"{user.id}:{raw}")
        cache.set(f"mfa:token:{raw}", {'user_id': user.id}, timeout=90)
        # Invalidate the challenge to prevent reuse
        cache.delete(f"mfa:challenge:{challenge_id}")
        return JsonResponse({'ok': True, 'mfa_token': signed})
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'invalid json'}, status=400)
    except Exception as e:
        logger.error(f"mfa_verify error: {e}")
        return JsonResponse({'ok': False, 'message': 'internal error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def mfa_setup(request):
    """
    Provide TOTP provisioning info for the authenticated user:
    - otpauth_uri (for QR generation)
    - secret (base32)
    Optionally, if 'qrcode' package is installed, return a data URL QR image.
    """
    try:
        user = _get_oauth_user(request)
        if not user:
            return JsonResponse({'ok': False, 'message': 'Authentication required'}, status=401)

        # Create or reuse a TOTP device (unconfirmed until user verifies)
        from django_otp.plugins.otp_totp.models import TOTPDevice
        device = TOTPDevice.objects.filter(user=user, name='default').first()
        if not device:
            device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)
        # Ensure device has a key; new TOTPDevice auto-generates key
        # Build otpauth URI
        issuer = 'NotifyHub'
        # device.key is bytes; convert to base32 (without padding)
        try:
            secret_b32 = base64.b32encode(device.bin_key).decode('ascii').replace('=', '')
        except Exception:
            # Fallback for older versions
            secret_b32 = base64.b32encode(device.key).decode('ascii').replace('=', '')
        otpauth_uri = _build_otpauth_uri(user.username, issuer, secret_b32)

        response = {'ok': True, 'otpauth_uri': otpauth_uri, 'secret': secret_b32}

        # Try optional QR generation
        try:
            import qrcode
            import io
            img = qrcode.make(otpauth_uri)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            data_url = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
            response['qrcode_data_url'] = data_url
        except Exception:
            # qrcode not installed or error; frontend can render QR from otpauth_uri
            pass

        return JsonResponse(response)
    except Exception as e:
        logger.error(f"mfa_setup error: {e}")
        return JsonResponse({'ok': False, 'message': 'internal error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mfa_confirm(request):
    """
    Confirm the user's TOTP device by verifying a first code and marking device confirmed.
    Body: { code: \"123456\" }
    """
    try:
        user = _get_oauth_user(request)
        if not user:
            return JsonResponse({'ok': False, 'message': 'Authentication required'}, status=401)
        data = json.loads(request.body or '{}')
        code = str(data.get('code', '')).strip()
        if not code:
            return JsonResponse({'ok': False, 'message': 'code required'}, status=400)

        from django_otp.plugins.otp_totp.models import TOTPDevice
        device = TOTPDevice.objects.filter(user=user, name='default').first()
        if not device:
            return JsonResponse({'ok': False, 'message': 'no device to confirm'}, status=400)
        if device.confirmed:
            return JsonResponse({'ok': True, 'already_confirmed': True})

        if device.verify_token(code):
            device.confirmed = True
            device.save()
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'message': 'invalid code'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'invalid json'}, status=400)
    except Exception as e:
        logger.error(f"mfa_confirm error: {e}")
        return JsonResponse({'ok': False, 'message': 'internal error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_profile(request):
    """
    Get the currently logged in user's profile data.
    """
    user = _get_oauth_user(request)
    if not user:
        if request.user.is_authenticated:
            user = request.user
        else:
            return JsonResponse({'ok': False, 'message': 'Authentication required'}, status=401)

    # Get role from user roles
    role_name = "User"
    # Check if user_roles relation exists and is valid
    try:
        user_role = user.user_roles.filter(is_active=True).first()
        if user_role:
            role_name = user_role.role.name
    except Exception:
        pass

    if role_name == "User":
        if user.is_superuser:
            role_name = "Super Admin"
        elif user.groups.filter(name__iexact='Company Admin').exists():
            role_name = "Company Admin"

    return JsonResponse({
        'ok': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role_name,
            'avatar': user.profile_picture.url if user.profile_picture else None,
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def upload_attachment(request):
    """
    Handle multi-part file upload for reminder attachments.
    Returns the attachment ID for use in the reminder creation mutation.
    """
    try:
        user = _get_oauth_user(request)
        if not user:
            return JsonResponse({'ok': False, 'message': 'Authentication required'}, status=401)
        
        if 'file' not in request.FILES:
            return JsonResponse({'ok': False, 'message': 'No file uploaded'}, status=400)
            
        uploaded_file = request.FILES['file']
        
        from .models import ReminderAttachment
        attachment = ReminderAttachment.objects.create(
            file=uploaded_file,
            filename=uploaded_file.name,
            file_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
            uploaded_by=user,
            company=user.company
        )
        
        return JsonResponse({
            'ok': True,
            'id': str(attachment.id),
            'filename': attachment.filename,
            'url': f"/media/{attachment.file.name}"
        })
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return JsonResponse({'ok': False, 'message': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def process_slack_pending_reminders_webhook(request):
    """Webhook to trigger sending Slack notifications for pending reminders.
    Intended to be called by a scheduler at 09:00 local time.
    """
    try:
        from .tasks import process_slack_pending_reminders
        result = process_slack_pending_reminders()
        status = 200 if result.get('ok') else 500
        return JsonResponse(result, status=status)
    except Exception as e:
        logger.error(f"process_slack_pending_reminders_webhook error: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# SSO Views

@csrf_exempt
def sso_login(request, domain):
    """Initiate SAML SSO flow for a company identified by domain (or slug)."""
    try:
        # In this implementation, we assume 'domain' parameter maps to Company domain or slug.
        # Adjust lookup as needed (e.g. Company.objects.get(slug=domain))
        company = get_object_or_404(Company, domain=domain)
        sso_settings = getattr(company, 'sso_settings', None)

        if not sso_settings or not sso_settings.is_enabled:
             return HttpResponseForbidden("SSO not enabled for this company.")

        req = SAMLHelper.get_saml_request(request)
        saml_settings = SAMLHelper.get_settings(sso_settings, host=request.get_host())
        auth = OneLogin_Saml2_Auth(req, saml_settings)

        # Determine redirect url after login (could be a parameter or default to dashboard)
        return_to = request.GET.get('next', '/')

        return redirect(auth.login(return_to=return_to))
    except Exception as e:
        logger.error(f"SSO Login Error: {e}")
        return HttpResponseServerError(f"SSO Error: {e}")

@csrf_exempt
def sso_acs(request, company_id):
    """SAML Assertion Consumer Service endpoint."""
    if not company_id:
        return HttpResponseBadRequest("Missing company identifier in ACS URL.")

    try:
        company = get_object_or_404(Company, pk=company_id)
        sso_settings = company.sso_settings

        req = SAMLHelper.get_saml_request(request)
        saml_settings = SAMLHelper.get_settings(sso_settings, host=request.get_host())
        auth = OneLogin_Saml2_Auth(req, saml_settings)

        auth.process_response()
        auth.process_response()
        errors = auth.get_errors()
        if errors:
            reason = auth.get_last_error_reason()
            logger.error(f"SAML Errors: {errors}, Reason: {reason}")
            return HttpResponseForbidden(f"SAML Error: {errors}. Reason: {reason}")

        if not auth.is_authenticated():
            return HttpResponseForbidden("SAML Authentication Failed.")

        # JIT Provisioning
        user_data = auth.get_attributes()
        # Expecting 'email' attribute. Adjust key based on IdP (e.g., 'http://schemas.xmlsoap.org/.../emailaddress')
        # Here we assume standard mapping or 'email'
        email_list = user_data.get('email') or user_data.get('User.Email') or user_data.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress')

        if not email_list:
             # Fallback to NameID if it looks like an email
             name_id = auth.get_nameid()
             if '@' in name_id:
                 email = name_id
             else:
                 return HttpResponseForbidden("No email attribute found in SAML Assertion.")
        else:
             email = email_list[0]

        # Login or Create User
        from django.contrib.auth import login
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            # Create new user
            username = email.split('@')[0]
            # Ensure unique username
            if User.objects.filter(username=username).exists():
                username = f"{username}_{uuid.uuid4().hex[:4]}"

            user = User.objects.create(
                username=username,
                email=email,
                company=company,
                # Set unusable password or random
            )
            user.set_unusable_password()
            user.save()
            logger.info(f"JIT Provisioning: Created user {user.username} for method SAML")
        else:
            # Optional: Ensure user belongs to this company?
            # For now, if email matches, we log them in.
            # If multi-company is strict, we might block if user.company != company
            pass

        # Backend must be specified for manual login
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Redirect to intended page or dashboard
        if 'RelayState' in request.POST and request.POST['RelayState'] != OneLogin_Saml2_Utils.get_self_url(req):
            return redirect(auth.redirect_to(request.POST['RelayState']))

        return redirect('/')

    except Exception as e:
        logger.error(f"SSO ACS Error: {e}")
        return HttpResponseServerError(f"SSO ACS Error: {e}")

@csrf_exempt
def sso_acs_legacy(request):
    """Fallback for old ACS URL to provide helpful error."""
    return HttpResponseBadRequest("SSO Configuration Error: You are posting to the old ACS URL (/sso/acs/). Please update your IdP (Okta) settings to use the new URL format: /sso/acs/[company_id]/ (e.g., /sso/acs/1/).")

def sso_metadata(request):
    """Expose SP Metadata XML."""
    # This might require context about which company we are generating metadata for,
    # OR we make generic metadata if we don't sign requests (but usually we need entityID).
    # IF specific entityID per company, we need company param.
    # For now, let's assume we pass ?company=ID similar to ACS, or we just error if not provided.
    company_id = request.GET.get('company')
    if not company_id:
        return HttpResponseBadRequest("Company ID required for metadata.")

    company = get_object_or_404(Company, pk=company_id)
    sso_settings = getattr(company, 'sso_settings', None)
    if not sso_settings:
        return HttpResponseNotFound("SSO not configured.")

    req = SAMLHelper.get_saml_request(request)
    saml_settings = SAMLHelper.get_settings(sso_settings, host=request.get_host())
    auth = OneLogin_Saml2_Auth(req, saml_settings)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        return HttpResponse(metadata, content_type='text/xml')
    else:
        return HttpResponseServerError(f"Metadata Error: {', '.join(errors)}")

def index(request):
    """Simple root view."""
    return HttpResponse("NotifyHub SSO Login Successful. Welcome!")

@csrf_exempt
@require_http_methods(["POST"])
def forgot_password(request):
    """
    REST endpoint to request password reset token.

    OWASP: Rate limited per IP (3/min). Always returns the same response to prevent
    email enumeration. Inputs are validated and length-bounded.
    """
    # --- Rate Limiting ---
    if getattr(settings, 'RATE_LIMIT_ENABLED', True):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
        rl_key = f"rl:forgot_pw:{ip}"
        attempts = cache.get(rl_key, 0)
        if attempts >= 3:
            # Still return success (don't reveal rate limit for this endpoint to avoid timing attacks)
            return JsonResponse({'ok': True, 'message': 'If an account exists with that email, a reset link has been sent.'})
        cache.set(rl_key, attempts + 1, 60)

    try:
        data = json.loads(request.body or "{}")
        email = str(data.get('email') or '').strip()

        # --- Input Validation ---
        if not email:
            return JsonResponse({'ok': False, 'message': 'Email is required'}, status=400)
        if len(email) > 254:
            return JsonResponse({'ok': False, 'message': 'Invalid email'}, status=400)

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        
        # Security: always return success to avoid email enumeration
        if user:
            signer = TimestampSigner()
            token = signer.sign(user.email)
            # Log the token so it can be used for testing
            logger.info(f"PASSWORD RESET REQUEST: User={user.username}, Email={email}")
            
            # Send email if SendGrid is configured
            reset_link = f"{request.scheme}://{request.get_host()}/reset-password?token={token}"
            try:
                from .utils import _send_html_email
                subject = "Reset your NotifyHub password"
                html = f"<p>You requested a password reset. Click the link below to set a new password:</p><p><a href='{reset_link}'>{reset_link}</a></p><p>This link will expire in 1 hour.</p>"
                _send_html_email(email, subject, html)
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")
            
            # Only log the link in DEBUG mode (never in production)
            if getattr(settings, 'DEBUG', False):
                logger.info("\n" + "="*50 + "\nPASSWORD RESET LINK (DEBUG ONLY):\n" + reset_link + "\n" + "="*50)

        return JsonResponse({'ok': True, 'message': 'If an account exists with that email, a reset link has been sent.'})
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return JsonResponse({'ok': False, 'message': 'Internal error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reset_password(request):
    """
    REST endpoint to reset password using a valid token.

    OWASP: Validates token signature and expiry. Enforces password length constraints.
    Rate limited per IP (5/min).
    """
    # --- Rate Limiting ---
    if getattr(settings, 'RATE_LIMIT_ENABLED', True):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown')).split(',')[0].strip()
        rl_key = f"rl:reset_pw:{ip}"
        attempts = cache.get(rl_key, 0)
        if attempts >= 5:
            return JsonResponse({'ok': False, 'message': 'Too many attempts, please try again later.'}, status=429)
        cache.set(rl_key, attempts + 1, 60)

    try:
        data = json.loads(request.body or "{}")
        token = str(data.get('token') or '').strip()
        new_password = str(data.get('password') or '')
        
        if not token or not new_password:
            return JsonResponse({'ok': False, 'message': 'Token and field password are required'}, status=400)

        # --- Input Validation ---
        if len(token) > 512:
            return JsonResponse({'ok': False, 'message': 'Invalid token'}, status=400)
        if len(new_password) < 8:
            return JsonResponse({'ok': False, 'message': 'Password must be at least 8 characters'}, status=400)
        if len(new_password) > 256:
            return JsonResponse({'ok': False, 'message': 'Password too long (max 256 chars)'}, status=400)
        
        signer = TimestampSigner()
        try:
            # Token valid for 1 hour
            email = signer.unsign(token, max_age=3600)
        except SignatureExpired:
            return JsonResponse({'ok': False, 'message': 'Token has expired'}, status=400)
        except BadSignature:
            return JsonResponse({'ok': False, 'message': 'Invalid token'}, status=400)
            
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return JsonResponse({'ok': False, 'message': 'User not found'}, status=404)
            
        user.set_password(new_password)
        user.save()
        
        logger.info(f"PASSWORD RESET SUCCESS: User={user.username}")
        return JsonResponse({'ok': True, 'message': 'Password has been reset successfully'})
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return JsonResponse({'ok': False, 'message': 'Internal error'}, status=500)


def get_authenticated_user_from_request(request):
    """Helper to get user from Bearer token in views"""
    from oauth2_provider.models import AccessToken
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        try:
            access_token = AccessToken.objects.get(token=token)
            if not access_token.is_expired():
                return access_token.user
        except AccessToken.DoesNotExist:
            pass
    return None


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def upload_profile_picture(request):
    """Handle profile picture upload or removal.

    OWASP: Rate limited per user (10/min). Validates file type by extension and content size.
    """
    user = get_authenticated_user_from_request(request)
    if not user:
        return JsonResponse({'ok': False, 'message': 'Authentication required'}, status=401)

    # --- Rate Limiting (per user ID, not just IP) ---
    if getattr(settings, 'RATE_LIMIT_ENABLED', True):
        rl_key = f"rl:profile_upload:{user.id}"
        attempts = cache.get(rl_key, 0)
        if attempts >= 10:
            return JsonResponse({'ok': False, 'message': 'Too many upload attempts, try again later.'}, status=429)
        cache.set(rl_key, attempts + 1, 60)
    if request.method == "DELETE":
        user.profile_picture = None
        user.save()
        return JsonResponse({'ok': True, 'message': 'Profile picture removed'})

    if 'profile_picture' not in request.FILES:
        logger.warning(f"Profile upload failed: 'profile_picture' not in request.FILES. Keys: {list(request.FILES.keys())}")
        return JsonResponse({'ok': False, 'message': 'No file provided'}, status=400)
    
    file = request.FILES['profile_picture']
    # Basic validation
    if not file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        logger.warning(f"Profile upload failed: Invalid file extension: {file.name}")
        return JsonResponse({'ok': False, 'message': 'Invalid file type. Please upload a PNG, JPG, or WEBP image.'}, status=400)
    
    # Align size limit with model's clean method (2MB)
    if file.size > 2 * 1024 * 1024:
        logger.warning(f"Profile upload failed: File too large: {file.size}")
        return JsonResponse({'ok': False, 'message': 'File too large (max 2MB)'}, status=400)

    try:
        user.profile_picture = file
        user.save()
        
        profile_picture_url = request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None
        
        return JsonResponse({
            'ok': True, 
            'message': 'Profile picture updated',
            'profile_picture_url': profile_picture_url
        })
    except Exception as e:
        logger.error(f"Profile picture save error: {str(e)}")
        # If it's a ValidationError, we might want to be more specific, but usually it's caught by clean() above
        return JsonResponse({'ok': False, 'message': f'Failed to save image: {str(e)}'}, status=400)


# ---- Google OAuth2 Integration ----

def google_auth_init(request):
    """Step 1: Redirect to Google's OAuth2 authorization URL"""
    from decouple import config
    import urllib.parse
    
    client_id = config('GOOGLE_CLIENT_ID', default='')
    if not client_id:
        return HttpResponseServerError("Google OAuth not configured (missing GOOGLE_CLIENT_ID)")
        
    # Use fixed backend URL from .env for redirect_uri stability
    backend_url = config('BACKEND_URL', default=request.build_absolute_uri('/')[:-1])
    redirect_uri = f"{backend_url.rstrip('/')}{reverse('google-auth-callback')}"
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'select_account'
    }
    
    google_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(google_url)


def google_auth_callback(request):
    """Step 2: Receive code from Google and exchange for user info"""
    from decouple import config
    from oauth2_provider.models import AccessToken, Application
    from datetime import timedelta
    from django.utils import timezone
    
    code = request.GET.get('code')
    if not code:
        return HttpResponseBadRequest("No authorization code received from Google")
        
    client_id = config('GOOGLE_CLIENT_ID', default='')
    client_secret = config('GOOGLE_CLIENT_SECRET', default='')
    backend_url = config('BACKEND_URL', default=request.build_absolute_uri('/')[:-1])
    redirect_uri = f"{backend_url.rstrip('/')}{reverse('google-auth-callback')}"
    
    # 1. Exchange code for tokens
    try:
        token_resp = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }, timeout=10)
        token_data = token_resp.json()
        
        if 'error' in token_data:
            return JsonResponse({'ok': False, 'error': token_data.get('error_description')}, status=400)
            
        access_token = token_data.get('access_token')
        
        # 2. Get User Info
        user_info_resp = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={
            'Authorization': f'Bearer {access_token}'
        }, timeout=10)
        user_info = user_info_resp.json()
        
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        
        # Fallback to full name if given_name/family_name are missing
        if not first_name and user_info.get('name'):
            name_parts = user_info.get('name', '').split(' ', 1)
            first_name = name_parts[0]
            if len(name_parts) > 1:
                last_name = name_parts[1]
        
        if not email:
            return JsonResponse({'ok': False, 'message': 'Google did not provide an email address'}, status=400)
            
        # 3. Find or Create User
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        
        if not user:
            # Create user and a default company
            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                username = f"{username}_{secrets.token_hex(3)}"
            
            from .models import Company
            company, _ = Company.objects.get_or_create(
                name=f"{first_name or username}'s Team",
                defaults={'email': email}
            )
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company
            )
            user.set_unusable_password()
        else:
            # Update existing user info from Google if missing
            updated = False
            if not user.first_name and first_name:
                user.first_name = first_name
                updated = True
            if not user.last_name and last_name:
                user.last_name = last_name
                updated = True
            if updated:
                user.save()
        
        user.save()
            
        # 4. Generate local AccessToken for the Frontend
        # Find the NotifyHub Frontend application
        app = Application.objects.filter(name="NotifyHub Frontend").first()
        if not app:
            # Fallback to any app or create one if debug
            app = Application.objects.first()
            
        if not app:
            return HttpResponseServerError("OAuth2 Application not configured. Please visit /fix-oauth/")
            
        # Create a new access token
        local_token = secrets.token_urlsafe(32)
        expires = timezone.now() + timedelta(days=30)
        
        AccessToken.objects.create(
            user=user,
            application=app,
            token=local_token,
            expires=expires,
            scope='read write'
        )
        
        # 5. Redirect back to frontend with the token
        frontend_url = config('FRONTEND_URL', default='http://localhost:5173')
        target_url = f"{frontend_url}/login?token={local_token}"
        return redirect(target_url)
        
    except Exception as e:
        logger.error(f"Google Callback Error: {str(e)}")
        return JsonResponse({'ok': False, 'message': 'Authentication failed during Google handshake'}, status=500)
def serve_protected_media(request, path):
    """
    Serve media files only to authenticated users.
    Ensures that profile pictures and other uploads are PRIVATE.
    """
    user = _get_oauth_user(request)
    if not user and not request.user.is_authenticated:
        return HttpResponseForbidden("Authentication required to view media.")

    import os
    from django.conf import settings
    from django.http import FileResponse, Http404
    
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Media file not found.")
        
    return FileResponse(open(file_path, 'rb'))
