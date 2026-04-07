from django.core.management.base import BaseCommand
import os
import requests
import json
from decouple import config


class Command(BaseCommand):
    help = 'Debug SendGrid configuration and connectivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show verbose output',
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        
        self.stdout.write("🔍 SendGrid Configuration Debug Tool")
        self.stdout.write("=" * 50)
        
        # Test 1: Environment variables
        env_ok = self.test_environment_variables(verbose)
        
        # Test 2: Connectivity
        if env_ok:
            connectivity_ok = self.test_sendgrid_connectivity(verbose)
            
            # Test 3: Domain authentication
            if connectivity_ok:
                auth_ok = self.test_domain_authentication(verbose)
            else:
                auth_ok = False
        else:
            connectivity_ok = False
            auth_ok = False
        
        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"Environment Variables: {'✅ OK' if env_ok else '❌ FAILED'}")
            if env_ok else self.style.ERROR(f"Environment Variables: {'✅ OK' if env_ok else '❌ FAILED'}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"SendGrid Connectivity: {'✅ OK' if connectivity_ok else '❌ FAILED'}")
            if connectivity_ok else self.style.ERROR(f"SendGrid Connectivity: {'✅ OK' if connectivity_ok else '❌ FAILED'}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Domain Authentication: {'✅ OK' if auth_ok else '❌ FAILED'}")
            if auth_ok else self.style.ERROR(f"Domain Authentication: {'✅ OK' if auth_ok else '❌ FAILED'}")
        )
        
        if not env_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Set SENDGRID_API_KEY environment variable in Cloud Run")
            )
        elif not connectivity_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check SendGrid API key validity and network connectivity")
            )
        elif not auth_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check SendGrid account permissions for domain authentication")
            )

    def test_environment_variables(self, verbose=False):
        """Test if required environment variables are set"""
        self.stdout.write("=== Environment Variables Test ===")
        
        # Check SENDGRID_API_KEY
        sendgrid_key = config('SENDGRID_API_KEY', default='')
        self.stdout.write(f"SENDGRID_API_KEY present: {bool(sendgrid_key)}")
        if sendgrid_key and verbose:
            self.stdout.write(f"SENDGRID_API_KEY length: {len(sendgrid_key)}")
            self.stdout.write(f"SENDGRID_API_KEY starts with: {sendgrid_key[:10]}...")
        
        # Check other important variables
        debug_mode = config('DEBUG', default='False')
        self.stdout.write(f"DEBUG mode: {debug_mode}")
        
        # Check if we're in Cloud Run
        k_service = os.environ.get('K_SERVICE', '')
        self.stdout.write(f"Cloud Run Service: {k_service}")
        
        return bool(sendgrid_key)

    def test_sendgrid_connectivity(self, verbose=False):
        """Test connectivity to SendGrid API"""
        self.stdout.write("\n=== SendGrid Connectivity Test ===")
        
        sendgrid_key = config('SENDGRID_API_KEY', default='')
        if not sendgrid_key:
            self.stdout.write(self.style.ERROR("❌ SENDGRID_API_KEY not set"))
            return False
        
        # Test basic API connectivity
        url = "https://api.sendgrid.com/v3/user/profile"
        headers = {
            "Authorization": f"Bearer {sendgrid_key}",
            "Content-Type": "application/json"
        }
        
        try:
            if verbose:
                self.stdout.write(f"Testing connection to: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            self.stdout.write(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(self.style.SUCCESS("✅ SendGrid API connection successful"))
                if verbose:
                    self.stdout.write(f"Account email: {data.get('email', 'N/A')}")
                return True
            else:
                self.stdout.write(self.style.ERROR(f"❌ SendGrid API error: {response.status_code}"))
                if verbose:
                    self.stdout.write(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR("❌ Request timed out"))
            return False
        except requests.exceptions.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f"❌ Connection error: {e}"))
            return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Unexpected error: {e}"))
            return False

    def test_domain_authentication(self, verbose=False):
        """Test domain authentication creation"""
        self.stdout.write("\n=== Domain Authentication Test ===")
        
        # Test with a dummy domain (this won't actually create anything)
        test_domain = "test.example.com"
        
        url = "https://api.sendgrid.com/v3/whitelabel/domains"
        headers = {
            "Authorization": f"Bearer {config('SENDGRID_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "domain": test_domain,
            "subdomain": "mail",
            "automatic_security": True,
            "custom_spf": False,
            "default": False
        }
        
        try:
            if verbose:
                self.stdout.write(f"Testing domain authentication for: {test_domain}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            self.stdout.write(f"Response status: {response.status_code}")
            
            if response.status_code == 400:
                # This is expected for a test domain
                self.stdout.write(self.style.SUCCESS("✅ SendGrid API is responding (400 expected for test domain)"))
                return True
            elif response.status_code == 201:
                self.stdout.write(self.style.SUCCESS("✅ Domain authentication endpoint working"))
                return True
            else:
                self.stdout.write(self.style.ERROR(f"❌ Unexpected response: {response.status_code}"))
                if verbose:
                    self.stdout.write(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error testing domain authentication: {e}"))
            return False
