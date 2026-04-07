#!/usr/bin/env python3
"""
Test script to verify container startup and basic functionality
"""

import os
import sys
import django

def test_environment():
    """Test environment variables and basic setup"""
    print("=== Environment Test ===")
    
    # Check required environment variables
    required_vars = ['SECRET_KEY']
    optional_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'SENDGRID_API_KEY']
    
    print("Required environment variables:")
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * len(value)} (set)")
        else:
            print(f"❌ {var}: not set")
    
    print("\nOptional environment variables:")
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * len(value)} (set)")
        else:
            print(f"⚠️  {var}: not set (optional)")
    
    return True

def test_django_setup():
    """Test Django setup"""
    print("\n=== Django Setup Test ===")
    
    try:
        # Set up Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
        django.setup()
        print("✅ Django setup successful")
        return True
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False

def test_database():
    """Test database connection"""
    print("\n=== Database Test ===")
    
    try:
        from django.db import connection
        from django.core.management import execute_from_command_line
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"✅ Database connection successful: {result}")
        
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_models():
    """Test model imports"""
    print("\n=== Model Test ===")
    
    try:
        from app.models import Reminder, SendGridDomainAuth, Company, Department, User
        print("✅ All models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False

def test_admin():
    """Test admin imports"""
    print("\n=== Admin Test ===")
    
    try:
        from app.admin import ReminderAdmin, SendGridDomainAuthAdmin
        print("✅ Admin classes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Admin import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Container Startup Test")
    print("=" * 50)
    
    # Test 1: Environment
    env_ok = test_environment()
    
    # Test 2: Django setup
    django_ok = test_django_setup()
    
    # Test 3: Database
    db_ok = test_database() if django_ok else False
    
    # Test 4: Models
    models_ok = test_models() if django_ok else False
    
    # Test 5: Admin
    admin_ok = test_admin() if django_ok else False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Environment: {'✅ OK' if env_ok else '❌ FAILED'}")
    print(f"Django Setup: {'✅ OK' if django_ok else '❌ FAILED'}")
    print(f"Database: {'✅ OK' if db_ok else '❌ FAILED'}")
    print(f"Models: {'✅ OK' if models_ok else '❌ FAILED'}")
    print(f"Admin: {'✅ OK' if admin_ok else '❌ FAILED'}")
    
    if not env_ok:
        print("\n🔧 FIX: Set required environment variables")
    elif not django_ok:
        print("\n🔧 FIX: Check Django configuration")
    elif not db_ok:
        print("\n🔧 FIX: Check database configuration")
    elif not models_ok:
        print("\n🔧 FIX: Check model definitions")
    elif not admin_ok:
        print("\n🔧 FIX: Check admin configuration")
    else:
        print("\n✅ All tests passed! Container should start successfully.")

if __name__ == "__main__":
    main()
