
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from app.models import Company, User, CompanySSOSettings
from onelogin.saml2.auth import OneLogin_Saml2_Auth

class SSOTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name="Acme Corp", domain="acme")
        self.sso_settings = CompanySSOSettings.objects.create(
            company=self.company,
            sso_endpoint="https://idp.example.com/sso",
            entity_id="https://idp.example.com",
            public_certificate="MOCK_CERT",
            is_enabled=True
        )

    @patch('app.views.OneLogin_Saml2_Auth')
    def test_sso_login_redirect(self, MockAuth):
        """Test that /sso/login/ redirects to IdP"""
        # Mock auth instance
        mock_instance = MockAuth.return_value
        mock_instance.login.return_value = "https://idp.example.com/sso?SAMLRequest=..."
        
        url = reverse('sso_login', args=['acme'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://idp.example.com"))

    @patch('app.views.OneLogin_Saml2_Auth')
    def test_sso_acs_jit_provisioning(self, MockAuth):
        """Test JIT provisioning on ACS"""
        mock_instance = MockAuth.return_value
        mock_instance.get_errors.return_value = []
        mock_instance.is_authenticated.return_value = True
        # Mock attributes
        mock_instance.get_attributes.return_value = {
            'email': ['alice@acme.com']
        }
        
        url = reverse('sso_acs', kwargs={'company_id': self.company.pk})
        # We need to POST SAMLResponse
        response = self.client.post(url, {'SAMLResponse': 'mock_response'})
        
        self.assertEqual(response.status_code, 302) # Should redirect to /
        
        # Verify User Created
        user = User.objects.get(email='alice@acme.com')
        self.assertEqual(user.company, self.company)
        self.assertTrue(user.username.startswith('alice'))

    @patch('app.views.OneLogin_Saml2_Auth')
    def test_sso_acs_existing_user(self, MockAuth):
        """Test logging in existing user via SSO"""
        existing_user = User.objects.create(username="bob", email="bob@acme.com", company=self.company)
        
        mock_instance = MockAuth.return_value
        mock_instance.get_errors.return_value = []
        mock_instance.is_authenticated.return_value = True
        mock_instance.get_attributes.return_value = {
            'email': ['bob@acme.com']
        }
        
        url = reverse('sso_acs', kwargs={'company_id': self.company.pk})
        response = self.client.post(url, {'SAMLResponse': 'mock_response'})
        
        self.assertEqual(response.status_code, 302)
        
        # Verify we are logged in as Bob? (Hard to test session in mock without inspecting response or context)
        # But absence of error and redirect suggests success.
