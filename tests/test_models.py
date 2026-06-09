"""
tests/test_models.py — Django TestCase suite for core model behaviour.

Run with:
    python manage.py test tests.test_models
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.models import (
    Reminder,
    Company,
    Department,
    SendGridDomainAuth,
    Permission,
    Role,
)
from django.contrib.auth import get_user_model

User = get_user_model()  # always app.User, never django.contrib.auth.models.User


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_company(name='Test Corp'):
    return Company.objects.create(name=name, email=f'{name.lower().replace(" ", "")}@example.com')


def make_user(company, username='testuser', superuser=False):
    if superuser:
        return User.objects.create_superuser(
            username=username, email=f'{username}@example.com',
            password='Str0ng!Pass', company=company,
        )
    return User.objects.create_user(
        username=username, email=f'{username}@example.com',
        password='Str0ng!Pass', company=company,
    )


# ── Model import smoke test ────────────────────────────────────────────────────

class ModelImportTest(TestCase):
    """Verifies all core models import cleanly — catches circular imports early."""

    def test_imports(self):
        from app.models import (  # noqa: F401
            Reminder, Company, Department, SendGridDomainAuth,
            Permission, Role, UserRole, ReminderAttachment, ReminderDelivery,
        )


# ── Company model ──────────────────────────────────────────────────────────────

class CompanyModelTest(TestCase):
    def test_str(self):
        c = make_company('Acme')
        self.assertEqual(str(c), 'Acme')


# ── User model ─────────────────────────────────────────────────────────────────

class UserModelTest(TestCase):
    def setUp(self):
        self.company = make_company()

    def test_create_user(self):
        u = make_user(self.company)
        self.assertEqual(u.company, self.company)
        self.assertFalse(u.is_superuser)

    def test_superuser_allows_null_company(self):
        """Superusers are allowed to have company=None (validation only blocks non-superusers)."""
        su = User.objects.create_superuser(
            username='root', email='root@example.com', password='Str0ng!Pass',
        )
        self.assertTrue(su.is_superuser)

    def test_non_superuser_without_company_fails_clean(self):
        """User.clean() must reject non-superusers with company=None."""
        u = User(username='orphan', email='orphan@example.com', company=None, is_superuser=False)
        u.set_password('Str0ng!Pass')
        u.pk = 1  # simulate saved object so clean() runs the check
        with self.assertRaises(ValidationError):
            u.clean()


# ── Reminder model ─────────────────────────────────────────────────────────────

class ReminderModelTest(TestCase):
    def setUp(self):
        self.company = make_company()
        self.user = make_user(self.company)

    def _reminder(self, **kwargs):
        defaults = dict(
            title='Stand-up',
            receiver_email='team@example.com',
            interval_type='daily',
            reminder_start_date=timezone.now(),
            company=self.company,
            created_by=self.user,
            active=True,
        )
        defaults.update(kwargs)
        return Reminder.objects.create(**defaults)

    def test_create_and_str(self):
        r = self._reminder()
        self.assertIn('Stand-up', str(r))

    def test_defaults(self):
        r = self._reminder()
        self.assertFalse(r.send)
        self.assertFalse(r.completed)
        self.assertFalse(r.is_deleted)

    def test_soft_delete_flag(self):
        r = self._reminder()
        # Reminder uses SoftDeleteManager which filters is_deleted=False by default.
        # Use all_objects (the unfiltered manager) to verify the flag was persisted.
        Reminder.all_objects.filter(pk=r.pk).update(is_deleted=True)
        self.assertTrue(
            Reminder.all_objects.filter(pk=r.pk, is_deleted=True).exists()
        )
        # Confirm the default manager excludes it
        self.assertFalse(Reminder.objects.filter(pk=r.pk).exists())

    def test_one_time_reminder(self):
        r = self._reminder(interval_type='one_time')
        self.assertEqual(r.interval_type, 'one_time')


# ── SendGridDomainAuth model ───────────────────────────────────────────────────

class SendGridDomainAuthTest(TestCase):
    def setUp(self):
        self.company = make_company()
        self.user = make_user(self.company)

    def test_str(self):
        auth = SendGridDomainAuth(
            user=self.user,
            customer_id='cust-1',
            domain='notifyhub.example.com',
        )
        self.assertIn('example.com', str(auth))

    def test_clean_requires_tenant_prefix(self):
        """Domain must start with 'notifyhub.' (SUBDOMAIN_TENANT_PREFIX default)."""
        auth = SendGridDomainAuth(user=self.user, domain='plain.example.com')
        with self.assertRaises(ValidationError):
            auth.clean()

    def test_clean_accepts_valid_domain(self):
        auth = SendGridDomainAuth(user=self.user, domain='notifyhub.example.com')
        auth.clean()  # should not raise


# ── Permission & Role models ───────────────────────────────────────────────────

class PermissionRoleTest(TestCase):
    def setUp(self):
        self.company = make_company()

    def test_permission_str(self):
        p = Permission.objects.create(
            code='reminders.create',
            name='Create Reminders',
            category='reminders',
        )
        self.assertIn('reminders.create', str(p))

    def test_role_str(self):
        r = Role.objects.create(name='HR Manager', company=self.company)
        self.assertIn('HR Manager', str(r))

    def test_role_with_permissions(self):
        p = Permission.objects.create(
            code='users.view', name='View Users', category='users',
        )
        r = Role.objects.create(name='Viewer', company=self.company)
        r.permissions.add(p)
        self.assertIn(p, r.permissions.all())


# ── Utils ──────────────────────────────────────────────────────────────────────

class UtilsTest(TestCase):
    def test_generate_unique_id(self):
        from app.utils import generate_unique_id
        uid = generate_unique_id()
        self.assertIsInstance(uid, str)
        self.assertGreater(len(uid), 0)

    def test_generate_unique_id_is_unique(self):
        from app.utils import generate_unique_id
        ids = {generate_unique_id() for _ in range(50)}
        self.assertEqual(len(ids), 50)

    def test_admin_imports(self):
        from app.admin import ReminderAdmin, SendGridDomainAuthAdmin  # noqa: F401
