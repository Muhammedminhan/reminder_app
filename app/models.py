# /reminder_app/app/models.py

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils.timezone import make_aware
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from auditlog.registry import auditlog
from django.utils import timezone
from django.conf import settings
import logging
import uuid

logger = logging.getLogger(__name__)

# Create your models here.
class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(max_length=300, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    Tax_identification = models.TextField(null=True, blank=True)
    domain = models.CharField(max_length=255, null=True, blank=True, help_text="Company's primary domain, e.g. 'companydomain.com'")

    def __str__(self):
        return self.name

class CompanySSOSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='sso_settings')
    sso_endpoint = models.URLField(help_text="IdP Single Sign-On URL (SSO URL)")
    entity_id = models.CharField(max_length=255, help_text="IdP Entity ID (Issuer URL)")
    public_certificate = models.TextField(help_text="IdP X.509 Public Certificate (PEM format)")
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SSO Settings for {self.company.name}"

auditlog.register(CompanySSOSettings)
auditlog.register(Company)


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        # Perform soft delete by setting is_deleted flag; return (count, details) like Django's delete
        count = super().update(is_deleted=True)
        return count, {self.model._meta.label: count}

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def hard_delete(self):
        return self.get_queryset().hard_delete()

    def with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class Reminder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    TASK_INTERVAL_CHOICES = [
        ('one_time', 'One-Time Reminder'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('6 months', '6 Months'),
        ('yearly', 'Yearly'),
    ]

    unique_id = models.CharField(max_length=5, unique=True, editable=False, default='')
    title = models.CharField(max_length=250)
    description = models.TextField(max_length=1500, null=True, blank=True)
    sender_email = models.CharField(max_length=150, null=False, blank=False, help_text="Enter the sender email ID")
    sender_name = models.CharField(max_length=200, null=True, blank=True, help_text="Please set proper meaningful sender name , so that the recipient can understand who has sent this - eg: HR | Company Name,  IT | Company Name, Tech B2B | Company Name, Peter Parker")
    receiver_email = models.TextField(max_length=2000, null=False, blank=False, help_text="Enter email IDs for reminders, separated by commas.")
    interval_type = models.CharField(max_length=10, choices=TASK_INTERVAL_CHOICES, null=True, blank=True, default='one_time')
    reminder_start_date = models.DateTimeField(null=True, blank=True, help_text="Set when to send the reminder (Send Reminder At)")
    reminder_end_date = models.DateTimeField(null=True, blank=True, help_text="Set the end date for recurring reminders")
    phone_no = models.CharField(max_length=20, null=True, blank=True, help_text="Please include the Country code")
    send = models.BooleanField(default=False)
    completed = models.BooleanField(default=False, help_text="Mark as completed after acting on the reminder.")
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    # Added created_by field (was missing though migration 0008 exists) to align model with DB and admin code
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reminders')
    active = models.BooleanField(default=True, help_text="Uncheck to pause sending of this reminder and its future occurrences.")
    visible_to_department = models.BooleanField(default=False, help_text="When enabled, this reminder will be visible to all members of your department. If unchecked, the reminder will remain private and visible only to you (the creator).")
    is_deleted = models.BooleanField(default=False, db_index=True)
    slack_user_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Slack member ID for direct notifications (e.g. U123456789)."
    )
    slack_channels = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Comma-separated list of Slack channel IDs or names (e.g. #general, C12345)."
    )
    slack_users = models.ManyToManyField(
        'User',
        related_name='reminder_slack_notifications',
        blank=True,
        help_text="Additional users to notify via Slack."
    )

    objects = SoftDeleteManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    def __str__(self):
        return self.title

    def is_active(self):
        """Returns True if the current date is before the end date, or no end date is set."""
        return not self.reminder_end_date or timezone.now() <= self.reminder_end_date

    def clean(self):
        super().clean()
        # Validate receiver_email field
        if self.receiver_email:
            emails = [e.strip() for e in self.receiver_email.split(',') if e.strip()]
            invalid_emails = []

            for email in emails:
                try:
                    validate_email(email)
                except ValidationError:
                    invalid_emails.append(email)

            if invalid_emails:
                raise ValidationError({
                    'receiver_email': f"Invalid email address(es): {', '.join(invalid_emails)}"
                })

    def save(self, *args, **kwargs):
        from .utils import generate_unique_id
        # Derive company from created_by if not explicitly set
        if not getattr(self, 'company_id', None) and getattr(self, 'created_by', None) and getattr(self.created_by, 'company_id', None):
            self.company = self.created_by.company
        if not self.unique_id:
            self.unique_id = generate_unique_id()
        # Do NOT auto-populate sender_name; leave blank so placeholder shows in admin and dynamic default applied only at send time
        if not self.interval_type:
            self.interval_type = 'one_time'
        if not self.reminder_start_date:
            delay_min = getattr(settings, 'REMINDER_DEFAULT_DELAY_MINUTES', 5)
            try:
                delay_min = int(delay_min)
            except Exception:
                delay_min = 5
            self.reminder_start_date = timezone.now() + timedelta(minutes=delay_min)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if not self.is_deleted:
            self.is_deleted = True
            self.save(update_fields=['is_deleted'])
        return (1, {self.__class__.__name__: 1})

auditlog.register(Reminder)


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'company'], name='unique_department_company')
        ]

    def __str__(self):
        return self.name

auditlog.register(Department)


class SoftDeleteUserManager(DjangoUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        return super().get_queryset()


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)
    slack_user_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Slack member ID for direct notifications (e.g. U123456789)."
    )

    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    objects = SoftDeleteUserManager()
    # Provide access to all (including deleted) for internal references if needed
    all_objects = DjangoUserManager()

    def delete(self, using=None, keep_parents=False):
        if not self.is_deleted:
            self.is_deleted = True
            # Also deactivate login capability
            self.is_active = False
            self.save(update_fields=['is_deleted', 'is_active'])
        return (1, {self.__class__.__name__: 1})

    def __str__(self):
        return self.username

    def clean(self):
        # Auto-derive company from department if not explicitly set
        if not self.company and getattr(self, 'department', None) and getattr(self.department, 'company', None):
            self.company = self.department.company
        # Defer strict validation until after object has a primary key; admin save_model will set company.
        if self.pk and not self.is_superuser and self.company is None:
            raise ValidationError("Non-superuser must be related to a company.")

        # Profile Picture Validation (2MB Limit + Type Check)
        if self.profile_picture:
            file_size = self.profile_picture.size
            if file_size > 2 * 1024 * 1024:
                raise ValidationError({"profile_picture": "Image file too large (max 2MB)."})
            
            from django.core.validators import FileExtensionValidator
            validator = FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])
            try:
                validator(self.profile_picture)
            except ValidationError:
                raise ValidationError({"profile_picture": "Invalid file type. Please upload a JPG, PNG, or WEBP image."})

    def save(self,  *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class SendGridDomainAuth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sendgrid_domain_auths")
    customer_id = models.CharField(max_length=255, null=True, blank=True)
    domain = models.CharField(max_length=255)
    domain_id = models.BigIntegerField(null=True, blank=True)
    subdomain = models.CharField(max_length=255, default="mail", blank=True)
    is_verified = models.BooleanField(default=False)
    dns_records = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    # Site Verification tracking
    site_verification_method = models.CharField(max_length=50, default='DNS_TXT', blank=True)
    site_verification_token = models.CharField(max_length=512, null=True, blank=True)
    site_verified = models.BooleanField(default=False)
    site_verified_at = models.DateTimeField(null=True, blank=True)
    # Email flow flags
    site_initial_email_sent = models.BooleanField(default=False)
    gcp_records_email_sent = models.BooleanField(default=False)
    mapping_ready_email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.customer_id} - {self.domain} ({'Verified' if self.is_verified else 'Pending'})"

    def clean(self):
        from django.conf import settings
        tenant = getattr(settings, 'SUBDOMAIN_TENANT_PREFIX', 'notifyhub').lower()
        brand = getattr(settings, 'SUBDOMAIN_BRAND_PREFIX', 'admin').lower()
        tenant_prefix = f"{tenant}."
        brand_prefix = f"{brand}."
        d = (self.domain or '').lower().strip()
        # Strip protocol and www for validation only
        for p in ('http://','https://'):
            if d.startswith(p):
                d = d[len(p):]
        if d.startswith('www.'):
            d = d[4:]
        if d.startswith(brand_prefix):
            # brand should not be included in stored domain
            d = d[len(brand_prefix):]
        # Must start with tenant prefix
        if not d.startswith(tenant_prefix):
            raise ValidationError({
                'domain': f"Domain must start with '{tenant_prefix}' (e.g. {tenant}.customer-domain.com)."
            })
        # Must contain at least one more dot after tenant segment
        remainder = d[len(tenant_prefix):]
        if '.' not in remainder:
            raise ValidationError({'domain': 'Domain must include an apex domain after tenant prefix (e.g. notifyhub.example.com).'})
        # Assign normalized form so save() normalization becomes idempotent
        self.domain = d

    def save(self, *args, **kwargs):
        self.clean()  # ensure validation + normalized domain applied prior to normalization logic below
        from django.conf import settings
        try:
            raw = (self.domain or '').strip().lower()
            for p in ('http://','https://'):
                if raw.startswith(p):
                    raw = raw[len(p):]
            raw = raw.rstrip('/')
            if raw.startswith('www.'):
                raw = raw[4:]
            brand = getattr(settings, 'SUBDOMAIN_BRAND_PREFIX', 'admin').lower()
            tenant = getattr(settings, 'SUBDOMAIN_TENANT_PREFIX', 'notifyhub').lower()
            brand_prefix = f"{brand}."
            if raw.startswith(brand_prefix):
                raw = raw[len(brand_prefix):]
            tenant_prefix = f"{tenant}."
            while raw.startswith(tenant_prefix + tenant_prefix):
                raw = raw[len(tenant_prefix):]
            if not raw.startswith(tenant_prefix) and '.' in raw:
                raw = tenant_prefix + raw
            self.domain = raw
        except Exception:
            pass
        super().save(*args, **kwargs)

    @property
    def branded_host(self):
        from django.conf import settings
        brand = getattr(settings, 'SUBDOMAIN_BRAND_PREFIX', 'admin').lower()
        return f"{brand}.{self.domain}" if self.domain else None

    @property
    def apex_domain(self):
        from django.conf import settings
        tenant = getattr(settings, 'SUBDOMAIN_TENANT_PREFIX', 'notifyhub').lower()
        tenant_prefix = f"{tenant}."
        if self.domain and self.domain.startswith(tenant_prefix):
            return self.domain[len(tenant_prefix):]
        return self.domain

class ScheduledTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    TASK_TYPES = [
        ('domain_verification', 'Domain Verification'),
        ('gcp_domain_mapping_verification', 'GCP Domain Mapping Verification'),
        ('site_verification', 'Google Site Verification'),
        ('email_reminder', 'Email Reminder'),
        ('other', 'Other'),
    ]

    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    task_data = models.JSONField(default=dict)
    scheduled_at = models.DateTimeField()
    executed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['task_type', 'scheduled_at', 'is_completed']),
        ]

    def __str__(self):
        return f"{self.task_type} - {self.scheduled_at}"


# Permission and Role System (Similar to Zoho Payroll)
class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Custom permissions for the system.
    Similar to Zoho Payroll's permission system.
    """
    PERMISSION_CATEGORIES = [
        ('reminders', 'Reminders'),
        ('users', 'Users'),
        ('departments', 'Departments'),
        ('company', 'Company Settings'),
        ('reports', 'Reports'),
        ('settings', 'System Settings'),
    ]

    code = models.CharField(max_length=100, unique=True, help_text="Unique permission code (e.g., 'reminders.create')")
    name = models.CharField(max_length=200, help_text="Human-readable permission name")
    category = models.CharField(max_length=50, choices=PERMISSION_CATEGORIES, help_text="Permission category")
    description = models.TextField(blank=True, null=True, help_text="Permission description")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Roles that group multiple permissions together.
    Similar to Zoho Payroll's role system.
    """
    name = models.CharField(max_length=100, help_text="Role name (e.g., 'HR Manager', 'Employee')")
    description = models.TextField(blank=True, null=True, help_text="Role description")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True,
                                help_text="If null, this is a system-wide role. If set, it's company-specific.")
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True,
                                         help_text="Permissions assigned to this role")
    is_active = models.BooleanField(default=True)
    is_system_role = models.BooleanField(default=False,
                                        help_text="System roles cannot be deleted or modified by company admins")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_roles')

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['name', 'company'], name='unique_role_company')
        ]
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        company_name = self.company.name if self.company else "System"
        return f"{self.name} ({company_name})"

    def get_permission_codes(self):
        """Return list of permission codes for this role"""
        return list(self.permissions.filter(is_active=True).values_list('code', flat=True))


class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """
    Assigns roles to users within a company context.
    A user can have multiple roles.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_assignments')
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                help_text="Company context for this role assignment")
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about this assignment")

    class Meta:
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'role', 'company'], name='unique_user_role_company')
        ]
        verbose_name = 'User Role Assignment'
        verbose_name_plural = 'User Role Assignments'

    def __str__(self):
        return f"{self.user.username} - {self.role.name} ({self.company.name})"

    def clean(self):
        """Validate that user and role belong to the same company (or role is system-wide)"""
        if self.role.company and self.role.company != self.company:
            raise ValidationError("Role must belong to the same company as the user role assignment")
        if self.user.company and self.user.company != self.company:
            raise ValidationError("User must belong to the same company as the role assignment")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# Add helper methods to User model for permission checking
def user_has_permission(user, permission_code):
    """
    Check if a user has a specific permission.
    Checks through:
    1. Superuser status
    2. Direct role assignments
    3. Django groups (for backward compatibility)
    """
    if user.is_superuser:
        return True

    # Check through UserRole assignments
    active_roles = UserRole.objects.filter(
        user=user,
        is_active=True,
        role__is_active=True,
        role__permissions__code=permission_code,
        role__permissions__is_active=True
    ).exists()

    if active_roles:
        return True

    # Check Django groups for backward compatibility
    if user.groups.filter(name__iexact='Company Admin').exists():
        # Company Admins have all permissions by default
        return True

    return False


def user_has_role(user, role_name, company=None):
    """Check if user has a specific role"""
    if user.is_superuser:
        return True

    query = UserRole.objects.filter(
        user=user,
        role__name__iexact=role_name,
        is_active=True,
        role__is_active=True
    )

    if company:
        query = query.filter(company=company)

    return query.exists()


def get_user_permissions(user):
    """Get all permission codes for a user"""
    if user.is_superuser:
        return list(Permission.objects.filter(is_active=True).values_list('code', flat=True))

    permissions = set()

    # Get permissions from roles
    user_roles = UserRole.objects.filter(
        user=user,
        is_active=True,
        role__is_active=True
    ).select_related('role').prefetch_related('role__permissions')

    for user_role in user_roles:
        permissions.update(user_role.role.get_permission_codes())

    # Company Admins get all permissions
    if user.groups.filter(name__iexact='Company Admin').exists():
        permissions.update(Permission.objects.filter(is_active=True).values_list('code', flat=True))

    return list(permissions)


# Register with auditlog
auditlog.register(Permission)
auditlog.register(Role)
auditlog.register(UserRole)