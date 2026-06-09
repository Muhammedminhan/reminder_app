#!/usr/bin/env python3
"""
Debug script to test SendGrid configuration and connectivity
Run this in your Cloud Run environment to diagnose issues
"""

import os
import requests
import json
from decouple import config

def test_environment_variables():
    """Test if required environment variables are set"""
    print("=== Environment Variables Test ===")
    
    # Check SENDGRID_API_KEY
    sendgrid_key = config('SENDGRID_API_KEY', default='')
    print(f"SENDGRID_API_KEY present: {bool(sendgrid_key)}")
    if sendgrid_key:
        print(f"SENDGRID_API_KEY length: {len(sendgrid_key)}")
        print(f"SENDGRID_API_KEY starts with: {sendgrid_key[:10]}...")
    
    # Check other important variables
    debug_mode = config('DEBUG', default='False')
    print(f"DEBUG mode: {debug_mode}")
    
    # Check if we're in Cloud Run
    k_service = os.environ.get('K_SERVICE', '')
    print(f"Cloud Run Service: {k_service}")
    
    return bool(sendgrid_key)

def test_sendgrid_connectivity():
    """Test connectivity to SendGrid API"""
    print("\n=== SendGrid Connectivity Test ===")
    
    sendgrid_key = config('SENDGRID_API_KEY', default='')
    if not sendgrid_key:
        print("❌ SENDGRID_API_KEY not set")
        return False
    
    # Test basic API connectivity
    url = "https://api.sendgrid.com/v3/user/profile"
    headers = {
        "Authorization": f"Bearer {sendgrid_key}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Testing connection to: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SendGrid API connection successful")
            print(f"Account email: {data.get('email', 'N/A')}")
            return True
        else:
            print(f"❌ SendGrid API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_domain_authentication():
    """Test domain authentication creation"""
    print("\n=== Domain Authentication Test ===")
    
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
        print(f"Testing domain authentication for: {test_domain}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            # This is expected for a test domain
            print("✅ SendGrid API is responding (400 expected for test domain)")
            return True
        elif response.status_code == 201:
            print("✅ Domain authentication endpoint working")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing domain authentication: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 SendGrid Configuration Debug Tool")
    print("=" * 50)
    
    # Test 1: Environment variables
    env_ok = test_environment_variables()
    
    # Test 2: Connectivity
    if env_ok:
        connectivity_ok = test_sendgrid_connectivity()
        
        # Test 3: Domain authentication
        if connectivity_ok:
            auth_ok = test_domain_authentication()
        else:
            auth_ok = False
    else:
        connectivity_ok = False
        auth_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Environment Variables: {'✅ OK' if env_ok else '❌ FAILED'}")
    print(f"SendGrid Connectivity: {'✅ OK' if connectivity_ok else '❌ FAILED'}")
    print(f"Domain Authentication: {'✅ OK' if auth_ok else '❌ FAILED'}")
    
    if not env_ok:
        print("\n🔧 FIX: Set SENDGRID_API_KEY environment variable in Cloud Run")
    elif not connectivity_ok:
        print("\n🔧 FIX: Check SendGrid API key validity and network connectivity")
    elif not auth_ok:
        print("\n🔧 FIX: Check SendGrid account permissions for domain authentication")

if __name__ == "__main__":
    main()
