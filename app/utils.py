# /reminder_app/app/utils.py

import random
import json
import string
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
import sendgrid
import requests
from django.utils import timezone
from decouple import config
import logging
from .models import Reminder, SendGridDomainAuth, ScheduledTask
from django.contrib import messages
from sendgrid.helpers.mail import Mail, Email, To, Content
# Corrected imports for GCP API interaction
import time
from .slack import send_dm_to_user, send_channel_message, SLACK_BOT_TOKEN

logger = logging.getLogger(__name__)

# SENDGRID settings with safe defaults
SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')
SENDGRID_BASE_URL = "https://api.sendgrid.com/v3"

HEADERS = {
    "Authorization": f"Bearer {SENDGRID_API_KEY}",
    "Content-Type": "application/json",
}

GCP_PROJECT_ID = config('GCP_PROJECT_ID', default='notifyhub-471315')
GCP_CLOUD_RUN_SERVICE = config('GCP_CLOUD_RUN_SERVICE', default='notifyhub')
GCP_REGION = config('GCP_REGION', default='us-central1')

SUBDOMAIN_BRAND_PREFIX = config('SUBDOMAIN_BRAND_PREFIX', default='notifyhub')
USE_SUBDOMAIN_ONLY = config('USE_SUBDOMAIN_ONLY', default=True, cast=bool)
FORCE_OVERRIDE_DOMAIN_MAPPING = config('FORCE_OVERRIDE_DOMAIN_MAPPING', default=True, cast=bool)
# New: allow forcing default sender to avoid unauthenticated branded domains
USE_BRANDED_SENDER = config('USE_BRANDED_SENDER', default=True, cast=bool)


def generate_unique_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=5))


def filter_company(request, qs):
    if request.user.is_superuser:
        return qs
    return qs.filter(company=request.user.company)


def set_company(request, obj):
    if not request.user.is_superuser:
        obj.company = request.user.company


def remove_company(request, fields):
    if not request.user.is_superuser:
        rem_fields = ['company']
        for field in rem_fields:
            try:
                fields.remove(field)
            except ValueError:
                pass
    return fields


def create_domain_authentication(domain: str, subdomain: str = "mail") -> dict:
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY environment variable is not set")

    url = f"{SENDGRID_BASE_URL}/whitelabel/domains"
    payload = {
        "domain": domain,
        "subdomain": subdomain,
        "automatic_security": True,
        "custom_spf": False,
        "default": False
    }

    logger.info(f"Making request to SendGrid API: {url}")
    logger.info(f"Payload: {payload}")

    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        logger.info(f"SendGrid API response status: {response.status_code}")

        if response.status_code != 201:
            error_text = response.text
            logger.error(f"SendGrid API error: {error_text}")
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response headers: {dict(response.headers)}")
            raise requests.exceptions.HTTPError(f"SendGrid API error: {response.status_code} - {error_text}")

        response_data = response.json()
        logger.info(f"SendGrid authentication successful for domain: {domain}")
        return response_data

    except requests.exceptions.Timeout:
        logger.error("SendGrid API request timed out")
        raise ValueError("SendGrid API request timed out. Please try again.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to SendGrid API: {e}")
        raise ValueError(f"Unable to connect to SendGrid API: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error to SendGrid API: {e}")
        raise ValueError(f"Error communicating with SendGrid API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in create_domain_authentication: {e}")
        raise


def create_domain_mapping_gcp(domain: str) -> dict:
    """
    Create Cloud Run Domain Mapping and return DNS records.
    Automatically retries with forceOverride if an existing mapping blocks creation.
    """
    try:
        from google.auth.transport.requests import AuthorizedSession
        import google.auth
        # Use cloud-platform scope for Cloud Run Admin API
        try:
            credentials, detected_project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        except Exception:
            credentials, detected_project = google.auth.default()
            try:
                credentials = credentials.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])
            except Exception:
                pass

        if not GCP_REGION or not GCP_CLOUD_RUN_SERVICE:
            return {"success": False, "error": "Missing GCP_REGION or GCP_CLOUD_RUN_SERVICE env vars"}

        project_id = GCP_PROJECT_ID or detected_project
        if not project_id:
            return {"success": False, "error": "Missing GCP_PROJECT_ID and default credentials project"}

        session = AuthorizedSession(credentials)
        parent = f"projects/{project_id}/locations/{GCP_REGION}"
        create_url = f"https://run.googleapis.com/v1/{parent}/domainmappings"

        body = {
            "apiVersion": "domains.cloudrun.com/v1",
            "kind": "DomainMapping",
            "metadata": {"name": domain},
            "spec": {"routeName": GCP_CLOUD_RUN_SERVICE}
        }

        def _extract_records() -> dict:
            get_url = f"https://run.googleapis.com/v1/projects/{project_id}/locations/{GCP_REGION}/domainmappings/{domain}"
            gcp_records = {}
            for _ in range(5):
                get_resp = session.get(get_url, timeout=30)
                if get_resp.status_code == 200:
                    mapping = get_resp.json()
                    records = mapping.get('status', {}).get('resourceRecords', [])
                    if records:
                        for record in records:
                            base_name = record.get('name')
                            key = base_name
                            if key in gcp_records:
                                idx = 2
                                while f"{base_name}-{idx}" in gcp_records:
                                    idx += 1
                                key = f"{base_name}-{idx}"
                            gcp_records[key] = {
                                "type": record.get('type'),
                                "host": record.get('name'),
                                "data": record.get('rrdata'),
                            }
                        break
                time.sleep(2)
            return gcp_records

        resp = session.post(create_url, json=body, timeout=30)
        logger.info(f"GCP create domain mapping status: {resp.status_code}")
        if resp.status_code in (200, 201):
            records = _extract_records()
            return {"success": True, "dns_records": records}

        # Handle conflict / already mapped
        if resp.status_code == 409:
            conflict_txt = resp.text.lower()
            logger.warning(f"Domain mapping conflict for {domain}: {resp.text}")
            # If force override allowed, retry with forceOverride query param
            if FORCE_OVERRIDE_DOMAIN_MAPPING:
                force_url = create_url + "?forceOverride=true"
                logger.info(f"Retrying domain mapping create for {domain} with forceOverride=true")
                force_resp = session.post(force_url, json=body, timeout=30)
                logger.info(f"Force override status: {force_resp.status_code}")
                if force_resp.status_code in (200, 201):
                    records = _extract_records()
                    return {"success": True, "dns_records": records, "forced": True}
                else:
                    # Fallback: attempt to fetch existing mapping in current region (maybe already ours)
                    existing = _extract_records()
                    if existing:
                        logger.info(f"Using existing mapping records for {domain} after failed force override")
                        return {"success": True, "dns_records": existing, "forced": False, "existing": True}
                    return {"success": False, "error": f"Force override failed HTTP {force_resp.status_code}: {force_resp.text}"}
            else:
                # If not forcing, attempt to fetch existing mapping (could be valid)
                existing = _extract_records()
                if existing:
                    return {"success": True, "dns_records": existing, "existing": True}
                return {"success": False, "error": f"Conflict (409): {resp.text}"}

        # Other failure
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        logger.warning(f"google-auth not available or error creating mapping: {e}")
        return {"success": False, "error": "google-auth not installed/configured or API error"}


def send_dns_instructions_email(to_email, domain, sendgrid_records, gcp_records):
    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY not set, cannot send DNS instructions email")
        return

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }

    from_email = config('DEFAULT_FROM_EMAIL', default='tech-admin@ferryswiss.com')

    logger.info(f"Using sender email: {from_email}")

    def format_records_html(records_dict):
        records_html = ""
        for record in records_dict.values():
            records_html += f"""
            <tr>
                <td>{record.get('type')}</td>
                <td>{record.get('host')}</td>
                <td>{record.get('data')}</td>
            </tr>
            """
        return records_html

    sendgrid_records_html = format_records_html(sendgrid_records)
    gcp_records_html = format_records_html(gcp_records)

    email_body = f"""
    <p>Dear Customer,</p>
    <p>Thank you for registering your domain <b>{domain}</b> with NotifyHub.</p>
    <p>To finalize the setup, you must add the following **DNS records** to your domain registrar or DNS service provider.</p>

    <h3>SendGrid DNS Records (for Email Authentication)</h3>
    <p>These records ensure your emails are delivered correctly and aren't marked as spam. You will typically add these as **CNAME** records.</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>Type</th><th>Host</th><th>Data</th></tr>
        {sendgrid_records_html}
    </table>
    <p style="margin-top: 10px;">
        After you've added these, we'll automatically check for verification. This may take some time (up to 48 hours) for DNS propagation.
    </p>

    <h3>Google Cloud DNS Records (for Custom Domain Mapping)</h3>
    <p>These records point your domain to your live NotifyHub service. You will typically add these as **A** and **AAAA** records.</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>Type</th><th>Host</th><th>Data</th></tr>
        {gcp_records_html}
    </table>
    <p style="margin-top: 10px;">
        After adding these, your application will become accessible at <b>https://{domain}</b> once the verification is complete.
    </p>

    <p>If you have any questions, please contact support.</p>
    <p>– The NotifyHub Team</p>
    """

    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "NotifyHub Team"},
        "subject": f"DNS Setup Instructions for {domain}",
        "content": [{"type": "text/html", "value": email_body}]
    }

    try:
        logger.info(f"Attempting to send email to {to_email} from {from_email}")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        logger.info(f"SendGrid response status: {response.status_code}")
        logger.info(f"SendGrid response body: {response.text}")
        if 200 <= response.status_code < 300:
            logger.info(f"Email sent successfully to {to_email}")
            return True
        logger.error(f"SendGrid Email Error: Status {response.status_code}")
        logger.error(f"SendGrid Error Response: {response.text}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while sending email to {to_email}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while sending email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending email to {to_email}: {e}")
        return False


def check_domain_verification_sync(domain_id):
    # Use SendGrid's validate endpoint to actively re-check DNS records
    url = f"https://api.sendgrid.com/v3/whitelabel/domains/{domain_id}/validate"
    headers = {
        "Authorization": f"Bearer {config('SENDGRID_API_KEY')}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=30)
        if response.status_code in [200, 201, 202]:
            data = response.json() if response.text else {}
            # The validate API usually returns { valid: bool, validation_results: {...} }
            valid = data.get("valid")
            if valid is None:
                # Fallback: some responses may wrap validity differently
                valid = data.get("domain", {}).get("valid", False)
            sendgrid_instance = SendGridDomainAuth.objects.get(domain_id=domain_id)
            sendgrid_instance.is_verified = bool(valid)
            sendgrid_instance.last_checked = timezone.now()
            sendgrid_instance.save()
            return {"success": True, "verified": bool(valid)}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_gcp_domain_mapping_status(domain):
    """
    Check Cloud Run Domain Mapping status and return readiness + DNS records.
    Uses projects/{project}/locations/{region}/domainmappings/{domain} (creation-matching) endpoint.
    Falls back to legacy namespaces path if primary returns 404 (for older regions / API behavior).
    """
    try:
        from google.auth.transport.requests import AuthorizedSession
        import google.auth
        try:
            credentials, detected_project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        except Exception:
            credentials, detected_project = google.auth.default()
            try:
                credentials = credentials.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])
            except Exception:
                pass
        project_id = GCP_PROJECT_ID or detected_project
        if not project_id:
            logger.warning(f"[GCP_STATUS] Missing project id for domain={domain}")
            return {"success": False, "error": "Missing GCP project id"}
        session = AuthorizedSession(credentials)
        # Primary (matches create endpoint)
        primary_url = f"https://run.googleapis.com/v1/projects/{project_id}/locations/{GCP_REGION}/domainmappings/{domain}"
        resp = session.get(primary_url, timeout=30)
        logger.debug(f"[GCP_STATUS] GET(primary) {primary_url} status={resp.status_code} domain={domain}")
        tried_legacy = False
        if resp.status_code == 404:
            # Legacy path fallback (older docs / internal representation)
            legacy_url = f"https://run.googleapis.com/apis/domains.cloudrun.com/v1/namespaces/{project_id}/domainmappings/{domain}"
            tried_legacy = True
            legacy_resp = session.get(legacy_url, timeout=30)
            logger.debug(f"[GCP_STATUS] GET(legacy) {legacy_url} status={legacy_resp.status_code} domain={domain}")
            if legacy_resp.status_code == 200:
                resp = legacy_resp
            else:
                snippet = (legacy_resp.text or '')[:300]
                logger.warning(f"[GCP_STATUS] 404 primary & legacy failure domain={domain} code={legacy_resp.status_code} body_snippet={snippet}")
                return {"success": False, "error": f"HTTP {legacy_resp.status_code}", "body": snippet}
        elif resp.status_code != 200:
            snippet = (resp.text or '')[:300]
            logger.warning(f"[GCP_STATUS] Non-200 primary domain={domain} code={resp.status_code} body_snippet={snippet}")
            return {"success": False, "error": f"HTTP {resp.status_code}", "body": snippet}
        mapping = resp.json()
        conditions = mapping.get('status', {}).get('conditions', [])
        is_ready = any(c.get('type') == 'Ready' and c.get('status') == 'True' for c in conditions)
        records = mapping.get('status', {}).get('resourceRecords', [])
        logger.debug(f"[GCP_STATUS] domain={domain} path={'legacy' if tried_legacy else 'primary'} is_ready={is_ready} cond_count={len(conditions)} records_count={len(records)}")
        gcp_records = {}
        for record in records:
            base_name = record.get('name')
            key = base_name
            if key in gcp_records:
                idx = 2
                while f"{base_name}-{idx}" in gcp_records:
                    idx += 1
                key = f"{base_name}-{idx}"
                logger.debug(f"[GCP_STATUS] Duplicate host normalized host={base_name} stored_as={key}")
            gcp_records[key] = {
                "type": record.get('type'),
                "host": record.get('name'),
                "data": record.get('rrdata'),
            }
        try:
            sendgrid_instance = SendGridDomainAuth.objects.get(domain=domain)
            sendgrid_instance.is_verified = is_ready
            sendgrid_instance.save(update_fields=['is_verified'])
        except Exception:
            pass
        return {"success": True, "is_ready": is_ready, "dns_records": gcp_records}
    except Exception as e:
        logger.exception(f"[GCP_STATUS] Exception checking mapping domain={domain} err={e}")
        return {"success": False, "error": str(e)}


def send_site_verification_email(to_email, domain, token):
    """Send instructions to add DNS TXT for Google Site Verification."""
    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY not set, cannot send site verification email")
        return False

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    from_email = config('DEFAULT_FROM_EMAIL', default='tech-admin@ferryswiss.com')

    txt_name = domain.strip('.')
    txt_value = f"google-site-verification={token}"

    html = f"""
    <p>Please verify ownership of <b>{domain}</b> to enable domain mapping.</p>
    <p>Add the following DNS TXT record at your DNS provider, then reply to this email or wait for auto-verification:</p>
    <table border="1" cellpadding="5" cellspacing="0">
      <tr><th>Type</th><th>Host</th><th>Value</th></tr>
      <tr><td>TXT</td><td>{txt_name}</td><td>{txt_value}</td></tr>
    </table>
    <p>After propagation, we will automatically complete the setup and send you the domain mapping DNS records.</p>
    """

    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "NotifyHub Team"},
        "subject": f"Verify domain ownership for {domain}",
        "content": [{"type": "text/html", "value": html}]
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        return 200 <= resp.status_code < 300
    except Exception as e:
        logger.error(f"Failed to send site verification email: {e}")
        return False


def request_site_verification_token(domain: str) -> dict:
    """Request a DNS_TXT token via Google Site Verification API."""
    try:
        from google.auth.transport.requests import AuthorizedSession
        import google.auth
        # Use siteverification scope
        try:
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/siteverification'])
        except Exception:
            credentials, _ = google.auth.default()
            try:
                credentials = credentials.with_scopes(['https://www.googleapis.com/auth/siteverification'])
            except Exception:
                pass
        session = AuthorizedSession(credentials)

        api_url = "https://www.googleapis.com/siteVerification/v1/token"
        body = {
            "site": {"identifier": domain, "type": "INET_DOMAIN"},
            "verificationMethod": "DNS_TXT"
        }
        resp = session.post(api_url, json=body, timeout=30)
        if resp.status_code not in (200, 201):
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        data = resp.json()
        return {"success": True, "token": data.get("token"), "method": data.get("method", "DNS_TXT")}
    except Exception as e:
        logger.warning(f"Site verification token request failed: {e}")
        return {"success": False, "error": str(e)}


def attempt_site_verification(domain: str) -> dict:
    """Attempt to verify the domain via Site Verification API (DNS_TXT)."""
    try:
        from google.auth.transport.requests import AuthorizedSession
        import google.auth
        # Use siteverification scope

        try:
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/siteverification'])
        except Exception:
            credentials, _ = google.auth.default()
            try:
                credentials = credentials.with_scopes(['https://www.googleapis.com/auth/siteverification'])
            except Exception:
                pass
        session = AuthorizedSession(credentials)

        api_url = "https://www.googleapis.com/siteVerification/v1/webResource?verificationMethod=DNS_TXT"
        body = {"site": {"identifier": domain, "type": "INET_DOMAIN"}}
        resp = session.post(api_url, json=body, timeout=30)
        if resp.status_code in (200, 201):
            resource = resp.json()
            return {"success": True, "resourceId": resource.get("id")}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        logger.warning(f"Site verification attempt failed: {e}")
        return {"success": False, "error": str(e)}


def _records_table(rows_dict):
    html = "<table border='1' cellpadding='5' cellspacing='0'><tr><th>Type</th><th>Host</th><th>Value</th></tr>"
    for rec in rows_dict.values():
        html += f"<tr><td>{rec.get('type')}</td><td>{rec.get('host')}</td><td>{rec.get('data')}</td></tr>"
    html += "</table>"
    return html


def send_initial_domain_setup_email(to_email, domain, sendgrid_records, site_token):
    if not SENDGRID_API_KEY:
        return False
    txt_record = {
        domain: {
            "type": "TXT",
            "host": domain,
            "data": f"google-site-verification={site_token}" if site_token else "(pending)"
        }
    }
    sendgrid_table = _records_table(sendgrid_records)
    txt_table = _records_table(txt_record)
    body = f"""
    <p>Welcome – let's set up your domain <b>{domain}</b>.</p>
    <h3>Step 1: Add Google Site Verification TXT Record</h3>
    {txt_table}
    <p>Add this TXT record at your DNS provider. This proves ownership so we can create the Cloud Run domain mapping.</p>
    <h3>Step 2: Add SendGrid Authentication Records (improves email deliverability)</h3>
    {sendgrid_table}
    <p>After propagation we'll verify automatically. When ownership is confirmed you'll get a second email with ALL Cloud Run domain mapping A / AAAA records (usually 8).</p>
    <p>No action needed yet for the application routing records. Wait for the next email.</p>
    <p>– NotifyHub</p>
    """
    return _send_html_email(to_email, f"Initial DNS Setup for {domain}", body)


def send_gcp_mapping_dns_email(to_email, domain, gcp_records):
    if not SENDGRID_API_KEY:
        logger.error(f"[GCP_DNS_EMAIL] SENDGRID_API_KEY missing; abort send for domain={domain} to={to_email}")
        return False
    record_count = len(gcp_records)
    record_types = {v.get('type','').upper() for v in gcp_records.values() if v.get('type')}
    logger.debug(
        f"[GCP_DNS_EMAIL] Preparing email domain={domain} to={to_email} count={record_count} types={sorted(record_types)} records_keys={list(gcp_records.keys())}"
    )
    table = _records_table(gcp_records)
    # Dynamic wording: detect record types
    if record_types and record_types.issubset({'CNAME'}):
        intro = f"Add the following Cloud Run domain mapping DNS record for <b>{domain}</b>:"
        scenario = 'CNAME_ONLY'
    else:
        intro = f"Add ALL the following Cloud Run domain mapping DNS records for <b>{domain}</b>:"
        scenario = 'MIXED_OR_A_AAAA'
    logger.info(f"[GCP_DNS_EMAIL] Sending DNS mapping email scenario={scenario} domain={domain} to={to_email} count={record_count}")
    body = f"""
    <p>{intro}</p>
    {table}
    <p>After propagation the mapping will become active. You'll receive a final confirmation when it's ready.</p>
    <p>– NotifyHub</p>
    """
    sent = _send_html_email(to_email, f"Cloud Run Domain Mapping DNS Records for {domain}", body)
    logger.info(f"[GCP_DNS_EMAIL] Send status domain={domain} to={to_email} success={sent}")
    return sent


def send_mapping_ready_email(to_email, domain):
    if not SENDGRID_API_KEY:
        logger.error(f"[MAPPING_READY_EMAIL] SENDGRID_API_KEY missing; abort send for domain={domain} to={to_email}")
        return False
    logger.debug(f"[MAPPING_READY_EMAIL] Preparing ready email domain={domain} to={to_email}")
    service_url = f"https://{domain}"
    body = f"""
    <p>Your domain mapping is now <b>READY</b>.</p>
    <p><b>Service URL:</b> <a href='{service_url}' target='_blank'>{service_url}</a></p>
    <p>You can start using this domain immediately for all application access.</p>
    <p>Keep this URL handy. If you set up both apex and subdomain variants, the branded subdomain will also work.</p>
    <p>– NotifyHub</p>
    """
    sent = _send_html_email(to_email, f"Domain Mapping Active for {domain}", body)
    logger.info(f"[MAPPING_READY_EMAIL] Send status domain={domain} to={to_email} success={sent}")
    return sent


def _send_html_email(to_email, subject, html):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"}
    from_email = config('DEFAULT_FROM_EMAIL', default='tech-admin@ferryswiss.com')
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "NotifyHub Team"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}]
    }
    try:
        logger.debug(f"Sending email via SendGrid: to={to_email} subject='{subject}'")
        r = requests.post(url, headers=headers, json=data, timeout=30)
        if 200 <= r.status_code < 300:
            logger.info(f"Email sent successfully: to={to_email} subject='{subject}' status={r.status_code}")
            return True
        snippet = (r.text or '')[:300]
        logger.warning(f"Email send failed: to={to_email} subject='{subject}' status={r.status_code} body_snippet={snippet}")
        return False
    except Exception as e:
        logger.error(f"Exception sending email to={to_email} subject='{subject}': {e}")
        return False


# Helper to isolate mapping DNS records from merged set (exclude SendGrid auth records)
def _extract_mapping_records(merged_dict, mapping_domain):
    prefix = f"{mapping_domain}|"
    return {k: v for k, v in merged_dict.items() if k.startswith(prefix)}


# Polling / scheduling interval configuration (minutes) with faster defaults
SITE_VERIFICATION_INITIAL_DELAY_MIN = int(config('SITE_VERIFICATION_INITIAL_DELAY_MIN', default=5))  # was 10
SITE_VERIFICATION_RETRY_DELAY_MIN = int(config('SITE_VERIFICATION_RETRY_DELAY_MIN', default=15))     # was 30
GCP_MAPPING_INITIAL_DELAY_MIN = int(config('GCP_MAPPING_INITIAL_DELAY_MIN', default=5))             # was 5
GCP_MAPPING_RETRY_DELAY_MIN = int(config('GCP_MAPPING_RETRY_DELAY_MIN', default=10))                # was 30
GCP_MAPPING_PARTIAL_RETRY_DELAY_MIN = int(config('GCP_MAPPING_PARTIAL_RETRY_DELAY_MIN', default=3))  # new faster retry for partial sets
FULL_GCP_RECORD_THRESHOLD = int(config('FULL_GCP_RECORD_THRESHOLD', default=8))
GCP_MIN_RECORD_THRESHOLD = int(config('GCP_MIN_RECORD_THRESHOLD', default=1))  # minimal viable count
GCP_FALLBACK_ATTEMPTS = int(config('GCP_FALLBACK_ATTEMPTS', default=2))  # after N polls fallback send


def process_scheduled_tasks():
    now = timezone.now()
    due_tasks = ScheduledTask.objects.filter(
        scheduled_at__lte=now,
        is_completed=False
    )

    for task in due_tasks:
        try:
            if task.task_type == 'domain_verification':
                domain_id = task.task_data.get('domain_id')
                if domain_id:
                    result = check_domain_verification_sync(domain_id)
                    if result['success'] and result['verified']:
                        task.is_completed = True
                        task.executed_at = timezone.now()
                        task.save()
                    else:
                        task.scheduled_at = timezone.now() + timedelta(hours=1)
                        task.save()
            elif task.task_type == 'gcp_domain_mapping_verification':
                domain = task.task_data.get('domain')
                if domain:
                    attempts = task.task_data.get('attempts', 0) + 1
                    logger.debug(f"[GCP_VERIFY_TASK] Start domain={domain} attempt={attempts}")
                    task.task_data['attempts'] = attempts
                    task.save(update_fields=['task_data'])
                    gcp_current = {}
                    result = check_gcp_domain_mapping_status(domain)
                    logger.debug(f"[GCP_VERIFY_TASK] Status result domain={domain} success={result.get('success')} ready={result.get('is_ready')} records={len((result.get('dns_records') or {}))}")
                    if not result.get('success'):
                        # Failure path: schedule retry with normal retry delay to avoid tight loop
                        err = result.get('error')
                        body = result.get('body')
                        logger.warning(f"[GCP_VERIFY_TASK] Status fetch failed domain={domain} attempt={attempts} error={err} body_snippet={body}")
                        task.scheduled_at = timezone.now() + timedelta(minutes=GCP_MAPPING_RETRY_DELAY_MIN)
                        task.save(update_fields=['scheduled_at'])
                        continue
                    # Success branch
                    new_gcp = result.get('dns_records') or {}
                    try:
                        base_domain = domain
                        branded_prefix = f"{SUBDOMAIN_BRAND_PREFIX}."
                        if base_domain.startswith(branded_prefix):
                            base_domain = base_domain[len(branded_prefix):]
                        instance = SendGridDomainAuth.objects.get(domain=base_domain)
                        existing = instance.dns_records or {}
                        logger.debug(f"[GCP_VERIFY_TASK] Merge existing_count={len(existing)} new_count={len(new_gcp)} domain={domain} base={base_domain}")
                        namespaced = {}
                        for k, v in new_gcp.items():
                            ns_key = f"{domain}|{k}" if '|' not in k else k
                            namespaced[ns_key] = v
                        merged = existing.copy()
                        merged.update(namespaced)
                        instance.dns_records = merged
                        # Only mapping records (namespaced) for this domain
                        mapping_prefix = f"{domain}|"
                        gcp_current = {k: v for k, v in merged.items() if k.startswith(mapping_prefix) and str(v.get('type', '')).upper() in ('A', 'AAAA')}
                        gcp_any_mapping = {k: v for k, v in merged.items() if k.startswith(mapping_prefix) and v.get('type')}
                        # Counts including SendGrid (for diagnostics) vs filtered
                        total_any = sum(1 for v in merged.values() if v.get('type'))
                        logger.debug(
                            f"[GCP_VERIFY_TASK] Counts domain={domain} mapping_A_AAAA={len(gcp_current)} mapping_ANY={len(gcp_any_mapping)} total_ANY_all_sources={total_any} threshold_full={FULL_GCP_RECORD_THRESHOLD} email_sent={instance.gcp_records_email_sent}"
                        )
                        if (not instance.gcp_records_email_sent) and len(gcp_current) >= FULL_GCP_RECORD_THRESHOLD:
                            logger.info(f"[GCP_VERIFY_TASK] Full threshold met sending consolidated domain={domain} base={base_domain}")
                            email_records = {}
                            for nk, nv in gcp_current.items():
                                parts = nk.split('|',1)
                                display_key = parts[1] if len(parts)==2 else nk
                                email_records[display_key] = nv
                            sent_ok = send_gcp_mapping_dns_email(instance.user.email, base_domain, email_records)
                            logger.info(f"[GCP_VERIFY_TASK] Consolidated send result={sent_ok} base={base_domain}")
                            if sent_ok:
                                instance.gcp_records_email_sent = True
                        elif not instance.gcp_records_email_sent:
                            if len(gcp_current) == 0 and len(gcp_any_mapping) >= GCP_MIN_RECORD_THRESHOLD:
                                logger.info(f"[GCP_VERIFY_TASK] CNAME-only mapping scenario triggering send domain={domain} base={base_domain} mapping_any_count={len(gcp_any_mapping)}")
                                email_records = {}
                                for nk, nv in gcp_any_mapping.items():
                                    parts = nk.split('|',1)
                                    display_key = parts[1] if len(parts)==2 else nk
                                    email_records[display_key] = nv
                                sent_ok = send_gcp_mapping_dns_email(instance.user.email, base_domain, email_records)
                                logger.info(f"[GCP_VERIFY_TASK] CNAME-only mapping send result={sent_ok} base={base_domain}")
                                if sent_ok:
                                    instance.gcp_records_email_sent = True
                            else:
                                fallback_condition = attempts >= GCP_FALLBACK_ATTEMPTS and (len(gcp_current) >= GCP_MIN_RECORD_THRESHOLD or (len(gcp_current) == 0 and len(gcp_any_mapping) >= GCP_MIN_RECORD_THRESHOLD))
                                logger.debug(f"[GCP_VERIFY_TASK] Fallback eval domain={domain} attempts={attempts} fallback_condition={fallback_condition}")
                                if fallback_condition:
                                    effective_records = gcp_current if len(gcp_current) > 0 else gcp_any_mapping
                                    logger.warning(f"[GCP_VERIFY_TASK] Fallback send domain={domain} base={base_domain} mapping_A_AAAA={len(gcp_current)} mapping_ANY={len(gcp_any_mapping)} using={'A/AAAA' if effective_records is gcp_current else 'MAPPING_ANY'} attempts={attempts}")
                                    email_records = {}
                                    for nk, nv in effective_records.items():
                                        parts = nk.split('|',1)
                                        display_key = parts[1] if len(parts)==2 else nk
                                        email_records[display_key] = nv
                                    sent_ok = send_gcp_mapping_dns_email(instance.user.email, base_domain, email_records)
                                    logger.info(f"[GCP_VERIFY_TASK] Fallback send result={sent_ok} base={base_domain}")
                                    if sent_ok:
                                        instance.gcp_records_email_sent = True
                        if result.get('is_ready') and not instance.mapping_ready_email_sent:
                            target_domain = f"{SUBDOMAIN_BRAND_PREFIX}.{base_domain}" if USE_SUBDOMAIN_ONLY else base_domain
                            logger.info(f"[GCP_VERIFY_TASK] Mapping reported READY attempting ready email domain={target_domain} base={base_domain}")
                            sent_ok = send_mapping_ready_email(instance.user.email, target_domain)
                            logger.info(f"[GCP_VERIFY_TASK] Ready email result={sent_ok} base={base_domain}")
                            if sent_ok:
                                instance.mapping_ready_email_sent = True
                                instance.is_verified = True
                        instance.save()
                    except Exception as me:
                        logger.exception(f"[GCP_VERIFY_TASK] Exception during merge/send domain={domain} err={me}")
                    # Reschedule or complete
                    try:
                        base_domain = domain
                        branded_prefix = f"{SUBDOMAIN_BRAND_PREFIX}."
                        if base_domain.startswith(branded_prefix):
                            base_domain = base_domain[len(branded_prefix):]
                        instance = SendGridDomainAuth.objects.get(domain=base_domain)
                        complete_condition = result.get('is_ready') and instance.mapping_ready_email_sent
                        logger.debug(f"[GCP_VERIFY_TASK] Completion eval domain={domain} ready={result.get('is_ready')} ready_email_sent={instance.mapping_ready_email_sent} complete={complete_condition}")
                        if complete_condition:
                            task.is_completed = True
                            task.executed_at = timezone.now()
                            task.save()
                            logger.info(f"[GCP_VERIFY_TASK] Task completed domain={domain}")
                        else:
                            if len(gcp_current) < FULL_GCP_RECORD_THRESHOLD:
                                delay = GCP_MAPPING_PARTIAL_RETRY_DELAY_MIN
                            else:
                                delay = GCP_MAPPING_RETRY_DELAY_MIN
                            task.scheduled_at = timezone.now() + timedelta(minutes=delay)
                            task.save()
                            logger.debug(f"[GCP_VERIFY_TASK] Rescheduled domain={domain} delay_min={delay}")
                    except Exception as re:
                        logger.exception(f"[GCP_VERIFY_TASK] Reschedule fallback exception domain={domain} err={re}")
                        task.scheduled_at = timezone.now() + timedelta(minutes=GCP_MAPPING_RETRY_DELAY_MIN)
                        task.save()
            elif task.task_type == 'site_verification':
                domain = task.task_data.get('domain')
                if not domain:
                    task.is_completed = True
                    task.executed_at = timezone.now()
                    task.save()
                    continue
                verify = attempt_site_verification(domain)
                if verify.get('success'):
                    try:
                        instance = SendGridDomainAuth.objects.get(domain=domain)
                        instance.site_verified = True
                        instance.site_verified_at = timezone.now()
                        instance.save()
                        # Decide which domain(s) to map
                        mapping_targets = []
                        branded_fqdn = f"{SUBDOMAIN_BRAND_PREFIX}.{domain}"
                        if USE_SUBDOMAIN_ONLY:
                            mapping_targets.append(branded_fqdn)
                        else:
                            mapping_targets.extend([domain, branded_fqdn])
                        # Create mappings
                        for m_domain in mapping_targets:
                            mapping_create = create_domain_mapping_gcp(m_domain)
                            if mapping_create.get('success'):
                                initial_gcp = mapping_create.get('dns_records') or {}
                                if initial_gcp:
                                    # namespace keys by mapping domain
                                    namespaced = {}
                                    for k, v in initial_gcp.items():
                                        ns_key = f"{m_domain}|{k}" if '|' not in k else k
                                        namespaced[ns_key] = v
                                    merged = {**(instance.dns_records or {}), **namespaced}
                                    instance.dns_records = merged
                                    gcp_current = {k: v for k, v in merged.items() if str(v.get('type','')).upper() in ('A','AAAA')}
                                    logger.info(f"Initial GCP DNS records for {m_domain}: {len(initial_gcp)} (merged A/AAAA={len(gcp_current)}) threshold={FULL_GCP_RECORD_THRESHOLD}")
                                    if (not instance.gcp_records_email_sent) and len(gcp_current) >= FULL_GCP_RECORD_THRESHOLD:
                                        # Build de-namespaced email dict
                                        email_records = {}
                                        for nk, nv in gcp_current.items():
                                            parts = nk.split('|',1)
                                            display_key = parts[1] if len(parts)==2 else nk
                                            email_records[display_key] = nv
                                        if send_gcp_mapping_dns_email(instance.user.email, domain, email_records):
                                            instance.gcp_records_email_sent = True
                                            logger.info(f"GCP DNS records email sent (initial consolidated) for {domain}")
                                    instance.save()
                            else:
                                logger.warning(f"Domain mapping creation failed for {m_domain}: {mapping_create.get('error')}")
                            # Schedule verification polling for each mapping target
                            ScheduledTask.objects.create(
                                task_type='gcp_domain_mapping_verification',
                                task_data={'domain': m_domain},
                                scheduled_at=timezone.now() + timedelta(minutes=GCP_MAPPING_INITIAL_DELAY_MIN),
                                company=instance.user.company,
                            )
                    except Exception as e:
                        logger.warning(f"Failed post-site-verification actions for {domain}: {e}")
                    task.is_completed = True
                    task.executed_at = timezone.now()
                    task.save()
                else:
                    task.scheduled_at = timezone.now() + timedelta(minutes=SITE_VERIFICATION_RETRY_DELAY_MIN)
                    task.save()

            # Add other task types here as needed
        except Exception as e:
            task.scheduled_at = timezone.now() + timedelta(hours=1)
            task.save()
            logger.error(f"Error processing task: {e}")


def process_reminder_tasks():
    now = timezone.now()
    processed = 0
    sent = 0
    skipped_end_date = 0
    # Auto-deactivate expired reminders
    expired_qs = Reminder.objects.filter(active=True, reminder_end_date__lt=now)
    deactivated = expired_qs.update(active=False) if expired_qs.exists() else 0

    due_reminders = Reminder.objects.filter(
        reminder_start_date__lte=now,
        send=False,
        active=True
    )

    for reminder in due_reminders:
        try:
            processed += 1
            if reminder.reminder_end_date and now > reminder.reminder_end_date:
                skipped_end_date += 1
                logger.info(f"Reminder skipped - past end date {reminder.reminder_end_date}")
                continue

            if _should_send_reminder(reminder, now):
                if _send_reminder_email(reminder):
                    reminder.send = True
                    reminder.completed = False  # reset completion
                    reminder.save(update_fields=['send','completed'])
                    # NEW: Slack notify creator if pending
                    _notify_slack_pending_reminder(reminder)
                    sent += 1
                    if reminder.interval_type and reminder.interval_type != 'one_time':
                        _schedule_next_reminder(reminder)
                    logger.info(f"Successfully sent reminder {reminder.id}: {reminder.title}")
                else:
                    logger.error(f"Failed to send reminder {reminder.id}: {reminder.title}")
            else:
                logger.debug(f"Reminder {reminder.id} not ready to send yet")

        except Exception as e:
            logger.error(f"Error processing reminder {reminder.id}: {e}")

    logger.info(
        f"Reminder processing complete: {processed} processed, {sent} sent, {skipped_end_date} skipped (past end date), {deactivated} deactivated")
    return {
        'processed': processed,
        'sent': sent,
        'skipped_end_date': skipped_end_date,
        'deactivated': deactivated,
    }


def _should_send_reminder(reminder, now):
    """Return True if the reminder should be sent now.
    Current logic is minimal because due_reminders queryset already filters:
      - reminder_start_date <= now
      - send = False (not yet sent)
      - active = True
    We still defensively check end date / start date boundaries and active flag.
    This function can be expanded later for throttling or additional business rules.
    """
    try:
        if not getattr(reminder, 'active', True):
            return False
        end_dt = getattr(reminder, 'reminder_end_date', None)
        if end_dt and now > end_dt:
            return False
        start_dt = getattr(reminder, 'reminder_start_date', None)
        if start_dt and now < start_dt:
            return False
        return True
    except Exception:
        return False


def _send_reminder_email(reminder):
    """Send the reminder email using SendGrid if configured.
    Returns True on (attempted) success. If SENDGRID_API_KEY is missing we log a warning
    and return True (simulation)."""
    try:
        if not reminder.receiver_email:
            logger.warning(f"Reminder {reminder.id} has no receiver_email; skipping send.")
            return False
        recipients = [e.strip() for e in reminder.receiver_email.split(',') if e.strip()]
        if not recipients:
            logger.warning(f"Reminder {reminder.id} has only empty recipients; skipping send.")
            return False
        logger.debug(f"Reminder {reminder.id} recipients resolved: {recipients}")
        subject = reminder.title or 'Reminder'
        plain_body = (reminder.description or '').strip() or f"Reminder: {subject}"
        desc_html = ((reminder.description or '').strip() or subject).replace('\n', '<br>')
        html_body = f"<p>{desc_html}</p>"
        # from_email_addr = reminder.sender_email or config('DEFAULT_FROM_EMAIL', default='no-reply@example.com')
        # Set from_email_addr to no-reply@notifyhub.companydomain.com
        company_domain = None
        if hasattr(reminder, 'company') and reminder.company:
            # Try to get domain from company object
            company_domain = getattr(reminder.company, 'domain', None)
            if not company_domain:
                # Fallback: try to get from company.name if it looks like a domain
                name = getattr(reminder.company, 'name', '')
                if '.' in name:
                    company_domain = name
        # Determine initial sender
        branded_from = None
        if company_domain and USE_BRANDED_SENDER:
            branded_from = f"no-reply@notifyhub.{company_domain}"
        from_name = _ensure_sender_name(reminder)  # use enforced default if needed
        # Fallback default sender (must be verified in SendGrid)
        default_from = config('DEFAULT_FROM_EMAIL', default='no-reply@ferryswiss.com')
        # Decide which from to use first
        from_email_addr = branded_from or default_from
        logger.info(
            f"[REMINDER_EMAIL] id={reminder.id} company_domain={company_domain} USE_BRANDED_SENDER={USE_BRANDED_SENDER} chosen_sender='{from_email_addr}' default_from='{default_from}' subject='{subject}'"
        )
        if not SENDGRID_API_KEY:
            logger.warning(f"_send_reminder_email: SENDGRID_API_KEY not set; NOT sending real email for reminder {reminder.id}. Marking as sent (simulation). from_name='{from_name}'")
            return True
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content, Personalization
        except Exception as ie:
            logger.error(f"SendGrid import failed: {ie}")
            return False
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

        def _do_send(sender_email: str) -> tuple[bool, int, str]:
            mail = Mail()
            mail.from_email = Email(sender_email, from_name)
            mail.subject = subject
            personalization = Personalization()
            for rcpt in recipients:
                personalization.add_to(To(rcpt))
            mail.add_personalization(personalization)
            mail.add_content(Content('text/plain', plain_body))
            mail.add_content(Content('text/html', html_body))
            try:
                resp = sg.client.mail.send.post(request_body=mail.get())
                status = getattr(resp, 'status_code', 0)
                body = resp.body.decode() if hasattr(resp.body, 'decode') else str(getattr(resp, 'body', ''))
                if status == 403:
                    logger.error(f"[SENDGRID_403] id={reminder.id} sender='{sender_email}' default_from='{default_from}' body_snippet={(body or '')[:500]}")
                return (200 <= status < 300, status, body)
            except Exception as e:
                # Map common HTTP error text if available
                msg = str(e)
                logger.error(f"[SENDGRID_EXCEPTION] id={reminder.id} sender='{sender_email}' error='{msg[:300]}'")
                return (False, 0, msg)

        ok, status, body = _do_send(from_email_addr)
        if ok:
            logger.info(f"SendGrid delivered reminder {reminder.id} status={status} sender='{from_email_addr}' from_name='{from_name}'")
            return True
        # If 403 or 4xx likely due to sender domain/auth, retry once with default_from (if different)
        should_retry_with_default = (str(status).startswith('4') and default_from and default_from != from_email_addr)
        # Also force retry if we used a clearly placeholder domain
        if branded_from and default_from and default_from != from_email_addr:
            # Heuristic: example.com or missing company domain often fails auth
            if 'example.com' in branded_from or branded_from.endswith('.example.com'):
                should_retry_with_default = True
        if should_retry_with_default:
            logger.warning(f"[REMINDER_EMAIL_RETRY] id={reminder.id} first_status={status} first_sender='{from_email_addr}' retry_sender='{default_from}' body_snippet={(body or '')[:300]}")
            ok2, status2, body2 = _do_send(default_from)
            if ok2:
                logger.info(f"[REMINDER_EMAIL_RETRY_OK] id={reminder.id} status={status2} sender='{default_from}'")
                return True
            logger.error(f"[REMINDER_EMAIL_RETRY_FAIL] id={reminder.id} status={status2} body_snippet={(body2 or '')[:500]}")
            return False
        snippet = (body or '')[:500]
        logger.error(f"[REMINDER_EMAIL_FAIL] id={reminder.id} status={status} sender='{from_email_addr}' body_snippet={snippet}")
        return False
    except Exception as outer:
        logger.error(f"_send_reminder_email unexpected error reminder {getattr(reminder,'id',None)}: {outer}")
        return False


def _schedule_next_reminder(reminder):
    """Schedule the next occurrence for a recurring reminder by cloning the record with an updated start date.
    Avoid duplicate future reminder creation if already scheduled.
    """
    try:
        if reminder.interval_type in (None, '', 'one_time'):
            return None
        base_start = reminder.reminder_start_date or timezone.now()
        
        # Compute next_start based on interval type
        if reminder.interval_type == 'daily':
            next_start = base_start + timedelta(days=1)
        elif reminder.interval_type == 'weekly':
            next_start = base_start + timedelta(weeks=1)
        elif reminder.interval_type == 'monthly':
            next_start = base_start + relativedelta(months=+1)
        elif reminder.interval_type == 'yearly':
            next_start = base_start + relativedelta(years=+1)
        elif reminder.interval_type == 'weekday':
            # Next weekday (Mon-Fri)
            next_start = base_start + timedelta(days=1)
            while next_start.weekday() >= 5: # Sat=5, Sun=6
                next_start += timedelta(days=1)
        elif reminder.interval_type == 'custom':
            every = reminder.custom_repeat_every or 1
            unit = reminder.custom_repeat_unit or 'week'
            if unit == 'day':
                next_start = base_start + timedelta(days=every)
            elif unit == 'week':
                days = reminder.custom_repeat_days
                if not days:
                    next_start = base_start + timedelta(weeks=every)
                else:
                    enabled_days = sorted([int(d) for d in days.split(',')])
                    found = False
                    current_google_wd = (base_start.weekday() + 1) % 7
                    for d in enabled_days:
                        if d > current_google_wd:
                            next_start = base_start + timedelta(days=d - current_google_wd)
                            found = True
                            break
                    if not found:
                        next_start = base_start + timedelta(days=(7 - current_google_wd) + ((every - 1) * 7) + enabled_days[0])
            elif unit == 'month':
                next_start = base_start + relativedelta(months=+every)
            elif unit == 'year':
                next_start = base_start + relativedelta(years=+every)
            else:
                next_start = base_start + timedelta(weeks=every)
        else:
            logger.warning(f"Unknown interval_type '{reminder.interval_type}' for reminder {reminder.id}; skipping schedule.")
            return None

        # Occurrence count and End conditions
        next_count = (reminder.occurrence_count or 1) + 1
        if reminder.interval_type == 'custom':
            if reminder.custom_end_condition == 'on_date' and reminder.reminder_end_date:
                if next_start > reminder.reminder_end_date:
                    return None
            elif reminder.custom_end_condition == 'after_count' and reminder.custom_end_occurrences:
                if next_count > reminder.custom_end_occurrences:
                    return None
        # Respect end date
        if reminder.reminder_end_date and next_start > reminder.reminder_end_date:
            logger.info(f"Next occurrence beyond end date for reminder {reminder.id}; not scheduling further.")
            return None
        # Idempotency: avoid duplicate scheduling (same next_start, same interval, unsent clone)
        existing = Reminder.objects.filter(
            company_id=reminder.company_id,
            created_by_id=getattr(reminder, 'created_by_id', None),
            interval_type=reminder.interval_type,
            send=False,
            active=True,
            reminder_start_date=next_start,
            title=reminder.title,
        ).first()
        if existing:
            logger.debug(f"Duplicate future reminder already exists (id={existing.id}) for original {reminder.id}; skipping clone.")
            return existing
        clone = Reminder.objects.create(
            title=reminder.title,
            description=reminder.description,
            sender_email=reminder.sender_email,
            sender_name=reminder.sender_name,
            receiver_email=reminder.receiver_email,
            interval_type=reminder.interval_type,
            reminder_start_date=next_start,
            reminder_end_date=reminder.reminder_end_date,
            phone_no=reminder.phone_no,
            company=reminder.company,
            created_by=getattr(reminder, 'created_by', None),
            active=reminder.active,
            send=False,
            completed=False,
        )
        logger.info(f"Scheduled next reminder clone {clone.id} for original {reminder.id} at {next_start}.")
        return clone
    except Exception as e:
        logger.error(f"_schedule_next_reminder failed for reminder {getattr(reminder,'id',None)}: {e}")
        return None



def _notify_slack_pending_reminder(reminder):
    """Send a Slack notification to the reminder creator when a reminder has been sent and remains pending.
    Added auto lookup of Slack user ID by email if missing.
    """
    try:
        creator = getattr(reminder, 'created_by', None)
        if not creator or getattr(reminder, 'completed', None):
            return
        if SLACK_BOT_TOKEN and not getattr(creator, 'slack_user_id', None) and getattr(creator, 'email', None):
            _lookup_and_cache_slack_id(creator)
        if not getattr(creator, 'slack_user_id', None):
            return
        subject = (reminder.title or 'Reminder').strip()
        sent_at = getattr(reminder, 'reminder_start_date', None) or timezone.now()
        company_name = getattr(getattr(reminder, 'company', None), 'name', None)
        parts = [":bell: *Reminder sent*", f"{subject} is awaiting completion."]
        if company_name:
            parts.append(f"Company: {company_name}")
        try:
            sent_display = sent_at.strftime('%Y-%m-%d %H:%M %Z').strip()
            parts.append(f"Sent at: {sent_display or sent_at.isoformat()}")
        except Exception:
            parts.append(f"Sent at: {sent_at}")
        if getattr(reminder, 'receiver_email', None):
            parts.append(f"Recipients: {reminder.receiver_email}")
        message = " ".join(parts)

        # 1. Notify Creator (if allowed/available) - kept as legacy behavior but deduped if in list below
        # We'll treat the creator as just another potential target, but checking their ID first.

        recipients_sent = set()

        # Collect target users (creator + explicit slack_users)
        target_users = set()
        if creator and getattr(creator, 'slack_user_id', None):
             target_users.add(creator)
        
        for u in reminder.slack_users.all():
            if getattr(u, 'slack_user_id', None):
                target_users.add(u)
            elif SLACK_BOT_TOKEN and getattr(u, 'email', None):
                # Try JIT lookup
                _lookup_and_cache_slack_id(u)
                if getattr(u, 'slack_user_id', None):
                     target_users.add(u)

        for user in target_users:
            if user.slack_user_id in recipients_sent:
                continue
            if send_dm_to_user(user, message):
                recipients_sent.add(user.slack_user_id)
        
        # 2. Notify Channels
        raw_channels = (getattr(reminder, 'slack_channels', '') or '').split(',')
        for ch in raw_channels:
            ch_clean = ch.strip()
            if ch_clean:
                send_channel_message(ch_clean, message)

        if not recipients_sent and not raw_channels:
            logger.debug('Slack notification could not be delivered for reminder %s (no valid targets)', getattr(reminder, 'id', None))
    except Exception as exc:  # pragma: no cover
        logger.warning('Failed to send Slack notification for reminder %s: %s', getattr(reminder, 'id', None), exc)


def _lookup_and_cache_slack_id(user):
    """Lookup Slack user ID by email and cache it on the user model."""
    import requests
    try:
        email = (getattr(user, 'email', '') or '').strip()
        if not email or not SLACK_BOT_TOKEN:
            return None
        resp = requests.get('https://slack.com/api/users.lookupByEmail', params={'email': email}, headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}, timeout=6)
        data = resp.json()
        slack_id = data.get('user', {}).get('id') if data.get('ok') else None
        if slack_id:
            user.slack_user_id = slack_id
            user.save(update_fields=['slack_user_id'])
        return slack_id
    except Exception as e:
        logger.debug(f"Slack lookup failed for {getattr(user,'id',None)}: {e}")
        return None


def _ensure_sender_name(reminder):
    """Ensure sender_name is populated with default 'Alerts | <Company>' if possible.
    Also treats legacy placeholder 'NotifyHub Alerts' (without company) as empty.
    Returns the effective sender name used.
    """
    try:
        current = getattr(reminder, 'sender_name', None)
        if (not current or current.strip() == '' or current == 'NotifyHub Alerts') and getattr(reminder, 'company', None):
            default_name = f"Alerts | {reminder.company.name}"[:200]
            reminder.sender_name = default_name
            try:
                reminder.save(update_fields=['sender_name'])
            except Exception:
                pass
            return default_name
        return current or 'NotifyHub Alerts'
    except Exception:
        return 'NotifyHub Alerts'


from django.core.cache import cache

def is_rate_limited(request, key, limit_per_min):
    """Simple rate limiter using IP address and cache."""
    from django.conf import settings
    if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
        return False
    
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    cache_key = f"rl:{key}:{ip}"
    count = cache.get(cache_key)
    
    if count is None:
        cache.set(cache_key, 1, 60)
        return False
        
    if count >= limit_per_min:
        logger.warning(f"RATE LIMIT TRIGGERED: key={key}, ip={ip}, count={count}")
        return True
    
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, count + 1, 60)
    return False

