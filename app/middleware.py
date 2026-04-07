import uuid
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import SendGridDomainAuth
from django.conf import settings
from decouple import config

class SessionUUIDFixerMiddleware:
    """Ensures the user ID in the session is a valid UUID to avoid crashes when model expects UUID."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth import SESSION_KEY
        if hasattr(request, 'session'):
            user_id = request.session.get(SESSION_KEY)
            if user_id:
                try:
                    # Try to parse it as a UUID
                    uuid.UUID(str(user_id))
                except (ValueError, TypeError):
                    # Not a valid UUID (likely an old integer ID), clear session
                    request.session.flush()
        return self.get_response(request)

BRAND_PREFIX = getattr(settings, 'SUBDOMAIN_BRAND_PREFIX', 'notifyhub')
DISABLE_BRAND_REDIRECT = getattr(settings, 'DISABLE_BRAND_REDIRECT', False)
SENSITIVE_PREFIXES = ('/admin', '/adrian-holovaty', '/graphql', '/o/', '/health')

class SubdomainMiddleware:
    def __init__(self, get_response):  # Added initializer to comply with Django middleware contract
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]
        if host.startswith(f"{BRAND_PREFIX}."):
            request.customer_domain = host[len(BRAND_PREFIX) + 1:]
            request.brand_subdomain = True
        else:
            request.customer_domain = None
            request.brand_subdomain = False
        return self.get_response(request)


class DomainVerificationMiddleware:
    """Adds messages for Company Admins about domain verification state with session flags."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if not request.user.is_authenticated:
                return self.get_response(request)
            if request.user.is_superuser:
                return self.get_response(request)
        except Exception:
            # If user loading fails (e.g. invalid UUID in session), treat as unauthenticated
            from django.contrib.auth import logout
            try:
                logout(request)
            except Exception:
                pass
            return self.get_response(request)
        try:
            is_company_admin = request.user.groups.filter(name__iexact='Company Admin').exists()
        except Exception:
            is_company_admin = False
        if is_company_admin:
            try:
                domain_auth = (SendGridDomainAuth.objects
                               .filter(user__company_id=request.user.company_id)
                               .order_by('-is_verified')
                               .first())
                if not domain_auth:
                    if not request.session.get('domain_auth_notice_shown'):
                        messages.error(request, "Domain authentication not configured yet. A superuser must set it up.")
                        request.session['domain_auth_notice_shown'] = True
                        request.session.modified = True
                    request.session.pop('domain_unverified_notice_shown', None)
                elif not domain_auth.is_verified:
                    if not request.session.get('domain_unverified_notice_shown'):
                        messages.warning(request, f"Domain {domain_auth.domain} not verified yet. Superuser is handling verification.")
                        request.session['domain_unverified_notice_shown'] = True
                        request.session.modified = True
                    request.session.pop('domain_auth_notice_shown', None)
                else:
                    changed = False
                    for k in ('domain_auth_notice_shown', 'domain_unverified_notice_shown'):
                        if request.session.get(k):
                            request.session.pop(k, None)
                            changed = True
                    if changed:
                        request.session.modified = True
            except Exception:
                pass
        return self.get_response(request)


class TenantRedirectMiddleware:
    """
    Redirects authenticated users to their branded subdomain.
    Skips API endpoints to allow frontend integration.
    """
    # API endpoints that should never be redirected
    API_PREFIXES = [
        '/signup/',
        '/o/',  # OAuth endpoints
        '/graphql/',
        '/webhook/',
        '/health/',
        '/login/',
        '/mfa/',
        '/admin/',
        '/adrian-holovaty/',  # Admin URL
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if DISABLE_BRAND_REDIRECT:
            return self.get_response(request)
        path = request.path or ''
        
        # Skip redirects for API endpoints, static files, and admin
        if self._is_api_endpoint(path) or path.startswith('/static/') or path.startswith('/admin/'):
            return self.get_response(request)
        
        try:
            if not request.user.is_authenticated or request.user.is_superuser:
                return self.get_response(request)
        except Exception:
            return self.get_response(request)
        
        current_host = request.get_host().split(':')[0]
        if current_host.startswith(f"{BRAND_PREFIX}."):
            return self.get_response(request)
            
        try:
            domain_auth = SendGridDomainAuth.objects.filter(user=request.user).first()
            if not domain_auth or not domain_auth.domain:
                return self.get_response(request)
            if not domain_auth.is_verified:
                return self.get_response(request)
            target_host = f"{BRAND_PREFIX}.{domain_auth.domain}"
            if current_host != target_host:
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(f"https://{target_host}{request.get_full_path()}")
        except Exception:
            pass
        return self.get_response(request)

    def _is_api_endpoint(self, path):
        """Check if the request path is an API endpoint that should not be redirected."""
        return any(path.startswith(prefix) for prefix in self.API_PREFIXES)

    # def __call__(self, request):
    #     # Skip redirects for API endpoints
    #     if self._is_api_endpoint(request.path):
    #         return self.get_response(request)
    #
    #     # Only redirect authenticated non-superuser users
    #     if request.user.is_authenticated and not request.user.is_superuser:
    #         try:
    #             domain_auth = SendGridDomainAuth.objects.filter(user=request.user).first()
    #             if domain_auth and domain_auth.is_verified:
    #                 target_host = f"{BRAND_PREFIX}.{domain_auth.domain}" if domain_auth.domain else None
    #                 current_host = request.get_host().split(':')[0]
    #                 if target_host and current_host != target_host:
    #                     from django.http import HttpResponseRedirect
    #                     url = f"https://{target_host}{request.get_full_path()}"
    #                     return HttpResponseRedirect(url)
    #         except Exception:
    #             pass
    #     return self.get_response(request)


class MessageDedupMiddleware:
    """Server-side deduplication of Django messages (same level + text)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        storage = getattr(request, '_messages', None)
        if not storage:
            return response
        try:
            queued = getattr(storage, '_queued_messages', None)
            if queued is None:
                return response
            unique = []
            seen = set()
            for m in queued:
                key = (m.level, m.message.strip())
                if key in seen:
                    continue
                seen.add(key)
                unique.append(m)
            storage._queued_messages = unique
        except Exception:
            pass
        return response

class IndexBlockMiddleware:
    """Append X-Robots-Tag headers to block indexing of admin/sensitive pages and entire site if disabled or sandbox."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            allow = getattr(settings, 'ALLOW_INDEXING', False)
            sandbox = getattr(settings, 'IS_SANDBOX', False)
            # Force block in sandbox or for sensitive prefixes
            force_block = sandbox or any(request.path.startswith(p) for p in SENSITIVE_PREFIXES)
            if force_block or not allow:
                ctype = response.get('Content-Type', '')
                if any(t in ctype for t in ('text/html', 'application/json', 'text/plain')):
                    response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        except Exception:
            pass
        return response
