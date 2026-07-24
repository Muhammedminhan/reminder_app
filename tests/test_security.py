"""tests/test_security.py

Security regression tests covering the four gaps identified in the 2026-07-24
code review: GraphQL tenant isolation, SAML tenant-binding, webhook rate
limiting, and PKCE one-time token exchange.

Each test class is self-contained and documents the invariant it enforces.
"""

import hashlib
import json
import os
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app.models import Company, CompanySSOSettings, Reminder, User


# ── shared helpers ────────────────────────────────────────────────────────────

def _saml_xml(entity_id: str) -> bytes:
    """Minimal SAML Response XML containing the given Issuer."""
    return (
        '<?xml version="1.0"?>'
        '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
        ' xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">'
        f'<saml:Issuer>{entity_id}</saml:Issuer>'
        '</samlp:Response>'
    ).encode()


def _mock_auth(entity_id: str, email: str, xml_override=...) -> MagicMock:
    """
    Return a MagicMock behaving like a fully-authenticated OneLogin_Saml2_Auth.

    Pass xml_override=None to simulate a missing response blob;
    omit it (or pass ... ) to use the default XML for entity_id.
    """
    m = MagicMock()
    m.get_errors.return_value = []
    m.is_authenticated.return_value = True
    m.get_last_response_in_xml.return_value = (
        _saml_xml(entity_id) if xml_override is ... else xml_override
    )
    m.get_attributes.return_value = {'email': [email]}
    m.redirect_to.return_value = '/'
    return m


# ── GraphQL tenant isolation ──────────────────────────────────────────────────

class GraphQLTenantIsolationTest(TestCase):
    """
    Invariant: a non-superuser GraphQL request must never see records that
    belong to a different company, regardless of which resolver is called.

    Setup: two companies, one user each, one reminder each.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company_a = Company.objects.create(name='Alpha Corp', domain='alpha.com')
        cls.company_b = Company.objects.create(name='Beta Corp', domain='beta.com')

        cls.user_a = User.objects.create_user(
            username='alice_iso', email='alice@alpha.com', password='test',
            company=cls.company_a,
        )
        cls.user_b = User.objects.create_user(
            username='bob_iso', email='bob@beta.com', password='test',
            company=cls.company_b,
        )
        cls.reminder_a = Reminder.objects.create(
            title='Alpha secret',
            created_by=cls.user_a,
            company=cls.company_a,
        )
        cls.reminder_b = Reminder.objects.create(
            title='Beta secret',
            created_by=cls.user_b,
            company=cls.company_b,
        )

    def _gql(self, query, user=None):
        client = Client()
        if user:
            client.force_login(user)
        return client.post(
            '/graphql/',
            json.dumps({'query': query}),
            content_type='application/json',
        )

    def _data(self, resp, key):
        return (resp.json().get('data') or {}).get(key)

    # users resolver -----------------------------------------------------------

    def test_users_list_excludes_other_company(self):
        """resolve_users must filter by the requester's company."""
        resp = self._gql('{ users { username } }', self.user_a)
        usernames = [u['username'] for u in self._data(resp, 'users') or []]
        self.assertIn('alice_iso', usernames)
        self.assertNotIn('bob_iso', usernames)

    def test_user_by_id_cross_tenant_returns_null(self):
        """resolve_user(id=X) must return null when X belongs to another company."""
        resp = self._gql(f'{{ user(id: "{self.user_b.pk}") {{ id }} }}', self.user_a)
        self.assertIsNone(self._data(resp, 'user'))

    # reminders resolver -------------------------------------------------------

    def test_reminders_list_excludes_other_company(self):
        """resolve_reminders must filter by the requester's company."""
        resp = self._gql('{ reminders { title } }', self.user_a)
        titles = [r['title'] for r in self._data(resp, 'reminders') or []]
        self.assertIn('Alpha secret', titles)
        self.assertNotIn('Beta secret', titles)

    def test_reminders_isolation_is_symmetric(self):
        """Company-B user must also be unable to see Company-A reminders."""
        resp = self._gql('{ reminders { title } }', self.user_b)
        titles = [r['title'] for r in self._data(resp, 'reminders') or []]
        self.assertIn('Beta secret', titles)
        self.assertNotIn('Alpha secret', titles)

    # unauthenticated ----------------------------------------------------------

    def test_unauthenticated_users_returns_empty(self):
        """Unauthenticated request must receive [] not data or an error."""
        resp = self._gql('{ users { id } }')
        self.assertEqual(self._data(resp, 'users'), [])

    def test_unauthenticated_reminders_returns_empty(self):
        resp = self._gql('{ reminders { id } }')
        self.assertEqual(self._data(resp, 'reminders'), [])


# ── SAML tenant binding ───────────────────────────────────────────────────────

class SAMLTenantBindingTest(TestCase):
    """
    Invariant: sso_acs() must fail closed (403) for any SAML response that
    doesn't fully satisfy issuer, email-domain, and cross-tenant checks.

    The one passing scenario (test_valid_jit_provisioning) validates that
    the happy path still works after all the hardening.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name='Acme Corp', domain='acme.com')
        cls.entity_id = 'https://idp.acme.com'
        cls.sso_settings = CompanySSOSettings.objects.create(
            company=cls.company,
            sso_endpoint='https://idp.acme.com/sso',
            entity_id=cls.entity_id,
            public_certificate='MOCK_CERT',
            is_enabled=True,
        )

    def _acs(self, auth_mock, company=None):
        company = company or self.company
        with patch('app.views.OneLogin_Saml2_Auth', return_value=auth_mock):
            return Client().post(
                reverse('sso_acs', kwargs={'company_id': company.pk}),
                {'SAMLResponse': 'MOCK'},
            )

    def test_issuer_mismatch_rejected(self):
        """An assertion signed by a foreign IdP must be rejected."""
        auth = _mock_auth('https://evil-idp.example.com', 'alice@acme.com')
        self.assertEqual(self._acs(auth).status_code, 403)

    def test_missing_issuer_element_rejected(self):
        """XML with no <Issuer> element must be rejected."""
        no_issuer_xml = (
            b'<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"/>'
        )
        auth = _mock_auth(self.entity_id, 'alice@acme.com', xml_override=no_issuer_xml)
        self.assertEqual(self._acs(auth).status_code, 403)

    def test_null_xml_blob_rejected(self):
        """When get_last_response_in_xml() returns None the endpoint fails closed."""
        auth = _mock_auth(self.entity_id, 'alice@acme.com', xml_override=None)
        self.assertEqual(self._acs(auth).status_code, 403)

    def test_email_domain_mismatch_rejected(self):
        """JIT provisioning is refused when the email domain != company.domain."""
        auth = _mock_auth(self.entity_id, 'attacker@evil.com')
        self.assertEqual(self._acs(auth).status_code, 403)

    def test_cross_tenant_existing_user_rejected(self):
        """
        A user who belongs to Company A must not be logged in via Company B's ACS.

        Scenario: alice@acme.com is registered under self.company (acme.com).
        An attacker creates company_b with domain other.com and an SSO endpoint,
        then crafts a SAML assertion for alice@acme.com against company_b's ACS.
        The email domain (acme.com) doesn't match company_b's domain (other.com),
        so the request must be rejected before the cross-company user check even runs.
        """
        company_b = Company.objects.create(name='Other Corp', domain='other.com')
        CompanySSOSettings.objects.create(
            company=company_b,
            sso_endpoint='https://idp.other.com/sso',
            entity_id='https://idp.other.com',
            public_certificate='MOCK_CERT',
            is_enabled=True,
        )
        User.objects.create_user(
            username='alice_ct', email='alice@acme.com',
            company=self.company, password='x',
        )
        auth = _mock_auth(
            'https://idp.other.com',
            'alice@acme.com',  # email domain acme.com != other.com
            xml_override=_saml_xml('https://idp.other.com'),
        )
        resp = self._acs(auth, company=company_b)
        self.assertEqual(resp.status_code, 403)

    def test_saml_errors_rejected(self):
        """Any SAML validation error from the library must produce a 403."""
        auth = _mock_auth(self.entity_id, 'alice@acme.com')
        auth.get_errors.return_value = ['invalid_signature']
        self.assertEqual(self._acs(auth).status_code, 403)

    def test_valid_jit_provisioning_creates_user_and_redirects(self):
        """A well-formed SAML assertion must JIT-provision a new user and 302."""
        auth = _mock_auth(self.entity_id, 'newuser@acme.com')
        resp = self._acs(auth)
        self.assertEqual(resp.status_code, 302)
        new_user = User.objects.filter(email='newuser@acme.com').first()
        self.assertIsNotNone(new_user, 'JIT provisioning should have created the user')
        self.assertEqual(new_user.company_id, self.company.pk)


# ── Webhook rate limiting ─────────────────────────────────────────────────────

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class WebhookRateLimitTest(TestCase):
    """
    Invariant: _check_webhook_auth must reject wrong tokens (401) and throttle
    the 11th request from the same IP within 60 seconds (429).
    """

    TOKEN = 'webhook-test-secret'

    def setUp(self):
        cache.clear()

    def _post(self, token=None):
        return self.client.post(
            reverse('process-tasks-webhook'),
            HTTP_X_WEBHOOK_TOKEN=token if token is not None else self.TOKEN,
        )

    @patch('app.views.process_scheduled_tasks')
    def test_valid_token_accepted(self, _):
        with patch.dict(os.environ, {'WEBHOOK_TOKEN': self.TOKEN}):
            resp = self._post()
        self.assertNotEqual(resp.status_code, 401)

    def test_wrong_token_rejected(self):
        with patch.dict(os.environ, {'WEBHOOK_TOKEN': self.TOKEN}):
            resp = self._post(token='wrong')
        self.assertEqual(resp.status_code, 401)

    def test_missing_token_rejected(self):
        with patch.dict(os.environ, {'WEBHOOK_TOKEN': self.TOKEN}):
            resp = self._post(token='')
        self.assertEqual(resp.status_code, 401)

    @patch('app.views.process_scheduled_tasks')
    def test_rate_limit_triggers_on_eleventh_request(self, _):
        """Requests 1–10 succeed; request 11 from the same IP must get 429."""
        with patch.dict(os.environ, {'WEBHOOK_TOKEN': self.TOKEN}):
            for i in range(10):
                resp = self._post()
                self.assertNotEqual(
                    resp.status_code, 429,
                    f'Request {i + 1} of 10 should not be rate-limited yet',
                )
            resp = self._post()
        self.assertEqual(resp.status_code, 429)


# ── PKCE / Google token-exchange one-time use ─────────────────────────────────

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class GoogleTokenExchangeTest(TestCase):
    """
    Invariant: /google/token-exchange/ may only issue the cached token once.

    The implementation uses cache.add() (Redis SET NX) as the atomic claim
    gate.  These tests verify the gate works correctly and that all invalid
    inputs are rejected before the gate is even reached.
    """

    def setUp(self):
        cache.clear()

    def _exchange(self, nonce: str):
        return self.client.post(
            reverse('google-token-exchange'),
            json.dumps({'nonce': nonce}),
            content_type='application/json',
        )

    def _seed(self, nonce: str, token: str = 'test-access-token'):
        """Simulate the OAuth callback storing a token keyed by the nonce hash."""
        nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
        cache.set(f'google_auth_code:{nonce_hash}', token, timeout=360)

    def test_first_claim_returns_token(self):
        """A valid nonce with a seeded cache entry returns the access token."""
        nonce = 'a' * 64
        self._seed(nonce)
        resp = self._exchange(nonce)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get('access_token'), 'test-access-token')

    def test_second_claim_is_rejected(self):
        """The same nonce cannot be claimed twice (one-time-use)."""
        nonce = 'b' * 64
        self._seed(nonce)
        first = self._exchange(nonce)
        self.assertEqual(first.status_code, 200, 'First claim should succeed')
        second = self._exchange(nonce)
        self.assertNotEqual(second.status_code, 200)
        self.assertFalse(second.json().get('ok', True))

    def test_unknown_nonce_rejected(self):
        """A nonce with no corresponding cache entry is rejected."""
        resp = self._exchange('c' * 64)
        self.assertNotEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get('ok', True))

    def test_oversized_nonce_rejected(self):
        """A nonce > 128 chars must be rejected immediately with 400."""
        resp = self._exchange('d' * 129)
        self.assertEqual(resp.status_code, 400)

    def test_empty_body_rejected(self):
        """A POST with no JSON body must return 400."""
        resp = self.client.post(
            reverse('google-token-exchange'),
            b'',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_token_is_deleted_after_claim(self):
        """The cached token must not be readable after a successful exchange."""
        nonce = 'e' * 64
        self._seed(nonce)
        self._exchange(nonce)
        nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
        self.assertIsNone(cache.get(f'google_auth_code:{nonce_hash}'),
                          'Token must be deleted from cache after a successful exchange')
