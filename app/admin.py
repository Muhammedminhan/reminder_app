# /reminder_app/app/admin.py

from django.contrib import admin, messages
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import IntegrityError, models
from .models import Reminder, Company, User, Department, SendGridDomainAuth, ScheduledTask, Permission, Role, UserRole, CompanySSOSettings
from app.forms import ReminderForm
from django.db import transaction
import logging
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
try:
    from oauth2_provider.models import Application
except Exception:
    Application = None

logger = logging.getLogger(__name__)

ASSIGNABLE_COMPANY_ADMIN_GROUPS = ['User', 'Department Admin']


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'company', 'department', 'is_active']
    def save(self, commit=True):
        user = super().save(commit=False)
        # Derive company from department if not provided
        if not user.company and getattr(user, 'department', None) and getattr(user.department, 'company', None):
            user.company = user.department.company
        if commit:
            user.save()
            self.save_m2m()
        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'company', 'department', 'is_active']
    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.company and getattr(user, 'department', None) and getattr(user.department, 'company', None):
            user.company = user.department.company
        if commit:
            user.save()
            self.save_m2m()
        return user

class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ('username','email','first_name','last_name','is_active','deleted_flag')

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('company', 'department', 'slack_user_id')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'company', 'department', 'slack_user_id', 'is_superuser'),
        }),
    )

    def _is_company_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Company Admin').exists()

    def _is_department_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Department Admin').exists()

    # New helper
    def _is_user(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='User').exists()

    # Override to tailor fieldsets for company admins (both add & change)
    def get_fieldsets(self, request, obj=None):
        if self._is_company_admin(request):
            if obj is None:  # add form
                return (
                    (None, {
                        'classes': ('wide',),
                        'fields': ('username', 'email', 'password1', 'password2', 'company', 'department', 'is_active', 'groups'),
                    }),
                )
            return (
                (None, {
                    'fields': ('username', 'email', 'first_name', 'last_name', 'company', 'department', 'is_active', 'groups')
                }),
            )
        if self._is_department_admin(request):
            # Department admin cannot change company/department assignments after creation
            if obj is None:
                return (
                    (None, {
                        'classes': ('wide',),
                        'fields': ('username', 'email', 'password1', 'password2', 'department', 'is_active'),
                    }),
                )
            # change form
            return (
                (None, {
                    'fields': ('username', 'email', 'first_name', 'last_name', 'department', 'is_active')
                }),
            )
        return super().get_fieldsets(request, obj)

    def has_module_permission(self, request):
        return request.user.is_superuser or self._is_company_admin(request) or self._is_department_admin(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or self._is_company_admin(request):
            return True
        if self._is_department_admin(request):
            if obj is None:
                return True
            return (obj.company_id == request.user.company_id and
                    getattr(obj, 'department_id', None) == getattr(request.user, 'department_id', None)) or obj.pk == request.user.pk
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser or self._is_company_admin(request):
            return True
        if self._is_department_admin(request):
            # Department admins cannot add users
            return False
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or self._is_company_admin(request):
            return True
        if self._is_department_admin(request):
            # Can only change their own user record
            if obj is None:
                return True
            return obj.pk == request.user.pk
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser or self._is_company_admin(request):
            return True
        if self._is_department_admin(request):
            # Can only delete their own user record
            if obj is None:
                return True
            return obj.pk == request.user.pk
        return False

    def deleted_flag(self, obj):
        if getattr(obj, 'is_deleted', False):
            return format_html('<span style="color:#d9534f;font-weight:bold;">Deleted</span>')
        return format_html('<span style="color:#5cb85c;">Active</span>')
    deleted_flag.short_description = 'Status'

    def get_list_filter(self, request):
        # Only show 'is_staff' and a custom group filter for company admins
        if self._is_company_admin(request):
            return ['is_staff', self.CompanyAdminGroupsFilter]
        return super().get_list_filter(request)

    # Custom filter for company admins: only Department Admin and User groups
    class CompanyAdminGroupsFilter(admin.SimpleListFilter):
        title = 'groups'
        parameter_name = 'company_admin_groups'

        def lookups(self, request, model_admin):
            return [
                (g.pk, g.name) for g in Group.objects.filter(name__in=ASSIGNABLE_COMPANY_ADMIN_GROUPS)
            ]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(groups__pk=self.value())
            return queryset

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            from .models import User as UserModel
            try:
                qs = UserModel.all_objects.all()
                deleted_param = request.GET.get('deleted')
                if deleted_param == 'yes':
                    return qs.filter(is_deleted=True)
                if deleted_param == 'no':
                    return qs.filter(is_deleted=False)
                # deleted_param None or 'all'
                return qs if deleted_param == 'all' else qs
            except (OperationalError, ProgrammingError):
                # Likely migration not applied yet; fall back to base queryset
                return qs
        # Non superuser paths unchanged
        if not request.user.is_authenticated:
            return qs.none()
        if self._is_company_admin(request):
            return qs.filter(company=request.user.company).exclude(pk=request.user.pk)
        if self._is_department_admin(request):
            dept_id = getattr(request.user, 'department_id', None)
            if not dept_id:
                return qs.none()
            return qs.filter(company_id=request.user.company_id, department_id=dept_id).exclude(pk=request.user.pk)
        return qs.none()

    def save_model(self, request, obj, form, change):
        # Force company/department for non-superusers
        if request.user.is_authenticated and not request.user.is_superuser:
            if self._is_company_admin(request):
                obj.company = request.user.company
            if self._is_department_admin(request):
                # Prefer direct company; fall back to department's company
                company = getattr(request.user, 'company', None)
                if not company:
                    dept = getattr(request.user, 'department', None)
                    company = getattr(dept, 'company', None)
                if company:
                    obj.company = company
                # Lock department to admin's department if present
                dept_admin_department = getattr(request.user, 'department', None)
                if dept_admin_department:
                    obj.department = dept_admin_department
        # Auto staff for company admins only
        if not change and self._is_company_admin(request):
            obj.is_staff = True
            obj.is_superuser = False
        super().save_model(request, obj, form, change)
        # Post-save group enforcement for company admin
        if self._is_company_admin(request):
            selected = list(obj.groups.filter(name__in=ASSIGNABLE_COMPANY_ADMIN_GROUPS).values_list('name', flat=True))
            if not selected:
                # Ensure at least 'User'
                user_group, _ = Group.objects.get_or_create(name='User')
                obj.groups.add(user_group)
        elif self._is_department_admin(request):
            # Ensure standard user group
            try:
                user_group, _ = Group.objects.get_or_create(name='User')
                obj.groups.add(user_group)
            except Exception:
                pass

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if self._is_company_admin(request):
            # Hide superuser status entirely (handled via fieldsets)
            if 'is_superuser' in ro:
                ro.remove('is_superuser')
        if self._is_department_admin(request):
            # Prevent permission escalation / company change
            for f in ['is_superuser', 'is_staff', 'company']:
                if f not in ro:
                    ro.append(f)
            if obj:  # department immutable on existing users
                if 'department' not in ro:
                    ro.append('department')
        return ro

    def get_fields(self, request, obj=None):
        # BaseUserAdmin.get_fields returns flattened list used in form building when fieldsets not used.
        fields = list(super().get_fields(request, obj))
        if self._is_company_admin(request):
            # Remove permission fields except groups & is_active
            for f in ['is_staff', 'is_superuser', 'user_permissions']:
                if f in fields:
                    fields.remove(f)
            # Ensure company is present
            if 'company' not in fields:
                fields.append('company')
            if 'groups' not in fields:
                fields.append('groups')
        elif self._is_department_admin(request):
            # Remove company & permission fields, department stays (but readonly handled separately)
            for f in ['company', 'is_staff', 'is_superuser', 'groups', 'user_permissions']:
                if f in fields:
                    fields.remove(f)
        else:
            if not request.user.is_superuser and 'company' in fields:
                # Non superuser / non company admin shouldn't set company directly
                fields.remove('company')
        return fields

    def add_view(self, request, form_url='', extra_context=None):
        if not request.user.is_superuser and self._is_company_admin(request) and not company_admin_domain_verified(request.user):
            messages.error(request, "Domain not verified. You cannot add users until domain verification is complete.")
            return redirect('admin:app_user_changelist')
        return super().add_view(request, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if self._is_company_admin(request):
            # Make department required
            if 'department' in form.base_fields:
                company = getattr(request.user, 'company', None)
                if company:
                    form.base_fields['department'].queryset = Department.objects.filter(company=company)
                    form.base_fields['department'].required = True
            if 'company' in form.base_fields:
                company_field = form.base_fields['company']
                company = getattr(request.user, 'company', None)
                if company:
                    company_field.queryset = Company.objects.filter(pk=company.pk)
                    company_field.initial = company.pk
                    company_field.required = True
                    # Remove empty label / blank option
                    try:
                        company_field.empty_label = None
                    except Exception:
                        pass
                    # Overwrite choices explicitly to avoid blank insertion by widget
                    company_field.widget.choices = [(company.pk, str(company))]
            # Do NOT remove 'groups' now; restrict queryset
            if 'groups' in form.base_fields:
                form.base_fields['groups'].queryset = Group.objects.filter(name__in=ASSIGNABLE_COMPANY_ADMIN_GROUPS)
            form.base_fields.pop('is_superuser', None)
            for perm_field in ['user_permissions', 'is_staff']:
                form.base_fields.pop(perm_field, None)
        elif self._is_department_admin(request):
            # Lock department/company
            dept = getattr(request.user, 'department', None)
            if 'department' in form.base_fields and dept:
                form.base_fields['department'].queryset = Department.objects.filter(pk=dept.pk)
                form.base_fields['department'].initial = dept.pk
                form.base_fields['department'].required = True
                try:
                    form.base_fields['department'].empty_label = None
                except Exception:
                    pass
            # Remove company & permission fields
            for perm_field in ['company', 'is_superuser', 'is_staff', 'groups', 'user_permissions']:
                form.base_fields.pop(perm_field, None)
        return form

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'groups' and self._is_company_admin(request):
            kwargs['queryset'] = Group.objects.filter(name__in=ASSIGNABLE_COMPANY_ADMIN_GROUPS)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# Move this assignment outside the class definition
CustomUserAdmin.company_admin_groups = CustomUserAdmin.CompanyAdminGroupsFilter

admin.site.register(User, CustomUserAdmin)


class SoftDeletedFilter(admin.SimpleListFilter):
    title = 'Deleted'
    parameter_name = 'deleted'

    def lookups(self, request, model_admin):
        return [
            ('no', 'Active'),
            ('yes', 'Deleted'),
            ('all', 'All'),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'yes':
            return queryset.filter(is_deleted=True)
        if val == 'no':
            return queryset.filter(is_deleted=False)
        if val == 'all':
            return queryset  # include whatever base queryset provided
        return queryset.filter(is_deleted=False)


class CompletionStatusFilter(admin.SimpleListFilter):
    title = 'Completion Status'
    parameter_name = 'completion_status'

    def lookups(self, request, model_admin):
        return [
            ('pending', 'Pending Completion'),
            ('completed', 'Completed'),
            ('unsent', 'Never Sent'),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'pending':
            return queryset.filter(send=True, completed=False)
        if val == 'completed':
            return queryset.filter(completed=True)
        if val == 'unsent':
            return queryset.filter(send=False)
        return queryset


class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        'unique_id', 'title', 'interval_type', 'reminder_start_date', 'reminder_end_date', 'send', 'completed', 'active', 'deleted_flag', 'created_by_display'
    )
    search_fields = ('title', 'unique_id')
    form = ReminderForm
    list_filter = ('interval_type', 'send', 'active', SoftDeletedFilter, CompletionStatusFilter)
    actions = ['mark_active', 'mark_inactive', 'mark_completed', 'mark_uncompleted', 'send_now_override']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['interval_type', 'send', 'active', SoftDeletedFilter, CompletionStatusFilter]
        else:
            return ['interval_type', 'send', 'active', CompletionStatusFilter]

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.user.is_authenticated:
            initial.setdefault('sender_email', request.user.email)
        if request.user.is_authenticated and request.user.company:
            initial.setdefault('sender_name', f"Alerts | {request.user.company.name}")
        return initial

    def mark_active(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f"{updated} reminder(s) marked active.")
    mark_active.short_description = "Mark selected reminders as Active"

    def mark_inactive(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f"{updated} reminder(s) marked inactive.")
    mark_inactive.short_description = "Mark selected reminders as Inactive"

    def mark_completed(self, request, queryset):
        # Optionally only allow for sent reminders; currently allow all
        updated = queryset.update(completed=True)
        self.message_user(request, f"{updated} reminder(s) marked completed.")
    mark_completed.short_description = "Mark selected reminders as Completed"

    def mark_uncompleted(self, request, queryset):
        updated = queryset.update(completed=False)
        self.message_user(request, f"{updated} reminder(s) marked pending completion.")
    mark_uncompleted.short_description = "Mark selected reminders as Pending"

    def send_now_override(self, request, queryset):
        from .utils import _send_reminder_email, _schedule_next_reminder
        sent = 0
        skipped_inactive = 0
        already_sent = 0
        for reminder in queryset.select_related('company', 'created_by'):
            # Skip inactive reminders
            if not reminder.active:
                skipped_inactive += 1
                continue
            # If already sent (send=True) we still allow resend? choose to treat as manual resend once without altering schedule
            if reminder.send:
                # Allow resend but do NOT schedule next again
                success = _send_reminder_email(reminder)
                if success:
                    reminder.completed = False  # keep it pending after resend
                    reminder.save(update_fields=['completed'])
                    sent += 1
                else:
                    self.message_user(request, f"Failed sending reminder {reminder.id} (already sent earlier).", level=messages.WARNING)
                already_sent += 1
                continue
            # Normal path for unsent reminder
            success = _send_reminder_email(reminder)
            if success:
                reminder.send = True
                reminder.completed = False
                reminder.save(update_fields=['send','completed'])
                if reminder.interval_type and reminder.interval_type != 'one_time':
                    _schedule_next_reminder(reminder)
                sent += 1
            else:
                self.message_user(request, f"Failed sending reminder {reminder.id}.", level=messages.ERROR)
        summary = f"Manual send complete: {sent} sent"
        if skipped_inactive:
            summary += f", {skipped_inactive} inactive skipped"
        if already_sent:
            summary += f", {already_sent} previously-sent re-dispatched"
        self.message_user(request, summary)
    send_now_override.short_description = "Send now (override)"

    def deleted_flag(self, obj):
        if getattr(obj, 'is_deleted', False):
            return format_html('<span style="color:#d9534f;font-weight:bold;">Deleted</span>')
        return format_html('<span style="color:#5cb85c;">Active</span>')
    deleted_flag.short_description = 'Status'

    def get_list_display(self, request):
        base = [
            'unique_id', 'title', 'interval_type', 'reminder_start_date', 'reminder_end_date',
            'send', 'completed', 'active', 'created_by_display'
        ]
        if request.user.is_superuser:
            base.insert(8, 'deleted_flag')  # Insert at the original position for superusers
        return base

    def _is_company_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Company Admin').exists()

    def _is_department_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Department Admin').exists()

    def _is_user(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='User').exists()

    def _column_exists(self, model, column_name):
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                table = model._meta.db_table
                cols = [c.name for c in connection.introspection.get_table_description(cursor, table)]
                return column_name in cols
        except Exception:
            return False

    def get_queryset(self, request):
        from .models import Reminder as ReminderModel
        base_qs = super().get_queryset(request)
        if request.user.is_superuser:
            try:
                qs = ReminderModel.all_objects.all()
                deleted_param = request.GET.get('deleted')
                if deleted_param == 'yes':
                    return qs.filter(is_deleted=True)
                if deleted_param == 'no':
                    return qs.filter(is_deleted=False)
                if deleted_param == 'all':
                    return qs
                # default (None) show active only
                return qs.filter(is_deleted=False)
            except (OperationalError, ProgrammingError):
                return base_qs
        # Non-superuser behavior unchanged
        if not request.user.is_authenticated:
            return base_qs.none()
        if self._is_company_admin(request):
            # Get all users in the same department and company
            from .models import User
            department_users = User.objects.filter(company=request.user.company, department=request.user.department)
            return base_qs.filter(created_by__in=department_users)
        if self._is_department_admin(request):
            dept_id = getattr(request.user, 'department_id', None)
            if not dept_id:
                return base_qs.none()
            return base_qs.filter(company_id=request.user.company_id, created_by__department_id=dept_id)
        if self._is_user(request):
            if not getattr(request.user, 'company_id', None):
                return base_qs.none()
            dept_id = getattr(request.user, 'department_id', None)
            base = base_qs.filter(company_id=request.user.company_id)
            if dept_id:
                # Show reminders created by the user OR department-visible reminders from same department
                from django.db import models
                base = base.filter(
                    models.Q(created_by_id=request.user.id) |
                    models.Q(created_by__department_id=dept_id, visible_to_department=True)
                )
            else:
                base = base.filter(created_by_id=request.user.id)
            return base
        return base_qs.none()

    def save_model(self, request, obj, form, change):
        if request.user.is_authenticated:
            # Ensure sender_email is set for department admin and user groups if field is hidden
            if (self._is_department_admin(request) or self._is_user(request)):
                if not obj.sender_email:
                    obj.sender_email = request.user.email
            if not obj.company_id:
                obj.company = request.user.company
            if (not change or not getattr(obj, 'created_by_id', None)) and self._column_exists(Reminder, 'created_by_id'):
                obj.created_by = request.user
            if not request.user.is_superuser and not self._is_company_admin(request):
                obj.company = request.user.company
                if self._column_exists(Reminder, 'created_by_id'):
                    obj.created_by = request.user
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            logger.error(f"ReminderAdmin save_model failed: {e}")
            raise

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            ro.extend(['company', 'created_by'])
        return ro

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        # Remove company / created_by from form for non superusers
        if not request.user.is_superuser:
            for f in ['company', 'created_by', 'phone_no', 'send']:
                if f in fields:
                    fields.remove(f)
            # Hide sender_email for Department Admin and User
            if self._is_department_admin(request) or self._is_user(request):
                if 'sender_email' in fields:
                    fields.remove('sender_email')
        return fields

    # Permissions
    def has_module_permission(self, request):
        # All authenticated users can see module; queryset will filter
        return request.user.is_authenticated

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or self._is_company_admin(request):
            return True
        if self._is_department_admin(request):
            if obj is None:
                return True
            creator = getattr(obj, 'created_by', None)
            if creator and creator.company_id == request.user.company_id and creator.department_id == request.user.department_id:
                return True
            if getattr(obj, 'created_by_id', None) == request.user.id:
                return True
            return False
        if not self._is_user(request):
            return False
        if obj is None:
            return True
        # Allow viewing if owner
        if obj.created_by_id == request.user.id:
            return True
        # Allow viewing if same company & department
        creator = getattr(obj, 'created_by', None)
        if creator and creator.company_id == request.user.company_id and getattr(request.user, 'department_id', None) and creator.department_id == request.user.department_id:
            return True
        return False

    def has_add_permission(self, request):
        # Always allow button; enforce in add_view for company admin unverified case
        if request.user.is_superuser:
            return True
        if self._is_company_admin(request):
            return True
        if self._is_department_admin(request):
            return True
        return self._is_user(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if self._is_company_admin(request):
            if obj is None:
                return True
            return obj.company_id == request.user.company_id
        if self._is_department_admin(request):
            if obj is None:
                return True
            creator = getattr(obj, 'created_by', None)
            return creator and creator.company_id == request.user.company_id and creator.department_id == request.user.department_id
        if self._is_user(request):
            if obj is None:
                return True
            return obj.created_by_id == request.user.id
        return False

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def created_by_display(self, obj):
        # Safe access even if DB/migration not yet applied (attribute may not exist)
        user = getattr(obj, 'created_by', None)
        return getattr(user, 'username', '') if user else ''
    created_by_display.short_description = 'Created By'
    created_by_display.admin_order_field = 'created_by'

    def add_view(self, request, form_url='', extra_context=None):
        if not request.user.is_superuser and self._is_company_admin(request) and not company_admin_domain_verified(request.user):
            messages.error(request, "Domain not verified. You cannot add reminders until domain verification is complete.")
            return redirect('admin:app_reminder_changelist')
        return super().add_view(request, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        try:
            company = None
            if obj and getattr(obj, 'company', None):
                company = obj.company
            elif request.user.is_authenticated and getattr(request.user, 'company', None):
                company = request.user.company
            if company and 'sender_name' in form.base_fields:
                default_name = f"Alerts | {company.name}"[:200]
                # Placeholder for UX
                form.base_fields['sender_name'].widget.attrs.setdefault('placeholder', default_name)
                # Pre-fill if empty (new obj or existing without sender_name)
                if (not obj) or (not getattr(obj, 'sender_name', None)):
                    form.base_fields['sender_name'].initial = default_name
        except Exception:
            pass
        return form


admin.site.register(Reminder, ReminderAdmin)


class DepartmentAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        from .utils import filter_company
        qs = super().get_queryset(request)
        return filter_company(request, qs)

    def save_model(self, request, obj, form, change):
        from .utils import set_company
        set_company(request, obj)
        try:
            with transaction.atomic():
                messages.set_level(request, messages.ERROR)
                super().save_model(request, obj, form, change)
        except IntegrityError:
            messages.error(request, "The department must be unique.")
        except Exception as e:
            messages.error(request, str(e))

    def get_fields(self, request, obj=None):
        from .utils import remove_company
        fields = super().get_fields(request, obj)
        return remove_company(request, fields)

    def _is_company_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Company Admin').exists()

    def has_module_permission(self, request):
        return request.user.is_superuser or self._is_company_admin(request)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or self._is_company_admin(request)

    def has_add_permission(self, request):
        # Show Add button; block attempt in add_view if unverified
        if request.user.is_superuser:
            return True
        return self._is_company_admin(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if self._is_company_admin(request):
            if obj is None:
                return True
            return obj.company_id == request.user.company_id
        return False

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not request.user.is_authenticated:
            return qs.none()
        if self._is_company_admin(request):
            return qs.filter(company=request.user.company)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if request.user.is_authenticated and not request.user.is_superuser:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not request.user.is_superuser:
            if 'company' in fields:
                fields.remove('company')
        return fields

    def add_view(self, request, form_url='', extra_context=None):
        if not request.user.is_superuser and self._is_company_admin(request) and not company_admin_domain_verified(request.user):
            messages.error(request, "Domain not verified. You cannot add departments until domain verification is complete.")
            return redirect('admin:app_department_changelist')
        return super().add_view(request, form_url, extra_context)


admin.site.register(Department, DepartmentAdmin)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'domain', 'email')
    search_fields = ('name', 'domain')

@admin.register(CompanySSOSettings)
class CompanySSOSettingsAdmin(admin.ModelAdmin):
    list_display = ('company', 'entity_id', 'is_enabled', 'created_at')
    search_fields = ('company__name', 'entity_id')
    raw_id_fields = ('company',)



def send_verification_email(modeladmin, request, queryset):
    # Updated to include GCP records when sending instructions via this action
    from .utils import send_dns_instructions_email, create_domain_mapping_gcp
    for domain_verification in queryset:
        try:
            sendgrid_records = domain_verification.dns_records or {}
            # Try to (re)fetch GCP records so users get the full set in this action too
            gcp_records = {}
            try:
                gcp_result = create_domain_mapping_gcp(domain_verification.apex_domain)
                if gcp_result.get('success') and gcp_result.get('dns_records'):
                    gcp_records = gcp_result['dns_records']
                    # Merge into the model so they're stored as well
                    try:
                        combined = {**(sendgrid_records or {}), **gcp_records}
                        domain_verification.dns_records = combined
                        domain_verification.save()
                    except Exception:
                        logger.warning("Failed to persist merged DNS records on send_verification_email action")
            except Exception as ge:
                logger.warning(f"GCP records fetch failed while sending email: {ge}")

            send_dns_instructions_email(domain_verification.user.email, domain_verification.domain,
                                        sendgrid_records, gcp_records)
            modeladmin.message_user(request, f"Verification instructions sent for {domain_verification.domain}.")
        except Exception as e:
            modeladmin.message_user(request,
                                    f"Failed to send verification instructions for {domain_verification.domain}: {e}",
                                    level=messages.ERROR)


send_verification_email.short_description = "Send verification instructions"

admin.site.site_header = 'NotifyHub Administration'
admin.site.site_title = 'NotifyHub Admin'
admin.site.index_title = 'Welcome to NotifyHub Administration'


@admin.register(SendGridDomainAuth)
class SendGridDomainAuthAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'user', 'domain', 'is_verified', 'last_checked', 'verification_status_display')
    search_fields = ('domain', 'user__username')
    actions = ['authenticate_with_sendgrid', 'check_verification_status']
    readonly_fields = (
        'customer_id', 'domain_id', 'subdomain', 'dns_records', 'is_verified', 'created_at',
        'last_checked', 'site_verification_method', 'site_verification_token', 'site_verified', 'site_verified_at',
         'site_initial_email_sent', 'gcp_records_email_sent', 'mapping_ready_email_sent'
    )

    def verification_status_display(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: green;">✅ Verified</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending Verification</span>')

    verification_status_display.short_description = 'Status'

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            rf = list(self.readonly_fields)
            # Remove 'is_verified' from readonly fields for manual editing
            if 'is_verified' in rf:
                rf.remove('is_verified')
            # Allow superuser to edit site_verified and site_verified_at
            if request.user.is_superuser:
                for field in ['site_verified', 'site_verified_at']:
                    if field in rf:
                        rf.remove(field)
            return rf + ['user', 'domain']
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        if obj and obj.pk:
            return [
                ('Domain Information', {
                    'fields': ('domain', 'user')
                }),
                ('SendGrid Details', {
                    'fields': ('customer_id', 'domain_id', 'subdomain', 'dns_records')
                }),
                ('Verification Status', {
                    'fields': ('is_verified', 'last_checked', 'created_at')
                }),
                ('Google Site Verification', {
                    'fields': ('site_verification_method', 'site_verification_token', 'site_verified', 'site_verified_at')
                }),
                ('Verification Status', {
                    'fields': ('site_initial_email_sent', 'gcp_records_email_sent', 'mapping_ready_email_sent')
                })
            ]
        else:
            return [
                ('Domain Setup', {
                    'fields': ('user', 'domain'),
                    'description': '''
                    <div style="background: #f0f8ff; padding: 15px; border-left: 4px solid #2196F3; margin-bottom: 20px; color: #000;">
                        <h3 style="color: #000;">�� Domain Authentication & Mapping Setup</h3>
                        <p><strong>Step 1:</strong> Save to generate a Google Site Verification TXT token which will be emailed to you.</p>
                        <p><strong>Step 2:</strong> Add the TXT token at your DNS provider; we'll auto-verify and then create the GCP mapping.</p>
                        <p><strong>Step 3:</strong> You'll receive the Cloud Run domain mapping DNS records once available.</p>
                    </div>
                    '''
                })
            ]

    def authenticate_with_sendgrid(self, request, queryset):
        from .utils import (
            create_domain_authentication, create_domain_mapping_gcp,
            request_site_verification_token, send_site_verification_email,
            send_initial_domain_setup_email
        )
        for obj in queryset:
            try:
                auth_data = create_domain_authentication(obj.domain)
                new_sendgrid_records = auth_data.get("dns") or {}
                combined_records = {}
                try:
                    if isinstance(obj.dns_records, dict):
                        combined_records.update(obj.dns_records)
                except Exception:
                    pass
                combined_records.update(new_sendgrid_records)

                if not obj.site_verified:
                    token_res = request_site_verification_token(obj.domain)
                    if token_res.get('success') and token_res.get('token'):
                        obj.site_verification_method = token_res.get('method', 'DNS_TXT')
                        obj.site_verification_token = token_res['token']
                        # Send initial staged email (TXT + SendGrid) only once
                        if not obj.site_initial_email_sent:
                            if send_initial_domain_setup_email(obj.user.email, obj.domain, new_sendgrid_records, obj.site_verification_token):
                                obj.site_initial_email_sent = True
                        # Schedule site verification task
                        try:
                            ScheduledTask.objects.create(
                                task_type='site_verification',
                                task_data={'domain': obj.domain},
                                scheduled_at=timezone.now() + timedelta(minutes=10),
                                company=obj.user.company,
                            )
                        except Exception:
                            pass
                        messages.info(request, f"Site verification token emailed for {obj.domain}. Awaiting verification before sending GCP mapping records.")
                    else:
                        messages.warning(request, f"Could not obtain site verification token for {obj.domain}.")
                else:
                    # If site already verified we do NOT email partial GCP records here; scheduled task will send full set when complete
                    messages.info(request, f"Site already verified for {obj.domain}. Waiting for full GCP DNS set (8 records) to email.")

                obj.customer_id = f"cust-{obj.domain.split('.')[0]}"
                obj.domain_id = auth_data.get("id")
                obj.subdomain = auth_data.get("subdomain")
                obj.dns_records = combined_records
                obj.is_verified = auth_data.get("valid", False)
                obj.save()
                self.message_user(request, f"Domain {obj.domain} processed successfully (staged email flow).")
            except Exception as e:
                self.message_user(request, f"Failed to process {obj.domain}: {e}", level=messages.ERROR)

    authenticate_with_sendgrid.short_description = "Re-authenticate with SendGrid"

    def check_verification_status(self, request, queryset):
        from .utils import check_domain_verification_sync
        for obj in queryset:
            try:
                if obj.domain_id:
                    result = check_domain_verification_sync(obj.domain_id)
                    if result['success']:
                        obj.is_verified = result['verified']
                        obj.save()
                        if obj.is_verified:
                            self.message_user(request, f"Domain {obj.domain} is verified! ✅")
                        else:
                            self.message_user(request, f"Domain {obj.domain} is not yet verified. DNS records may still be propagating.")
                    else:
                        self.message_user(request, f"Could not check {obj.domain}: {result['error']}",
                                          level=messages.WARNING)
                else:
                    self.message_user(request, f"Domain {obj.domain} has no domain_id set.", level=messages.WARNING)
            except Exception as e:
                self.message_user(request, f"Failed to check {obj.domain}: {e}", level=messages.ERROR)

    check_verification_status.short_description = "Check verification status"

    def save_model(self, request, obj, form, change):
        from .utils import (
            create_domain_authentication,
            request_site_verification_token,
            send_initial_domain_setup_email,
        )
        is_new = not change
        try:
            if is_new and not getattr(obj, 'customer_id', None):
                try:
                    prefix = (obj.domain or '').split('.')[0] or 'cust'
                except Exception:
                    prefix = 'cust'
                obj.customer_id = f"cust-{prefix}"
            if is_new and getattr(obj, 'domain_id', None) is None:
                obj.domain_id = 0

            super().save_model(request, obj, form, change)

            if is_new:
                try:
                    from decouple import config as _config
                    if not _config('SENDGRID_API_KEY', default=''):
                        messages.warning(request, "SENDGRID_API_KEY not set. Saved record without SendGrid authentication.")
                        return
                except Exception:
                    messages.warning(request, "Could not read SENDGRID_API_KEY. Saved without SendGrid authentication.")
                    return

                # Site verification token first
                if not obj.site_verified and not obj.site_verification_token:
                    token_res = request_site_verification_token(obj.domain)
                    if token_res.get('success') and token_res.get('token'):
                        obj.site_verification_method = token_res.get('method', 'DNS_TXT')
                        obj.site_verification_token = token_res['token']
                    else:
                        messages.warning(request, f"Failed to retrieve site verification token: {token_res.get('error')}")

                # SendGrid auth
                sendgrid_records = {}
                auth_data = None
                try:
                    auth_data = create_domain_authentication(obj.domain)
                    sendgrid_records = auth_data.get("dns") or {}
                except Exception as e:
                    # Check for SendGrid API conflict (domain already exists)
                    error_message = str(e)
                    already_exists = False
                    status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                    if status_code == 409 or status_code == 400 or (
                        'already exists' in error_message or 'already exists for this URL' in error_message or 'already verified' in error_message):
                        already_exists = True
                    if already_exists:
                        # Accept manual verification for this domain
                        obj.is_verified = True
                        obj.domain_id = obj.domain_id or 0
                        obj.subdomain = obj.subdomain or ''
                        obj.dns_records = obj.dns_records or {}
                        obj.save()
                        messages.success(request, f"Domain {obj.domain} already exists and is manually verified. Instance saved and marked as verified.")
                    else:
                        messages.error(request, f"SendGrid authentication call failed: {e}")
                        # Do not mark as verified, keep current flow

                # Persist baseline (no GCP records yet)
                try:
                    obj.customer_id = f"cust-{obj.domain.split('.')[0]}"
                    obj.domain_id = auth_data.get("id") if auth_data else obj.domain_id
                    obj.subdomain = auth_data.get("subdomain") if auth_data else getattr(obj, 'subdomain', None)
                    obj.dns_records = {**sendgrid_records} if sendgrid_records else obj.dns_records
                    if auth_data:
                        obj.is_verified = auth_data.get("valid", False)
                    obj.save()
                except Exception as e:
                    messages.warning(request, f"Saved, but failed to store details: {e}")

                # Initial staged email (TXT + SendGrid)
                if not obj.site_initial_email_sent:
                    if send_initial_domain_setup_email(obj.user.email, obj.domain, sendgrid_records, obj.site_verification_token):
                        obj.site_initial_email_sent = True
                        obj.save()
                        messages.success(request, "Initial DNS setup email sent (TXT + SendGrid).")
                    else:
                        messages.warning(request, "Failed sending initial DNS setup email.")

                # Schedule site verification polling
                if obj.site_verification_token:
                    try:
                        ScheduledTask.objects.create(
                            task_type='site_verification',
                            task_data={'domain': obj.domain},
                            scheduled_at=timezone.now() + timedelta(minutes=10),
                            company=obj.user.company,
                        )
                    except Exception as e:
                        messages.warning(request, f"Site verification scheduling failed: {e}")

                # Schedule SendGrid verification recheck
                try:
                    if obj.domain_id:
                        ScheduledTask.objects.create(
                            task_type='domain_verification',
                            task_data={'domain_id': obj.domain_id},
                            scheduled_at=timezone.now() + timedelta(minutes=5),
                            company=obj.user.company,
                        )
                except Exception as e:
                    messages.warning(request, f"Domain verification scheduling failed: {e}")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred while saving: {e}")
            logging.exception("Unexpected error in SendGridDomainAuthAdmin.save_model")


# Helper to check domain verification for a company admin user.
# Accepts verification if ANY SendGridDomainAuth tied to the same company (even if owned by superuser) is verified.

def company_admin_domain_verified(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    try:
        is_company_admin = user.groups.filter(name__iexact='Company Admin').exists()
    except Exception:
        is_company_admin = False
    if not is_company_admin:
        return True  # Only restrict company admins
    company_id = getattr(user, 'company_id', None)
    if not company_id:
        return False
    return SendGridDomainAuth.objects.filter(user__company_id=company_id, is_verified=True).exists()


# Permission and Role Admin Interfaces
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for managing permissions (superuser only)"""
    list_display = ('code', 'name', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('code', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Permission Details', {
            'fields': ('code', 'name', 'category', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for managing roles"""
    list_display = ('name', 'company', 'is_system_role', 'is_active', 'permission_count_display', 'created_at')
    list_filter = ('is_active', 'is_system_role', 'company', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        ('Role Details', {
            'fields': ('name', 'description', 'company', 'is_system_role', 'is_active')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'description': 'Select permissions to assign to this role'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def permission_count_display(self, obj):
        """Display count of permissions"""
        count = obj.permissions.filter(is_active=True).count()
        return format_html('<span style="color: {};">{}</span>',
                         'green' if count > 0 else 'red', count)
    permission_count_display.short_description = 'Permissions'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('permissions')
        if not request.user.is_superuser:
            # Company admins can only see roles for their company or system roles
            qs = qs.filter(models.Q(company_id=request.user.company_id) | models.Q(company__isnull=True))
        return qs

    def has_module_permission(self, request):
        return request.user.is_superuser or self._is_company_admin(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._is_company_admin(request):
            return False
        if obj:
            # Can view if it's their company's role or a system role
            return obj.company_id == request.user.company_id or obj.company is None
        return True

    def has_add_permission(self, request):
        return request.user.is_superuser or self._is_company_admin(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._is_company_admin(request):
            return False
        if obj:
            # Cannot modify system roles
            if obj.is_system_role:
                return False
            # Can modify if it's their company's role
            return obj.company_id == request.user.company_id
        return True

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._is_company_admin(request):
            return False
        if obj:
            # Cannot delete system roles
            if obj.is_system_role:
                return False
            # Can delete if it's their company's role
            return obj.company_id == request.user.company_id
        return True

    def _is_company_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Company Admin').exists()

    def save_model(self, request, obj, form, change):
        if not change:  # New role
            obj.created_by = request.user
            if not request.user.is_superuser:
                obj.company = request.user.company
                obj.is_system_role = False
        super().save_model(request, obj, form, change)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin interface for managing user role assignments"""
    list_display = ('user', 'role', 'company', 'is_active', 'assigned_by', 'assigned_at')
    list_filter = ('is_active', 'company', 'assigned_at')
    search_fields = ('user__username', 'user__email', 'role__name', 'company__name')
    readonly_fields = ('assigned_at', 'assigned_by')
    fieldsets = (
        ('Assignment Details', {
            'fields': ('user', 'role', 'company', 'is_active')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('user', 'role', 'company', 'assigned_by')
        if not request.user.is_superuser:
            # Company admins can only see assignments for their company
            qs = qs.filter(company_id=request.user.company_id)
        return qs

    def has_module_permission(self, request):
        return request.user.is_superuser or self._is_company_admin(request)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._is_company_admin(request):
            return False
        if obj:
            return obj.company_id == request.user.company_id
        return True

    def has_add_permission(self, request):
        return request.user.is_superuser or self._is_company_admin(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._is_company_admin(request):
            return False
        if obj:
            return obj.company_id == request.user.company_id
        return True

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self._is_company_admin(request):
            return False
        if obj:
            return obj.company_id == request.user.company_id
        return True

    def _is_company_admin(self, request):
        return request.user.is_authenticated and request.user.groups.filter(name__iexact='Company Admin').exists()

    def save_model(self, request, obj, form, change):
        if not change:  # New assignment
            obj.assigned_by = request.user
            if not request.user.is_superuser:
                obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter foreign key choices based on user permissions"""
        if db_field.name == 'user' and not request.user.is_superuser:
            # Company admins can only assign roles to users in their company
            kwargs['queryset'] = User.objects.filter(company_id=request.user.company_id)
        elif db_field.name == 'role' and not request.user.is_superuser:
            # Company admins can only use roles for their company or system roles
            kwargs['queryset'] = Role.objects.filter(
                models.Q(company_id=request.user.company_id) | models.Q(company__isnull=True),
                is_active=True
            )
        elif db_field.name == 'company' and not request.user.is_superuser:
            # Company admins can only assign within their company
            kwargs['queryset'] = Company.objects.filter(id=request.user.company_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


if Application:
    # Unregister default admin if already registered to avoid AlreadyRegistered
    try:
        admin.site.unregister(Application)
    except admin.sites.NotRegistered:
        pass

    @admin.register(Application)
    class ApplicationAdmin(admin.ModelAdmin):
        list_display = ('name', 'client_id', 'client_type', 'authorization_grant_type', 'user')
        search_fields = ('name', 'client_id')

        def save_model(self, request, obj, form, change):
            # If client_secret is blank, generate and set it
            # DOT's Application.save() handles hashing automatically
            secret = getattr(obj, 'client_secret', '') or ''
            if not secret:
                gen = get_random_string(50)
                obj.client_secret = gen
                # Ensure confidential when using client secret
                if getattr(obj, 'client_type', None) != Application.CLIENT_CONFIDENTIAL:
                     obj.client_type = Application.CLIENT_CONFIDENTIAL
            super().save_model(request, obj, form, change)

