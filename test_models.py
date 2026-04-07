#!/usr/bin/env python3
"""
Test script to check if models can be loaded and basic operations work
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/admin/PycharmProjects/reminder_app')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
django.setup()

from django.contrib.auth.models import User
from app.models import Reminder, SendGridDomainAuth, Company, Department
from django.core.exceptions import ValidationError

def test_model_imports():
    """Test if models can be imported without errors"""
    print("=== Testing Model Imports ===")
    try:
        from app.models import Reminder, SendGridDomainAuth, Company, Department, User
        print("✅ All models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        return False

def test_reminder_model():
    """Test Reminder model basic operations"""
    print("\n=== Testing Reminder Model ===")
    try:
        # Test creating a Reminder instance
        reminder = Reminder(
            title="Test Reminder",
            description="Test description",
            interval_type="daily"
        )
        print("✅ Reminder instance created successfully")
        
        # Test the is_active method
        is_active = reminder.is_active()
        print(f"✅ is_active() method works: {is_active}")
        
        return True
    except Exception as e:
        print(f"❌ Error with Reminder model: {e}")
        return False

def test_sendgrid_model():
    """Test SendGridDomainAuth model basic operations"""
    print("\n=== Testing SendGridDomainAuth Model ===")
    try:
        # Test creating a SendGridDomainAuth instance
        # First, we need a user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )
        
        sendgrid_auth = SendGridDomainAuth(
            user=user,
            domain="test.example.com",
            customer_id="test-customer"
        )
        print("✅ SendGridDomainAuth instance created successfully")
        
        # Test the __str__ method
        str_repr = str(sendgrid_auth)
        print(f"✅ __str__ method works: {str_repr}")
        
        return True
    except Exception as e:
        print(f"❌ Error with SendGridDomainAuth model: {e}")
        return False

def test_utils_imports():
    """Test if utils functions can be imported"""
    print("\n=== Testing Utils Imports ===")
    try:
        from app.utils import generate_unique_id, filter_company, set_company, remove_company
        print("✅ Utils functions imported successfully")
        
        # Test generate_unique_id
        unique_id = generate_unique_id()
        print(f"✅ generate_unique_id works: {unique_id}")
        
        return True
    except Exception as e:
        print(f"❌ Error importing utils: {e}")
        return False

def test_admin_imports():
    """Test if admin classes can be imported"""
    print("\n=== Testing Admin Imports ===")
    try:
        from app.admin import ReminderAdmin, SendGridDomainAuthAdmin
        print("✅ Admin classes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing admin classes: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Model and Admin Test Tool")
    print("=" * 50)
    
    # Test 1: Model imports
    models_ok = test_model_imports()
    
    # Test 2: Reminder model
    reminder_ok = test_reminder_model()
    
    # Test 3: SendGrid model
    sendgrid_ok = test_sendgrid_model()
    
    # Test 4: Utils imports
    utils_ok = test_utils_imports()
    
    # Test 5: Admin imports
    admin_ok = test_admin_imports()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Model Imports: {'✅ OK' if models_ok else '❌ FAILED'}")
    print(f"Reminder Model: {'✅ OK' if reminder_ok else '❌ FAILED'}")
    print(f"SendGrid Model: {'✅ OK' if sendgrid_ok else '❌ FAILED'}")
    print(f"Utils Imports: {'✅ OK' if utils_ok else '❌ FAILED'}")
    print(f"Admin Imports: {'✅ OK' if admin_ok else '❌ FAILED'}")
    
    if not models_ok:
        print("\n🔧 FIX: Check model imports and dependencies")
    elif not reminder_ok:
        print("\n🔧 FIX: Check Reminder model configuration")
    elif not sendgrid_ok:
        print("\n🔧 FIX: Check SendGridDomainAuth model configuration")
    elif not utils_ok:
        print("\n🔧 FIX: Check utils.py imports and functions")
    elif not admin_ok:
        print("\n🔧 FIX: Check admin.py configuration")

if __name__ == "__main__":
    main()
