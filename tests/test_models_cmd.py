from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import Reminder, SendGridDomainAuth, Company, Department
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Test model functionality and identify issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show verbose output',
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        
        self.stdout.write("🔍 Model Functionality Test Tool")
        self.stdout.write("=" * 50)
        
        # Test 1: Model imports
        models_ok = self.test_model_imports(verbose)
        
        # Test 2: Reminder model
        reminder_ok = self.test_reminder_model(verbose)
        
        # Test 3: SendGrid model
        sendgrid_ok = self.test_sendgrid_model(verbose)
        
        # Test 4: Utils imports
        utils_ok = self.test_utils_imports(verbose)
        
        # Test 5: Admin imports
        admin_ok = self.test_admin_imports(verbose)
        
        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"Model Imports: {'✅ OK' if models_ok else '❌ FAILED'}")
            if models_ok else self.style.ERROR(f"Model Imports: {'✅ OK' if models_ok else '❌ FAILED'}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Reminder Model: {'✅ OK' if reminder_ok else '❌ FAILED'}")
            if reminder_ok else self.style.ERROR(f"Reminder Model: {'✅ OK' if reminder_ok else '❌ FAILED'}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"SendGrid Model: {'✅ OK' if sendgrid_ok else '❌ FAILED'}")
            if sendgrid_ok else self.style.ERROR(f"SendGrid Model: {'✅ OK' if sendgrid_ok else '❌ FAILED'}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Utils Imports: {'✅ OK' if utils_ok else '❌ FAILED'}")
            if utils_ok else self.style.ERROR(f"Utils Imports: {'✅ OK' if utils_ok else '❌ FAILED'}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Admin Imports: {'✅ OK' if admin_ok else '❌ FAILED'}")
            if admin_ok else self.style.ERROR(f"Admin Imports: {'✅ OK' if admin_ok else '❌ FAILED'}")
        )
        
        if not models_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check model imports and dependencies")
            )
        elif not reminder_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check Reminder model configuration")
            )
        elif not sendgrid_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check SendGridDomainAuth model configuration")
            )
        elif not utils_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check utils.py imports and functions")
            )
        elif not admin_ok:
            self.stdout.write(
                self.style.WARNING("\n🔧 FIX: Check admin.py configuration")
            )

    def test_model_imports(self, verbose=False):
        """Test if models can be imported without errors"""
        self.stdout.write("=== Testing Model Imports ===")
        try:
            from app.models import Reminder, SendGridDomainAuth, Company, Department, User
            self.stdout.write(self.style.SUCCESS("✅ All models imported successfully"))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error importing models: {e}"))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            return False

    def test_reminder_model(self, verbose=False):
        """Test Reminder model basic operations"""
        self.stdout.write("\n=== Testing Reminder Model ===")
        try:
            # Test creating a Reminder instance
            reminder = Reminder(
                title="Test Reminder",
                description="Test description",
                interval_type="daily"
            )
            self.stdout.write(self.style.SUCCESS("✅ Reminder instance created successfully"))
            
            # Test the is_active method
            is_active = reminder.is_active()
            self.stdout.write(self.style.SUCCESS(f"✅ is_active() method works: {is_active}"))
            
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error with Reminder model: {e}"))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            return False

    def test_sendgrid_model(self, verbose=False):
        """Test SendGridDomainAuth model basic operations"""
        self.stdout.write("\n=== Testing SendGridDomainAuth Model ===")
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
            self.stdout.write(self.style.SUCCESS("✅ SendGridDomainAuth instance created successfully"))
            
            # Test the __str__ method
            str_repr = str(sendgrid_auth)
            self.stdout.write(self.style.SUCCESS(f"✅ __str__ method works: {str_repr}"))
            
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error with SendGridDomainAuth model: {e}"))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            return False

    def test_utils_imports(self, verbose=False):
        """Test if utils functions can be imported"""
        self.stdout.write("\n=== Testing Utils Imports ===")
        try:
            from app.utils import generate_unique_id, filter_company, set_company, remove_company
            self.stdout.write(self.style.SUCCESS("✅ Utils functions imported successfully"))
            
            # Test generate_unique_id
            unique_id = generate_unique_id()
            self.stdout.write(self.style.SUCCESS(f"✅ generate_unique_id works: {unique_id}"))
            
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error importing utils: {e}"))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            return False

    def test_admin_imports(self, verbose=False):
        """Test if admin classes can be imported"""
        self.stdout.write("\n=== Testing Admin Imports ===")
        try:
            from app.admin import ReminderAdmin, SendGridDomainAuthAdmin
            self.stdout.write(self.style.SUCCESS("✅ Admin classes imported successfully"))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error importing admin classes: {e}"))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            return False
