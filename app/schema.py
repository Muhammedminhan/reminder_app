import graphene
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Reminder, Company, SendGridDomainAuth, Department, ScheduledTask, Permission, Role, UserRole
from .models import user_has_permission, user_has_role, get_user_permissions
from django.contrib.auth import authenticate
from django.conf import settings
import requests
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from oauth2_provider.models import AccessToken
from auditlog.models import LogEntry


def get_authenticated_user(info):
    """Get authenticated user from OAuth2 token"""
    auth_header = info.context.META.get('HTTP_AUTHORIZATION', '')
    auth_header = info.context.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        import logging
        logger = logging.getLogger('app')
        try:
            access_token = AccessToken.objects.get(token=token)
            if access_token.is_expired():
                logger.warning(f"TOKEN EXPIRED: {token[:10]}... User={access_token.user}")
                return None
            return access_token.user
        except AccessToken.DoesNotExist:
            logger.warning(f"TOKEN NOT FOUND: {token[:10]}... Header start: {auth_header[:15]}...")
            pass
    elif auth_header:
        import logging
        logging.getLogger('app').warning(f"MALFORMED AUTH HEADER: {auth_header[:20]}...")
    return None


class CompanyType(DjangoObjectType):
    class Meta:
        model = Company
        fields = (
            'id', 'name', 'email', 'address', 'website', 'Tax_identification',
        )


class UserType(DjangoObjectType):
    roles = graphene.List(lambda: RoleType)  # Forward reference
    permissions = graphene.List(graphene.String)
    department = graphene.Field(lambda: DepartmentType)  # Forward reference
    
    class Meta:
        model = get_user_model()
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 
            'company', 'department', 'is_active', 'date_joined', 'profile_picture',
            'slack_user_id',
        )
    
    def resolve_profile_picture(self, info):
        if self.profile_picture:
            return info.context.build_absolute_uri(self.profile_picture.url)
        return None
    
    def resolve_roles(self, info):
        """Get all active roles for this user"""
        from .models import UserRole
        user_roles = UserRole.objects.filter(
            user=self,
            is_active=True,
            role__is_active=True
        ).select_related('role').prefetch_related('role__permissions')
        return [ur.role for ur in user_roles]
    
    def resolve_permissions(self, info):
        """Get all permission codes for this user"""
        return get_user_permissions(self)


class ReminderType(DjangoObjectType):
    class Meta:
        model = Reminder
        fields = (
            'id', 'unique_id', 'title', 'description', 'sender_email', 'sender_name',
            'receiver_email', 'interval_type', 'reminder_start_date', 'reminder_end_date',
            'phone_no', 'send', 'completed', 'company', 'created_by', 'active',
            'visible_to_department', 'slack_channels', 'slack_user_id',
        )


class DepartmentType(DjangoObjectType):
    class Meta:
        model = Department
        fields = (
            'id', 'name', 'company',
        )


class SendGridDomainAuthType(DjangoObjectType):
    class Meta:
        model = SendGridDomainAuth
        fields = (
            'id', 'customer_id', 'domain', 'domain_id', 'subdomain', 'is_verified',
            'dns_records', 'created_at', 'last_checked', 'site_verification_method',
            'site_verification_token', 'site_verified', 'site_verified_at',
            'site_initial_email_sent', 'gcp_records_email_sent', 'mapping_ready_email_sent',
            'user',
        )


class ScheduledTaskType(DjangoObjectType):
    class Meta:
        model = ScheduledTask
        fields = (
            'id', 'task_type', 'task_data', 'scheduled_at', 'executed_at', 
            'is_completed', 'created_at', 'company',
        )


class PermissionType(DjangoObjectType):
    class Meta:
        model = Permission
        fields = (
            'id', 'code', 'name', 'category', 'description', 'is_active', 
            'created_at', 'updated_at',
        )


class RoleType(DjangoObjectType):
    permissions = graphene.List(PermissionType)
    permission_count = graphene.Int()
    
    class Meta:
        model = Role
        fields = (
            'id', 'name', 'description', 'company', 'is_active', 'is_system_role',
            'created_at', 'updated_at', 'created_by',
        )
    
    def resolve_permissions(self, info):
        return self.permissions.filter(is_active=True).all()
    
    def resolve_permission_count(self, info):
        return self.permissions.filter(is_active=True).count()


class UserRoleType(DjangoObjectType):
    class Meta:
        model = UserRole
        fields = (
            'id', 'user', 'role', 'company', 'assigned_by', 'assigned_at',
            'is_active', 'notes',
        )


class PerformancePoint(graphene.ObjectType):
    label = graphene.String()
    value = graphene.Int()


class DashboardStatsType(graphene.ObjectType):
    pending_count = graphene.Int()
    completed_count = graphene.Int()
    next_seven_days_count = graphene.Int()
    total_active_count = graphene.Int()
    total_active_count = graphene.Int()
    total_users_count = graphene.Int()


class ActivityType(graphene.ObjectType):
    id = graphene.ID()
    title = graphene.String()
    time = graphene.String()
    description = graphene.String()
    action = graphene.String()


class SlackChannelType(graphene.ObjectType):
    id = graphene.String()
    name = graphene.String()


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)
    users = graphene.List(UserType)
    user = graphene.Field(UserType, id=graphene.ID(required=True))
    companies = graphene.List(CompanyType)
    company = graphene.Field(CompanyType, id=graphene.ID(required=True))
    departments = graphene.List(DepartmentType)
    department = graphene.Field(DepartmentType, id=graphene.ID(required=True))
    reminders = graphene.List(ReminderType, active=graphene.Boolean(required=False))
    reminder = graphene.Field(ReminderType, id=graphene.ID(required=True))
    sendgrid_domain_auths = graphene.List(SendGridDomainAuthType)
    sendgrid_domain_auth = graphene.Field(SendGridDomainAuthType, id=graphene.ID(required=True))
    scheduled_tasks = graphene.List(ScheduledTaskType, task_type=graphene.String(required=False), is_completed=graphene.Boolean(required=False))
    scheduled_task = graphene.Field(ScheduledTaskType, id=graphene.ID(required=True))
    
    # Permission and Role queries
    permissions = graphene.List(PermissionType, category=graphene.String(required=False))
    permission = graphene.Field(PermissionType, id=graphene.ID(required=False), code=graphene.String(required=False))
    roles = graphene.List(RoleType, company=graphene.ID(required=False))
    role = graphene.Field(RoleType, id=graphene.ID(required=True))
    user_roles = graphene.List(UserRoleType, user=graphene.ID(required=False), company=graphene.ID(required=False))
    my_permissions = graphene.List(graphene.String)
    my_roles = graphene.List(RoleType)
    system_performance = graphene.List(PerformancePoint, period=graphene.String())
    dashboard_stats = graphene.Field(DashboardStatsType)
    slack_channels = graphene.List(SlackChannelType)
    recent_activities = graphene.List(ActivityType)

    def resolve_recent_activities(self, info):
        user = get_authenticated_user(info)
        if not user:
            return []
            
        from django.contrib.contenttypes.models import ContentType
        from .models import Reminder
        
        # Get content type for Reminder
        reminder_ct = ContentType.objects.get_for_model(Reminder)
        
        # Fetch last 10 activities for Reminders
        # In a real multi-tenant app, we'd filter by objects belonging to the user's company
        # but Auditlog doesn't store company info directly. We'd need a more complex join.
        # For now, let's just get the most recent ones.
        logs = LogEntry.objects.filter(content_type=reminder_ct).order_by('-timestamp')[:10]
        
        activities = []
        for log in logs:
            action_map = {0: 'Created', 1: 'Updated', 2: 'Deleted'}
            action_str = action_map.get(log.action, 'Modified')
            
            # Format time (e.g. "5m ago")
            from django.utils import timezone
            diff = timezone.now() - log.timestamp
            if diff.days > 0:
                time_str = f"{diff.days}d ago"
            elif diff.seconds > 3600:
                time_str = f"{diff.seconds // 3600}h ago"
            elif diff.seconds > 60:
                time_str = f"{diff.seconds // 60}m ago"
            else:
                time_str = "just now"
                
            activities.append(ActivityType(
                id=str(log.id),
                title=f"{action_str}: {log.object_repr}",
                description=f"Action performed by {log.actor.username if log.actor else 'System'}",
                time=time_str,
                action=action_str
            ))
        return activities

    def resolve_slack_channels(self, info):
        # Fetch from Slack API
        from decouple import config
        token = config('SLACK_BOT_TOKEN', default='')
        channels = []
        if token:
            try:
                import requests
                resp = requests.get('https://slack.com/api/conversations.list', headers={'Authorization': f'Bearer {token}'}, params={'exclude_archived': 'true'}, timeout=6)
                data = resp.json()
                if data.get('ok'):
                    for ch in data.get('channels', []):
                        channels.append(SlackChannelType(id=ch['id'], name=ch['name']))
            except Exception:
                pass
        
        # Fallback list if none fetched (for development/demo)
        if not channels:
            channels = [
                SlackChannelType(id='#general', name='general'),
                SlackChannelType(id='#random', name='random'),
                SlackChannelType(id='#engineering', name='engineering'),
                SlackChannelType(id='#marketing', name='marketing')
            ]
        return channels

    def resolve_me(self, info):
        user = get_authenticated_user(info)
        return user
 
    def resolve_users(self, info):
        user = get_authenticated_user(info)
        if not user:
            return get_user_model().objects.none()
        qs = get_user_model().objects.all().select_related('company', 'department')
        if not user.is_superuser:
            if getattr(user, 'company_id', None):
                qs = qs.filter(company_id=user.company_id)
            else:
                qs = qs.none()
        return qs

    def resolve_user(self, info, id):
        user = get_authenticated_user(info)
        qs = get_user_model().objects.select_related('company', 'department')
        if user and not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        return qs.filter(pk=id).first()

    def resolve_companies(self, info):
        user = get_authenticated_user(info)
        if not user:
            return Company.objects.none()
        
        # Only superusers can see all companies
        if user.is_superuser:
            return Company.objects.all()
        
        # Regular users can only see their own company
        if getattr(user, 'company', None):
            return Company.objects.filter(id=user.company.id)
        
        return Company.objects.none()

    def resolve_company(self, info, id):
        user = get_authenticated_user(info)
        qs = Company.objects.all()
        if not user:
            return None
        if not user.is_superuser:
            if getattr(user, 'company_id', None):
                qs = qs.filter(id=user.company_id)
            else:
                return None
        return qs.filter(pk=id).first()

    def resolve_departments(self, info):
        qs = Department.objects.all().select_related('company')
        user = get_authenticated_user(info)
        if user and not user.is_superuser:
            if getattr(user, 'company_id', None):
                qs = qs.filter(company_id=user.company_id)
            else:
                qs = qs.none()
        return qs

    def resolve_department(self, info, id):
        qs = Department.objects.select_related('company')
        user = get_authenticated_user(info)
        if user and not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        return qs.filter(pk=id).first()

    def resolve_reminders(self, info, active=None):
        user = get_authenticated_user(info)
        if not user:
            return Reminder.objects.none()

        qs = Reminder.objects.all().select_related('company', 'created_by')
        if active is not None:
            qs = qs.filter(active=active)
        
        if not user.is_superuser:
            if getattr(user, 'company_id', None):
                qs = qs.filter(company_id=user.company_id)
            else:
                qs = qs.none()
        return qs

    def resolve_reminder(self, info, id):
        user = get_authenticated_user(info)
        if not user:
            return None

        qs = Reminder.objects.select_related('company', 'created_by')
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        return qs.filter(pk=id).first()

    def resolve_sendgrid_domain_auths(self, info):
        qs = SendGridDomainAuth.objects.all().select_related('user', 'user__company')
        user = get_authenticated_user(info)
        if user and not user.is_superuser:
            if getattr(user, 'company_id', None):
                qs = qs.filter(user__company_id=user.company_id)
            else:
                qs = qs.none()
        return qs

    def resolve_sendgrid_domain_auth(self, info, id):
        qs = SendGridDomainAuth.objects.select_related('user', 'user__company')
        user = get_authenticated_user(info)
        if user and not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(user__company_id=user.company_id)
        return qs.filter(pk=id).first()

    def resolve_scheduled_tasks(self, info, task_type=None, is_completed=None):
        qs = ScheduledTask.objects.all().select_related('company')
        user = get_authenticated_user(info)
        if user and not user.is_superuser:
            if getattr(user, 'company_id', None):
                qs = qs.filter(company_id=user.company_id)
            else:
                qs = qs.none()
        
        if task_type:
            qs = qs.filter(task_type=task_type)
        if is_completed is not None:
            qs = qs.filter(is_completed=is_completed)
        
        return qs

    def resolve_scheduled_task(self, info, id):
        qs = ScheduledTask.objects.select_related('company')
        user = get_authenticated_user(info)
        if user and not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        return qs.filter(pk=id).first()
    
    def resolve_permissions(self, info, category=None):
        """Get all permissions, optionally filtered by category"""
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = Permission.objects.filter(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return qs.all()
    
    def resolve_permission(self, info, id=None, code=None):
        """Get a specific permission by ID or code"""
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        if id:
            return Permission.objects.filter(pk=id, is_active=True).first()
        elif code:
            return Permission.objects.filter(code=code, is_active=True).first()
        return None
    
    def resolve_roles(self, info, company=None):
        """Get roles - system-wide or company-specific"""
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = Role.objects.filter(is_active=True).prefetch_related('permissions')
        
        if user.is_superuser:
            # Superusers can see all roles
            if company:
                qs = qs.filter(company_id=company)
        else:
            # Regular users can only see roles for their company or system roles
            if company:
                qs = qs.filter(Q(company_id=company) | Q(company__isnull=True))
            else:
                qs = qs.filter(Q(company_id=user.company_id) | Q(company__isnull=True))
        
        return qs.all()
    
    def resolve_role(self, info, id):
        """Get a specific role"""
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        role = Role.objects.filter(pk=id, is_active=True).prefetch_related('permissions').first()
        if not role:
            return None
        
        # Check access
        if user.is_superuser:
            return role
        if role.company is None:  # System role
            return role
        if role.company_id == user.company_id:
            return role
        
        raise Exception('Not authorized to view this role')
    
    def resolve_user_roles(self, info, user=None, company=None):
        """Get user role assignments"""
        requester = get_authenticated_user(info)
        if not requester:
            raise Exception('Authentication required')
        
        qs = UserRole.objects.filter(is_active=True).select_related('user', 'role', 'company')
        
        if requester.is_superuser:
            if user:
                qs = qs.filter(user_id=user)
            if company:
                qs = qs.filter(company_id=company)
        else:
            # Regular users can only see roles for their company
            qs = qs.filter(company_id=requester.company_id)
            if user:
                qs = qs.filter(user_id=user)
        
        return qs.all()
    
    def resolve_my_permissions(self, info):
        """Get current user's permissions"""
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        return get_user_permissions(user)
    
    def resolve_my_roles(self, info):
        """Get current user's roles"""
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        user_roles = UserRole.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True
        ).select_related('role').prefetch_related('role__permissions')
        
        return [ur.role for ur in user_roles]

    def resolve_system_performance(self, info, period='Weekly'):
        import random
        # In a real app, we would query historical data
        # For 'Weekly', return 7 points; 'Monthly', 12; 'Daily', 24
        count = 7
        if period == 'Monthly':
            count = 12
        elif period == 'Daily':
            count = 24
        
        # We can also base this on actual reminders in the DB to make it somewhat realistic
        # but for "live" feel, we might want some randomness or just the count.
        # Let's return some semi-random data based on a seed for consistency per call but shifting with time?
        # Actually, let's just return a nice set of points.
        from django.utils import timezone
        import math
        
        points = []
        now = timezone.now()
        for i in range(count):
            # Create a wave pattern with some noise
            base = 100 + 40 * math.sin(i * 0.8)
            noise = random.randint(-15, 15)
            value = max(20, int(base + noise))
            points.append(PerformancePoint(label=f"T{i}", value=value))
            
        return points

    def resolve_dashboard_stats(self, info):
        user = get_authenticated_user(info)
        if not user:
            return None
        
        reminders = Reminder.objects.all()
        users = get_user_model().objects.all()
        
        if not user.is_superuser:
            if getattr(user, 'company_id', None):
                reminders = reminders.filter(company_id=user.company_id)
                users = users.filter(company_id=user.company_id)
            else:
                return DashboardStatsType(
                    pending_count=0,
                    completed_count=0,
                    next_seven_days_count=0,
                    total_active_count=0,
                    total_users_count=0
                )
            
        pending = reminders.filter(completed=False).count()
        completed = reminders.filter(completed=True).count()
        
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        in_seven = reminders.filter(
            reminder_start_date__gte=now,
            reminder_start_date__lte=now + timedelta(days=7)
        ).count()
        
        total_active = reminders.filter(active=True).count()
        total_users = users.count()
        
        return DashboardStatsType(
            pending_count=pending,
            completed_count=completed,
            next_seven_days_count=in_seven,
            total_active_count=total_active,
            total_users_count=total_users
        )


class CreateReminder(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String(required=False)
        sender_email = graphene.String(required=True)
        sender_name = graphene.String(required=False)
        receiver_email = graphene.String(required=True)
        interval_type = graphene.String(required=False)
        reminder_start_date = graphene.DateTime(required=False)
        reminder_end_date = graphene.DateTime(required=False)
        phone_no = graphene.String(required=False)
        completed = graphene.Boolean(required=False)
        visible_to_department = graphene.Boolean(required=False)
        slack_channels = graphene.String(required=False)
        slack_user_id = graphene.String(required=False)

    ok = graphene.Boolean()
    reminder = graphene.Field(ReminderType)

    def mutate(root, info, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        try:
            # Graphene converts camelCase GraphQL args to snake_case Python kwargs
            # Map kwargs to Reminder model fields explicitly
            reminder = Reminder()
            reminder.title = kwargs.get('title')
            
            # OWASP Input Validation & Sanitization
            if not reminder.title:
                raise Exception('Title is required')
            if len(reminder.title) > 255:
                raise Exception('Title exceeds maximum length of 255 characters')
            
            reminder.description = kwargs.get('description')
            if reminder.description and len(reminder.description) > 5000:
                raise Exception('Description exceeds maximum length of 5000 characters')
                
            reminder.sender_email = kwargs.get('sender_email')
            if not reminder.sender_email or '@' not in reminder.sender_email:
                raise Exception('Valid Sender email is required')
            
            reminder.sender_name = kwargs.get('sender_name')
            reminder.receiver_email = kwargs.get('receiver_email')
            if not reminder.receiver_email or '@' not in reminder.receiver_email:
                raise Exception('Valid Receiver email is required')
            
            reminder.interval_type = kwargs.get('interval_type')
            reminder.reminder_start_date = kwargs.get('reminder_start_date')
            reminder.reminder_end_date = kwargs.get('reminder_end_date')
            reminder.phone_no = kwargs.get('phone_no')
            if reminder.phone_no and len(reminder.phone_no) > 50:
                raise Exception('Phone number invalid format')
            
            if 'active' in kwargs:
                reminder.active = kwargs.get('active')
            else:
                reminder.active = True  # Default to active
            
            if 'completed' in kwargs:
                reminder.completed = kwargs.get('completed')
            
            if 'visible_to_department' in kwargs:
                reminder.visible_to_department = kwargs.get('visible_to_department')
            
            if 'slack_channels' in kwargs:
                reminder.slack_channels = kwargs.get('slack_channels')
            
            if 'slack_user_id' in kwargs:
                reminder.slack_user_id = kwargs.get('slack_user_id')
            
            reminder.created_by = user
            if getattr(user, 'company', None):
                reminder.company = user.company
            
            reminder.full_clean()  # Run Django model validation
            reminder.save()
            
            if 'slack_user_id' in kwargs and kwargs['slack_user_id']:
                user_ids = [uid.strip() for uid in kwargs['slack_user_id'].split(',') if uid.strip()]
                users_to_add = get_user_model().objects.filter(id__in=user_ids)
                reminder.slack_users.set(users_to_add)
            elif 'slack_user_id' in kwargs:
                reminder.slack_users.clear()

            return CreateReminder(ok=True, reminder=reminder)
        except Exception as e:
            # Return a more helpful error message
            raise Exception(f'Failed to create reminder: {str(e)}')


class UpdateReminder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String(required=False)
        description = graphene.String(required=False)
        sender_email = graphene.String(required=False)
        sender_name = graphene.String(required=False)
        receiver_email = graphene.String(required=False)
        interval_type = graphene.String(required=False)
        reminder_start_date = graphene.DateTime(required=False)
        reminder_end_date = graphene.DateTime(required=False)
        phone_no = graphene.String(required=False)
        send = graphene.Boolean(required=False)
        completed = graphene.Boolean(required=False)
        slack_channels = graphene.String(required=False)
        slack_user_id = graphene.String(required=False)

    ok = graphene.Boolean()
    reminder = graphene.Field(ReminderType)

    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        qs = Reminder.objects.all()
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        reminder = qs.filter(pk=id).first()
        if not reminder:
            raise Exception('Reminder not found')
        for key, value in kwargs.items():
            setattr(reminder, key, value)
        reminder.save()
        
        if 'slack_user_id' in kwargs:
            if kwargs['slack_user_id']:
                user_ids = [uid.strip() for uid in kwargs['slack_user_id'].split(',') if uid.strip()]
                users_to_add = get_user_model().objects.filter(id__in=user_ids)
                reminder.slack_users.set(users_to_add)
            else:
                reminder.slack_users.clear()
                
        return UpdateReminder(ok=True, reminder=reminder)


class DeleteReminder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        qs = Reminder.objects.all()
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        reminder = qs.filter(pk=id).first()
        if not reminder:
            raise Exception('Reminder not found')
        reminder.delete()
        return DeleteReminder(ok=True)


class CreateDepartment(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        company = graphene.ID(required=False)

    ok = graphene.Boolean()
    department = graphene.Field(DepartmentType)

    def mutate(root, info, name, company=None):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        # Security: Only allow users to create departments for their own company
        if not user.is_superuser:
            if not getattr(user, 'company_id', None):
                raise Exception('User must belong to a company to create departments')
            company = user.company.id  # Force user's company
        elif company and not user.is_superuser:
            # Even if company is specified, non-superusers can only use their own company
            company = user.company.id
        
        department = Department(name=name)
        if company:
            department.company_id = company
        department.save()
        return CreateDepartment(ok=True, department=department)


class UpdateDepartment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        company = graphene.ID(required=False)

    ok = graphene.Boolean()
    department = graphene.Field(DepartmentType)

    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = Department.objects.all()
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        department = qs.filter(pk=id).first()
        if not department:
            raise Exception('Department not found')
        
        # Security: Prevent non-superusers from changing company
        if not user.is_superuser and 'company' in kwargs:
            kwargs.pop('company')  # Remove company from updates for non-superusers
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(department, key, value)
        department.save()
        return UpdateDepartment(ok=True, department=department)


class DeleteDepartment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = Department.objects.all()
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        department = qs.filter(pk=id).first()
        if not department:
            raise Exception('Department not found')
        department.delete()
        return DeleteDepartment(ok=True)


class CreateSendGridDomainAuth(graphene.Mutation):
    class Arguments:
        domain = graphene.String(required=True)
        subdomain = graphene.String(required=False)
        customer_id = graphene.String(required=False)

    ok = graphene.Boolean()
    sendgrid_domain_auth = graphene.Field(SendGridDomainAuthType)

    def mutate(root, info, domain, subdomain="mail", customer_id=None):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        # Only superusers can create SendGrid domain auth
        if not user.is_superuser:
            raise Exception('Only superusers can create SendGrid domain authentication')
        
        sendgrid_auth = SendGridDomainAuth(
            user=user,
            domain=domain,
            subdomain=subdomain,
            customer_id=customer_id
        )
        sendgrid_auth.save()
        return CreateSendGridDomainAuth(ok=True, sendgrid_domain_auth=sendgrid_auth)


class UpdateSendGridDomainAuth(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        domain = graphene.String(required=False)
        subdomain = graphene.String(required=False)
        customer_id = graphene.String(required=False)
        is_verified = graphene.Boolean(required=False)

    ok = graphene.Boolean()
    sendgrid_domain_auth = graphene.Field(SendGridDomainAuthType)

    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = SendGridDomainAuth.objects.all()
        if not user.is_superuser:
            qs = qs.filter(user__company_id=user.company_id)
        sendgrid_auth = qs.filter(pk=id).first()
        if not sendgrid_auth:
            raise Exception('SendGrid domain auth not found')
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(sendgrid_auth, key, value)
        sendgrid_auth.save()
        return UpdateSendGridDomainAuth(ok=True, sendgrid_domain_auth=sendgrid_auth)


class DeleteSendGridDomainAuth(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = SendGridDomainAuth.objects.all()
        if not user.is_superuser:
            qs = qs.filter(user__company_id=user.company_id)
        sendgrid_auth = qs.filter(pk=id).first()
        if not sendgrid_auth:
            raise Exception('SendGrid domain auth not found')
        sendgrid_auth.delete()
        return DeleteSendGridDomainAuth(ok=True)


class CreateScheduledTask(graphene.Mutation):
    class Arguments:
        task_type = graphene.String(required=True)
        task_data = graphene.JSONString(required=False)
        scheduled_at = graphene.DateTime(required=True)
        company = graphene.ID(required=False)

    ok = graphene.Boolean()
    scheduled_task = graphene.Field(ScheduledTaskType)

    def mutate(root, info, task_type, scheduled_at, task_data=None, company=None):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        # Security: Only allow users to create tasks for their own company
        if not user.is_superuser:
            if not getattr(user, 'company_id', None):
                raise Exception('User must belong to a company to create scheduled tasks')
            company = user.company.id  # Force user's company
        
        scheduled_task = ScheduledTask(
            task_type=task_type,
            task_data=task_data or {},
            scheduled_at=scheduled_at,
            company_id=company
        )
        scheduled_task.save()
        return CreateScheduledTask(ok=True, scheduled_task=scheduled_task)


class UpdateScheduledTask(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        task_type = graphene.String(required=False)
        task_data = graphene.JSONString(required=False)
        scheduled_at = graphene.DateTime(required=False)
        executed_at = graphene.DateTime(required=False)
        is_completed = graphene.Boolean(required=False)

    ok = graphene.Boolean()
    scheduled_task = graphene.Field(ScheduledTaskType)

    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = ScheduledTask.objects.all()
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        scheduled_task = qs.filter(pk=id).first()
        if not scheduled_task:
            raise Exception('Scheduled task not found')
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(scheduled_task, key, value)
        scheduled_task.save()
        return UpdateScheduledTask(ok=True, scheduled_task=scheduled_task)


class DeleteScheduledTask(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        qs = ScheduledTask.objects.all()
        if not user.is_superuser and getattr(user, 'company_id', None):
            qs = qs.filter(company_id=user.company_id)
        scheduled_task = qs.filter(pk=id).first()
        if not scheduled_task:
            raise Exception('Scheduled task not found')
        scheduled_task.delete()
        return DeleteScheduledTask(ok=True)


# Permission and Role Mutations
class CreatePermission(graphene.Mutation):
    """Create a new permission (superuser only)"""
    class Arguments:
        code = graphene.String(required=True)
        name = graphene.String(required=True)
        category = graphene.String(required=True)
        description = graphene.String(required=False)
    
    ok = graphene.Boolean()
    permission = graphene.Field(PermissionType)
    
    def mutate(root, info, code, name, category, description=None):
        user = get_authenticated_user(info)
        if not user or not user.is_superuser:
            raise Exception('Only superusers can create permissions')
        
        permission = Permission.objects.create(
            code=code,
            name=name,
            category=category,
            description=description
        )
        return CreatePermission(ok=True, permission=permission)


class UpdatePermission(graphene.Mutation):
    """Update a permission (superuser only)"""
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        category = graphene.String(required=False)
        description = graphene.String(required=False)
        is_active = graphene.Boolean(required=False)
    
    ok = graphene.Boolean()
    permission = graphene.Field(PermissionType)
    
    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user or not user.is_superuser:
            raise Exception('Only superusers can update permissions')
        
        permission = Permission.objects.filter(pk=id).first()
        if not permission:
            raise Exception('Permission not found')
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(permission, key, value)
        permission.save()
        return UpdatePermission(ok=True, permission=permission)


class CreateRole(graphene.Mutation):
    """Create a new role"""
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String(required=False)
        company = graphene.ID(required=False)
        permission_ids = graphene.List(graphene.ID, required=False)
        is_system_role = graphene.Boolean(required=False)
    
    ok = graphene.Boolean()
    role = graphene.Field(RoleType)
    
    def mutate(root, info, name, description=None, company=None, permission_ids=None, is_system_role=False):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        # Only superusers can create system roles or roles for other companies
        if is_system_role or (company and company != user.company_id):
            if not user.is_superuser:
                raise Exception('Only superusers can create system roles or roles for other companies')
        
        # Determine company
        target_company = None
        if company:
            if user.is_superuser:
                target_company = Company.objects.filter(pk=company).first()
            else:
                target_company = user.company
        elif not is_system_role:
            # If not system role and no company specified, use user's company
            target_company = user.company
        
        role = Role.objects.create(
            name=name,
            description=description,
            company=target_company,
            is_system_role=is_system_role,
            created_by=user
        )
        
        # Add permissions
        if permission_ids:
            permissions = Permission.objects.filter(pk__in=permission_ids, is_active=True)
            role.permissions.set(permissions)
        
        return CreateRole(ok=True, role=role)


class UpdateRole(graphene.Mutation):
    """Update a role"""
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        description = graphene.String(required=False)
        permission_ids = graphene.List(graphene.ID, required=False)
        is_active = graphene.Boolean(required=False)
    
    ok = graphene.Boolean()
    role = graphene.Field(RoleType)
    
    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        role = Role.objects.filter(pk=id).first()
        if not role:
            raise Exception('Role not found')
        
        # Check permissions
        if role.is_system_role and not user.is_superuser:
            raise Exception('System roles can only be modified by superusers')
        if role.company and role.company_id != user.company_id and not user.is_superuser:
            raise Exception('Not authorized to modify this role')
        
        permission_ids = kwargs.pop('permission_ids', None)
        
        # Update fields
        for key, value in kwargs.items():
            if value is not None:
                setattr(role, key, value)
        role.save()
        
        # Update permissions if provided
        if permission_ids is not None:
            permissions = Permission.objects.filter(pk__in=permission_ids, is_active=True)
            role.permissions.set(permissions)
        
        return UpdateRole(ok=True, role=role)


class DeleteRole(graphene.Mutation):
    """Delete a role (soft delete by setting is_active=False)"""
    class Arguments:
        id = graphene.ID(required=True)
    
    ok = graphene.Boolean()
    
    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        role = Role.objects.filter(pk=id).first()
        if not role:
            raise Exception('Role not found')
        
        # Check permissions
        if role.is_system_role and not user.is_superuser:
            raise Exception('System roles can only be deleted by superusers')
        if role.company and role.company_id != user.company_id and not user.is_superuser:
            raise Exception('Not authorized to delete this role')
        
        # Soft delete
        role.is_active = False
        role.save()
        
        return DeleteRole(ok=True)


class AssignRoleToUser(graphene.Mutation):
    """Assign a role to a user"""
    class Arguments:
        user_id = graphene.ID(required=True)
        role_id = graphene.ID(required=True)
        notes = graphene.String(required=False)
    
    ok = graphene.Boolean()
    user_role = graphene.Field(UserRoleType)
    
    def mutate(root, info, user_id, role_id, notes=None):
        requester = get_authenticated_user(info)
        if not requester:
            raise Exception('Authentication required')
        
        # Check if requester has permission to assign roles
        if not requester.is_superuser:
            is_company_admin = requester.groups.filter(name__iexact='Company Admin').exists()
            if not is_company_admin:
                if not user_has_permission(requester, 'users.manage_roles'):
                    raise Exception('Not authorized to assign roles')
        
        # Get user and role
        UserModel = get_user_model()
        user = UserModel.objects.filter(pk=user_id).first()
        if not user:
            raise Exception('User not found')
        
        role = Role.objects.filter(pk=role_id, is_active=True).first()
        if not role:
            raise Exception('Role not found')
        
        # Determine company context
        company = user.company
        if not company:
            raise Exception('User must belong to a company')
        
        # Validate role belongs to same company (or is system role)
        if role.company and role.company != company and not requester.is_superuser:
            raise Exception('Role must belong to the same company as the user')
        
        # Create or update user role assignment
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            company=company,
            defaults={'assigned_by': requester, 'notes': notes}
        )
        
        if not created:
            # Reactivate if it was deactivated
            user_role.is_active = True
            user_role.assigned_by = requester
            if notes:
                user_role.notes = notes
            user_role.save()
        
        return AssignRoleToUser(ok=True, user_role=user_role)


class RemoveRoleFromUser(graphene.Mutation):
    """Remove a role from a user (soft delete)"""
    class Arguments:
        user_id = graphene.ID(required=True)
        role_id = graphene.ID(required=True)
    
    ok = graphene.Boolean()
    
    def mutate(root, info, user_id, role_id):
        requester = get_authenticated_user(info)
        if not requester:
            raise Exception('Authentication required')
        
        # Check permissions
        if not requester.is_superuser:
            is_company_admin = requester.groups.filter(name__iexact='Company Admin').exists()
            if not is_company_admin:
                if not user_has_permission(requester, 'users.manage_roles'):
                    raise Exception('Not authorized to remove roles')
        
        user_role = UserRole.objects.filter(
            user_id=user_id,
            role_id=role_id,
            is_active=True
        ).first()
        
        if not user_role:
            raise Exception('User role assignment not found')
        
        # Check company access
        if not requester.is_superuser and user_role.company_id != requester.company_id:
            raise Exception('Not authorized to remove this role')
        
        # Soft delete
        user_role.is_active = False
        user_role.save()
        
        return RemoveRoleFromUser(ok=True)


# Company Mutations
class CreateCompany(graphene.Mutation):
    """Create a new company (superuser only)"""
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=False)
        address = graphene.String(required=False)
        website = graphene.String(required=False)
        tax_identification = graphene.String(required=False)
    
    ok = graphene.Boolean()
    company = graphene.Field(CompanyType)
    
    def mutate(root, info, name, email=None, address=None, website=None, tax_identification=None):
        user = get_authenticated_user(info)
        if not user or not user.is_superuser:
            raise Exception('Only superusers can create companies')
        
        company = Company.objects.create(
            name=name,
            email=email or '',
            address=address or '',
            website=website or '',
            Tax_identification=tax_identification or ''
        )
        return CreateCompany(ok=True, company=company)


class UpdateCompany(graphene.Mutation):
    """Update a company"""
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String(required=False)
        email = graphene.String(required=False)
        address = graphene.String(required=False)
        website = graphene.String(required=False)
        tax_identification = graphene.String(required=False)
    
    ok = graphene.Boolean()
    company = graphene.Field(CompanyType)
    
    def mutate(root, info, id, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        company = Company.objects.filter(pk=id).first()
        if not company:
            raise Exception('Company not found')
        
        # Check permissions
        if not user.is_superuser:
            # Company admins can only update their own company
            if user.company_id != company.id:
                raise Exception('Not authorized to update this company')
            # Check permission
            from .models import user_has_permission
            if not user_has_permission(user, 'company.edit'):
                raise Exception('Permission denied: company.edit')
        
        # Update fields
        for key, value in kwargs.items():
            if value is not None:
                if key == 'tax_identification':
                    setattr(company, 'Tax_identification', value)
                else:
                    setattr(company, key, value)
        company.save()
        
        return UpdateCompany(ok=True, company=company)


class DeleteCompany(graphene.Mutation):
    """Delete a company (superuser only)"""
    class Arguments:
        id = graphene.ID(required=True)
    
    ok = graphene.Boolean()
    
    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user or not user.is_superuser:
            raise Exception('Only superusers can delete companies')
        
        company = Company.objects.filter(pk=id).first()
        if not company:
            raise Exception('Company not found')
        
        # Check if company has users
        UserModel = get_user_model()
        if UserModel.objects.filter(company=company).exists():
            raise Exception('Cannot delete company with existing users. Please reassign or delete users first.')
        
        company.delete()
        return DeleteCompany(ok=True)


# User Mutations (Update and Delete)
class UpdateUser(graphene.Mutation):
    """Update a user (admin only)"""
    class Arguments:
        id = graphene.ID(required=True)
        username = graphene.String(required=False)
        email = graphene.String(required=False)
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        department = graphene.ID(required=False)
        is_active = graphene.Boolean(required=False)
        company = graphene.ID(required=False)  # Superuser only
    
    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    
    def mutate(root, info, id, **kwargs):
        requester = get_authenticated_user(info)
        if not requester:
            raise Exception('Authentication required')
        
        UserModel = get_user_model()
        user = UserModel.objects.filter(pk=id).first()
        if not user:
            raise Exception('User not found')
        
        # Check permissions
        if not requester.is_superuser:
            is_company_admin = requester.groups.filter(name__iexact='Company Admin').exists()
            if not is_company_admin:
                from .models import user_has_permission
                if not user_has_permission(requester, 'users.edit'):
                    raise Exception('Permission denied: users.edit')
            
            # Company admins can only edit users in their company
            if user.company_id != requester.company_id:
                raise Exception('Not authorized to edit this user')
            
            # Company admins cannot change company
            kwargs.pop('company', None)
        
        # Handle department
        dept_id = kwargs.pop('department', None)
        if dept_id is not None:
            dept = Department.objects.filter(pk=dept_id).first()
            if not dept:
                raise Exception('Department not found')
            if not requester.is_superuser and dept.company_id != requester.company_id:
                raise Exception('Department must belong to the same company')
            user.department = dept
        
        # Handle company (superuser only)
        company_id = kwargs.pop('company', None)
        if company_id and requester.is_superuser:
            company = Company.objects.filter(pk=company_id).first()
            if company:
                user.company = company
        
        # Update other fields
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        
        user.save()
        return UpdateUser(ok=True, user=user)


class DeleteUser(graphene.Mutation):
    """Delete a user (admin only)"""
    class Arguments:
        id = graphene.ID(required=True)
    
    ok = graphene.Boolean()
    
    def mutate(root, info, id):
        requester = get_authenticated_user(info)
        if not requester:
            raise Exception('Authentication required')
        
        UserModel = get_user_model()
        user = UserModel.objects.filter(pk=id).first()
        if not user:
            raise Exception('User not found')
        
        # Cannot delete yourself
        if user.id == requester.id:
            raise Exception('Cannot delete your own account')
        
        # Check permissions
        if not requester.is_superuser:
            is_company_admin = requester.groups.filter(name__iexact='Company Admin').exists()
            if not is_company_admin:
                from .models import user_has_permission
                if not user_has_permission(requester, 'users.delete'):
                    raise Exception('Permission denied: users.delete')
            
            # Company admins can only delete users in their company
            if user.company_id != requester.company_id:
                raise Exception('Not authorized to delete this user')
        
        user.delete()
        return DeleteUser(ok=True)


# Permission Delete Mutation
class DeletePermission(graphene.Mutation):
    """Delete a permission (soft delete by setting is_active=False) - superuser only"""
    class Arguments:
        id = graphene.ID(required=True)
    
    ok = graphene.Boolean()
    
    def mutate(root, info, id):
        user = get_authenticated_user(info)
        if not user or not user.is_superuser:
            raise Exception('Only superusers can delete permissions')
        
        permission = Permission.objects.filter(pk=id).first()
        if not permission:
            raise Exception('Permission not found')
        
        # Soft delete
        permission.is_active = False
        permission.save()
        
        return DeletePermission(ok=True)


class Mutation(graphene.ObjectType):
    create_reminder = CreateReminder.Field()
    update_reminder = UpdateReminder.Field()
    delete_reminder = DeleteReminder.Field()
    create_department = CreateDepartment.Field()
    update_department = UpdateDepartment.Field()
    delete_department = DeleteDepartment.Field()
    create_sendgrid_domain_auth = CreateSendGridDomainAuth.Field()
    update_sendgrid_domain_auth = UpdateSendGridDomainAuth.Field()
    delete_sendgrid_domain_auth = DeleteSendGridDomainAuth.Field()
    create_scheduled_task = CreateScheduledTask.Field()
    update_scheduled_task = UpdateScheduledTask.Field()
    delete_scheduled_task = DeleteScheduledTask.Field()
    
    # User profile updates (current user) - handled above


class CreateUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=False)
        password = graphene.String(required=True)
        department = graphene.ID(required=False)
        is_active = graphene.Boolean(required=False)
        company = graphene.ID(required=False)  # Superuser only

    ok = graphene.Boolean()
    user = graphene.Field(UserType)

    def mutate(root, info, username, password, email=None, department=None, is_active=True, company=None):
        from .utils import is_rate_limited
        from django.conf import settings
        
        request = info.context
        if is_rate_limited(request, 'signup', settings.RATE_LIMIT_SIGNUP_PER_MINUTE):
            raise Exception('Too many signup attempts. Please try again later.')
        requester = get_authenticated_user(info)
        if not requester:
            raise Exception('Authentication required')

        # Permissions: superuser or company admin
        is_company_admin = False
        try:
            is_company_admin = requester.groups.filter(name__iexact='Company Admin').exists()
        except Exception:
            is_company_admin = False

        if not (requester.is_superuser or is_company_admin):
            raise Exception('Not authorized to create users')

        # Determine target company
        target_company_id = None
        if requester.is_superuser and company:
            target_company_id = company
        else:
            target_company_id = getattr(requester, 'company_id', None)
            if not target_company_id:
                raise Exception('Requester must belong to a company to create users')

        # Validate department (if provided)
        dept_obj = None
        if department is not None:
            dept_obj = Department.objects.filter(pk=department).first()
            if not dept_obj:
                raise Exception('Department not found')
            if getattr(dept_obj, 'company_id', None) != target_company_id:
                raise Exception('Department must belong to the target company')

        # Create user
        UserModel = get_user_model()
        new_user = UserModel.objects.create_user(
            username=username,
            email=email or '',
            password=password
        )
        try:
            new_user.company_id = target_company_id
        except Exception:
            pass
        if dept_obj:
            try:
                new_user.department = dept_obj
            except Exception:
                pass
        try:
            new_user.is_active = bool(is_active)
        except Exception:
            pass
        new_user.save()

        # Add to 'User' group
        try:
            user_group, _ = Group.objects.get_or_create(name='User')
            new_user.groups.add(user_group)
        except Exception:
            pass

        return CreateUser(ok=True, user=new_user)


class UpdateMe(graphene.Mutation):
    class Arguments:
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        email = graphene.String(required=False)
        department = graphene.ID(required=False)

    ok = graphene.Boolean()
    user = graphene.Field(UserType)

    def mutate(root, info, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')

        # If department change is requested, ensure it belongs to same company
        dept_id = kwargs.pop('department', None)
        if dept_id is not None:
            dept = Department.objects.filter(pk=dept_id).first()
            if not dept:
                raise Exception('Department not found')
            if not user.is_superuser:
                if getattr(user, 'company_id', None) != getattr(dept, 'company_id', None):
                    raise Exception('Cannot move to a department outside your company')
            user.department = dept

        if 'first_name' in kwargs:
            user.first_name = kwargs.get('first_name')
        if 'last_name' in kwargs:
            user.last_name = kwargs.get('last_name')
        if 'email' in kwargs:
            user.email = kwargs.get('email')
        
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        user.save()
        return UpdateMe(ok=True, user=user)


class Mutation(graphene.ObjectType):
    # Company mutations
    create_company = CreateCompany.Field()
    update_company = UpdateCompany.Field()
    delete_company = DeleteCompany.Field()
    
    # Reminder mutations
    create_reminder = CreateReminder.Field()
    update_reminder = UpdateReminder.Field()
    delete_reminder = DeleteReminder.Field()
    
    # Department mutations
    create_department = CreateDepartment.Field()
    update_department = UpdateDepartment.Field()
    delete_department = DeleteDepartment.Field()
    
    # User mutations
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()
    update_me = UpdateMe.Field()
    
    # SendGrid Domain Auth mutations
    create_sendgrid_domain_auth = CreateSendGridDomainAuth.Field()
    update_sendgrid_domain_auth = UpdateSendGridDomainAuth.Field()
    delete_sendgrid_domain_auth = DeleteSendGridDomainAuth.Field()
    
    # Scheduled Task mutations
    create_scheduled_task = CreateScheduledTask.Field()
    update_scheduled_task = UpdateScheduledTask.Field()
    delete_scheduled_task = DeleteScheduledTask.Field()
    
    # Permission and Role mutations
    create_permission = CreatePermission.Field()
    update_permission = UpdatePermission.Field()
    delete_permission = DeletePermission.Field()
    create_role = CreateRole.Field()
    update_role = UpdateRole.Field()
    delete_role = DeleteRole.Field()
    assign_role_to_user = AssignRoleToUser.Field()
    remove_role_from_user = RemoveRoleFromUser.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)



