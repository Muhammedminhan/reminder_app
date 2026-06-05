# Multi-Tenant Domain Setup Guide

This guide explains how to set up the complete multi-tenant domain system for NotifyHub, where each user gets their own branded subdomain.

## Overview

The system creates the following domain structure:
- **Owner domain**: `notifyhub.fs.com` (your branded domain)
- **User domains**: `notifyhub.abc.com`, `notifyhub.gef.com`, etc. (each user's branded subdomain)

## Architecture

### Domain Flow
1. User logs in via the main Cloud Run URL
2. System redirects them to their branded subdomain (`notifyhub.{user_domain}`)
3. All subsequent access happens via their branded subdomain
4. Middleware handles subdomain detection and routing

### Components
- **SubdomainMiddleware**: Detects subdomain patterns and extracts customer domain
- **DomainVerificationMiddleware**: Ensures users complete domain verification before accessing features
- **TenantRedirectMiddleware**: Redirects authenticated users to their branded subdomain
- **GCP Domain Mappings**: Creates Cloud Run domain mappings for each subdomain
- **SendGrid Domain Authentication**: Handles email domain authentication

## Setup Steps

### 1. Environment Variables

Ensure these environment variables are set in your Cloud Run service:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_CLOUD_RUN_SERVICE=notifyhub
GCP_REGION=us-central1

# Domain Configuration
SUBDOMAIN_BRAND_PREFIX=notifyhub
USE_SUBDOMAIN_ONLY=true
FORCE_OVERRIDE_DOMAIN_MAPPING=true

# SendGrid Configuration
SENDGRID_API_KEY=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=tech-admin@ferryswiss.com

# Database Configuration (if using Cloud SQL)
DB_HOST=your-cloud-sql-host
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
```

### 2. Set Up Owner Domain

Create the domain mapping for your own branded domain:

```bash
python manage.py setup_owner_domain --domain fs.com --email your-email@fs.com
```

This will:
- Create a GCP domain mapping for `notifyhub.fs.com`
- Display the DNS records you need to add
- Send you an email with DNS setup instructions

### 3. Set Up Test User Domain

For testing, set up a test user domain:

```bash
python manage.py setup_multi_tenant --test-domain abc.com --test-email test@abc.com
```

**Prerequisites:**
- Create a user account for `test@abc.com`
- Create a `SendGridDomainAuth` instance for `abc.com` via the admin panel

### 4. DNS Configuration

Add the DNS records provided by the setup commands to your DNS provider:

#### For Owner Domain (fs.com)
```
Type: CNAME
Host: notifyhub
Value: ghs.googlehosted.com
```

#### For User Domains (abc.com, etc.)
```
Type: CNAME  
Host: notifyhub
Value: ghs.googlehosted.com
```

### 5. Cloud Scheduler Jobs

Set up these Cloud Scheduler jobs for automated verification:

#### Task Processing (every 5 minutes)
```bash
gcloud scheduler jobs create http process-tasks \
  --schedule="*/5 * * * *" \
  --uri="https://your-cloud-run-url/webhook/process-tasks/" \
  --http-method=POST \
  --oidc-service-account-email=your-service-account@your-project.iam.gserviceaccount.com
```

#### Reminder Processing (every minute)
```bash
gcloud scheduler jobs create http process-reminders \
  --schedule="* * * * *" \
  --uri="https://your-cloud-run-url/webhook/process-reminders/" \
  --http-method=POST \
  --oidc-service-account-email=your-service-account@your-project.iam.gserviceaccount.com
```

## User Workflow

### For New Users

1. **Registration**: User creates account via main Cloud Run URL
2. **Domain Setup**: User creates `SendGridDomainAuth` instance via admin panel
3. **DNS Instructions**: System sends email with DNS records to add
4. **Verification**: Automated system verifies domain and creates GCP mapping
5. **Redirect**: User is redirected to their branded subdomain (`notifyhub.{user_domain}`)

### For Existing Users

1. **Login**: User logs in via main Cloud Run URL
2. **Auto-redirect**: System automatically redirects to their branded subdomain
3. **Access**: All features accessible via their branded subdomain

## Testing

### Test Owner Domain
```bash
# Should redirect to notifyhub.fs.com
curl -I https://your-cloud-run-url/admin/
```

### Test User Domain
```bash
# Should redirect to notifyhub.abc.com
curl -I https://your-cloud-run-url/admin/ -H "Cookie: sessionid=user-session"
```

### Test Subdomain Access
```bash
# Should work directly
curl -I https://notifyhub.abc.com/admin/
```

## Troubleshooting

### Common Issues

1. **DNS not propagating**: Wait 5-15 minutes for DNS changes to propagate
2. **Domain mapping not ready**: Check GCP console for domain mapping status
3. **Redirect loops**: Ensure DNS records are correctly configured
4. **Email not sending**: Check SendGrid API key and sender verification

### Debug Commands

```bash
# Check domain mapping status
python manage.py shell
>>> from app.utils import check_gcp_domain_mapping_status
>>> result = check_gcp_domain_mapping_status('notifyhub.abc.com')
>>> print(result)

# Check SendGrid domain verification
>>> from app.utils import check_domain_verification_sync
>>> result = check_domain_verification_sync(domain_id)
>>> print(result)
```

### Logs

Check Cloud Run logs for detailed error messages:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

## Security Considerations

1. **HTTPS Only**: All domains use HTTPS with proper SSL certificates
2. **Domain Verification**: Users must verify domain ownership before access
3. **Subdomain Isolation**: Each user's subdomain is isolated
4. **CSRF Protection**: Proper CSRF tokens for all forms
5. **Session Security**: Secure session cookies with proper domain settings

## Monitoring

### Key Metrics to Monitor

1. **Domain Mapping Status**: Check GCP console for mapping readiness
2. **DNS Propagation**: Monitor DNS resolution for all subdomains
3. **Email Delivery**: Monitor SendGrid email delivery rates
4. **User Access**: Monitor successful logins and redirects
5. **Error Rates**: Monitor 500 errors and failed verifications

### Alerts to Set Up

1. **Domain Mapping Failures**: Alert when GCP domain mapping creation fails
2. **Email Delivery Failures**: Alert when DNS instruction emails fail
3. **High Error Rates**: Alert when error rates exceed threshold
4. **DNS Resolution Issues**: Alert when subdomains become unreachable

## Maintenance

### Regular Tasks

1. **Monitor Domain Mappings**: Check GCP console weekly for any failed mappings
2. **Update DNS Records**: Update DNS records if Cloud Run service changes
3. **Review Logs**: Weekly review of error logs and failed verifications
4. **Test User Flows**: Monthly testing of new user registration and domain setup

### Scaling Considerations

1. **Domain Limit**: GCP has limits on domain mappings per project
2. **DNS Propagation**: Large numbers of domains may have DNS propagation delays
3. **Email Rate Limits**: SendGrid has rate limits for email sending
4. **Database Performance**: Monitor database performance with many users

## Support

For issues with the multi-tenant setup:

1. Check the troubleshooting section above
2. Review Cloud Run logs for error details
3. Verify DNS configuration and propagation
4. Test with a simple domain first before complex setups
