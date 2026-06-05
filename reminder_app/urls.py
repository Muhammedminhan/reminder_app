"""
URL configuration for NotifyHub.
"""
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from graphene_django.views import GraphQLView


# ── robots.txt ──────────────────────────────────────────────────────────────
@require_GET
def robots_txt(request):
    host = request.get_host().split(':')[0]
    scheme = 'https' if request.is_secure() else 'http'
    lines = [
        "User-agent: *",
        "Disallow: /adrian-holovaty/",
        "Disallow: /o/",
        "Disallow: /graphql/",
        "Disallow: /health/",
        "",
        f"Sitemap: {scheme}://{host}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


# ── Health check ────────────────────────────────────────────────────────────
def health_check(request):
    """Simple health check endpoint for Cloud Run."""
    return JsonResponse({'status': 'healthy', 'message': 'NotifyHub is running'})


# ── GraphQL rate-limiting wrapper ────────────────────────────────────────────
def rate_limit_graphql(view_func):
    from app.utils import is_rate_limited

    def _wrapped_view(request, *args, **kwargs):
        if request.method == 'OPTIONS':
            return view_func(request, *args, **kwargs)
        if is_rate_limited(request, 'graphql_public', 100):
            return JsonResponse(
                {'errors': [{'message': '429 Too Many Requests. Please try again later.'}]},
                status=429,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# ── URL patterns ─────────────────────────────────────────────────────────────
admin.site.site_header = 'NotifyHub Administration'

urlpatterns = [
    path('adrian-holovaty/', admin.site.urls),
    # health/ and robots.txt are defined here; duplicates in app/urls.py are
    # intentionally removed so these canonical versions always win.
    path('health/', health_check, name='health_check'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path(
        'graphql/',
        csrf_exempt(
            rate_limit_graphql(
                GraphQLView.as_view(graphiql=settings.DEBUG)
            )
        ),
    ),
    path('', include('app.urls')),
    # /fix-oauth/ has been permanently removed — it exposed admin credentials
    # and OAuth secrets in plain HTML to unauthenticated requests.
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
