"""
URL configuration for dummy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_otp.admin import OTPAdminSite
from django.contrib import admin
from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /adrian-holovaty/",
        "Disallow: /o/",
        "Disallow: /graphql/",
        "Disallow: /fix-oauth/",
        "Disallow: /health/",
        "",
        "Sitemap: https://notifyhub.example.com/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

# admin.site.__class__ = OTPAdminSite
admin.site.site_header = 'NotifyHub Administration'



def health_check(request):
    """Simple health check endpoint for Cloud Run"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'NotifyHub is running'
    })

def rate_limit_graphql(view_func):
    """Decorator to enforce rate limiting on GraphQL endpoint."""
    from app.utils import is_rate_limited
    def _wrapped_view(request, *args, **kwargs):
        if request.method == 'OPTIONS':
            return view_func(request, *args, **kwargs)
            
        # Allow 100 requests per minute per IP for the generic graphql endpoint
        if is_rate_limited(request, 'graphql_public', 100):
            return JsonResponse(
                {'errors': [{'message': '429 Too Many Requests. Please try again later.'}]}, 
                status=429
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def fix_oauth_view(request):
    """Temporary view to fix OAuth configuration and show errors"""
    from django.http import HttpResponse
    from oauth2_provider.models import Application
    from django.contrib.auth import get_user_model
    import traceback
    
    try:
        User = get_user_model()
        # Get first superuser
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            # Create one if missing
            try:
                user = User.objects.create_superuser('admin_fix', 'admin@example.com', 'admin123')
            except:
                return HttpResponse("Error: No superuser found and failed to create one.")

        import os
        from decouple import config
        # OWASP Best Practice: Remove hard-coded secrets, use environment variables
        client_id = config('OAUTH_CLIENT_ID', default=os.environ.get('OAUTH_CLIENT_ID', 'REDACTED_CLIENT_ID'))
        client_secret = config('OAUTH_CLIENT_SECRET', default=os.environ.get('OAUTH_CLIENT_SECRET', 'REDACTED_CLIENT_SECRET'))

        app, created = Application.objects.update_or_create(
            client_id=client_id,
            defaults={
                "user": user,
                "client_type": Application.CLIENT_PUBLIC,
                "authorization_grant_type": Application.GRANT_PASSWORD,
                "client_secret": client_secret,
                "name": "NotifyHub Frontend",
                "skip_authorization": True
            }
        )
        
        status = "Created" if created else "Updated"
        return HttpResponse(f"""
            <h1>✅ Success!</h1>
            <p>OAuth Application <strong>{status}</strong> successfully.</p>
            <p><strong>Client ID:</strong> {app.client_id}</p>
            <p><strong>Client Secret:</strong> (Configured)</p>
            <p>You can now authenticate.</p>
        """)
    except Exception as e:
        return HttpResponse(f"<h1>❌ Error Occurred</h1><pre>{traceback.format_exc()}</pre>")


from django.conf import settings
from django.conf.urls.static import static
from graphene_django.views import GraphQLView

urlpatterns = [
    path('adrian-holovaty/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),
    path('robots.txt', robots_txt),
    path('', include('app.urls')),
    path('fix-oauth/', fix_oauth_view),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


