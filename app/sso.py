
from django.conf import settings
from django.urls import reverse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

class SAMLHelper:
    @staticmethod
    def get_saml_request(request):
        """Prepare the request dictionary expected by python3-saml"""
        # Handle X-Forwarded-Proto for proxies (Cloud Run, etc.)
        http_host = request.get_host()
        if 'HTTP_X_FORWARDED_PROTO' in request.META:
            https = 'on' if request.META['HTTP_X_FORWARDED_PROTO'] == 'https' else 'off'
        else:
            https = 'on' if request.is_secure() else 'off'

        # Force port 443 if https, otherwise use reported port
        # This fixes issues where internal port is 8080 but public is 443
        if https == 'on':
            server_port = 443
        else:
            server_port = request.META.get('SERVER_PORT')

        return {
            'https': https,
            'http_host': http_host,
            'script_name': request.META.get('PATH_INFO'),
            'server_port': server_port,
            'get_data': request.GET.copy(),
            'post_data': request.POST.copy()
        }

    @staticmethod
    def get_settings(company_sso_settings, host=None):
        """Build SAML settings dictionary dynamically for a company"""
        # Allow passing dynamic host, or fallback to sensible default (not *)
        if host:
            base_url = f"https://{host}"
        else:
            # Fallback that avoids '*'
            base_url = "http://localhost:8000"
            if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '*':
                 base_url = f"https://{settings.ALLOWED_HOSTS[0]}"

        return {
            'strict': True,
            'debug': settings.DEBUG,
            'sp': {
                'entityId': f"{base_url}/sso/metadata/",
                'assertionConsumerService': {
                    'url': f"{base_url}/sso/acs/{company_sso_settings.company.pk}/", 
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': f"{base_url}/sso/sls/",
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
            },
            'idp': {
                'entityId': company_sso_settings.entity_id,
                'singleSignOnService': {
                    'url': company_sso_settings.sso_endpoint,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': company_sso_settings.public_certificate,
            }
        }
