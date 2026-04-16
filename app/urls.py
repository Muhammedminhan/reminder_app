from django.urls import path
from .views import (
    login_redirect,
    process_tasks_webhook,
    process_reminders_webhook,
    health_check,
    signup,
    login_password,
    mfa_verify,
    mfa_setup,
    mfa_confirm,
    fallback_notification_webhook,
    process_slack_pending_reminders_webhook,
    sso_login,
    sso_acs,
    sso_acs_legacy,
    sso_metadata,
    get_user_profile,
    index,
    robots_txt,
    forgot_password,
    reset_password,
    upload_profile_picture,
    upload_attachment,
    google_auth_init,
    google_auth_callback,
    serve_protected_media,
)

urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('', index, name='index'),
    path('login-redirect/', login_redirect, name='login-redirect'),
    path('webhook/process-tasks/', process_tasks_webhook, name='process-tasks-webhook'),
    path('webhook/process-reminders/', process_reminders_webhook, name='process-reminders-webhook'),
    path('webhook/fallback-notification/', fallback_notification_webhook, name='fallback-notification-webhook'),
    path('webhook/process-slack-pending/', process_slack_pending_reminders_webhook, name='process-slack-pending-reminders-webhook'),
    path('health/', health_check, name='health-check'),
    path('signup/', signup, name='signup'),
    # MFA endpoints
    path('login/password/', login_password, name='login-password'),
    path('mfa/verify/', mfa_verify, name='mfa-verify'),
    path('mfa/setup/', mfa_setup, name='mfa-setup'),
    path('mfa/confirm/', mfa_confirm, name='mfa-confirm'),
    # SSO endpoints
    path('sso/login/<str:domain>/', sso_login, name='sso_login'),
    path('sso/acs/<str:company_id>/', sso_acs, name='sso_acs'),
    path('sso/acs/', sso_acs_legacy, name='sso_acs_legacy'),
    path('sso/metadata/', sso_metadata, name='sso_metadata'),
    # User Profile
    path('user/profile/', get_user_profile, name='get-user-profile'),
    path('user/profile-picture/', upload_profile_picture, name='upload-profile-picture'),
    path('reminder/upload-attachment/', upload_attachment, name='upload-attachment'),
    # Password Reset
    path('auth/forgot-password/', forgot_password, name='forgot-password'),
    path('auth/reset-password/', reset_password, name='reset-password'),
    # Google OAuth2
    path('google/login/', google_auth_init, name='google-auth-init'),
    path('google/callback/', google_auth_callback, name='google-auth-callback'),
    # Media Serving (Protected)
    path('media/<path:path>/', serve_protected_media, name='serve-protected-media'),
]
