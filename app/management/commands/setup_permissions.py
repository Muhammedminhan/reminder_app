"""
Management command to set up default permissions and roles.
Similar to Zoho Payroll's permission system initialization.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from app.models import Permission, Role, Company
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up default permissions and roles for the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset and recreate all permissions (WARNING: This will delete existing permissions)',
        )
        parser.add_argument(
            '--create-roles',
            action='store_true',
            help='Create default roles after creating permissions',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        create_roles = options.get('create_roles', False)

        if reset:
            self.stdout.write(self.style.WARNING('Resetting permissions...'))
            Permission.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('All permissions deleted.'))

        # Define default permissions
        permissions_data = [
            # Reminders
            {
                'code': 'reminders.create',
                'name': 'Create Reminders',
                'category': 'reminders',
                'description': 'Allow user to create new reminders'
            },
            {
                'code': 'reminders.view',
                'name': 'View Reminders',
                'category': 'reminders',
                'description': 'Allow user to view reminders'
            },
            {
                'code': 'reminders.edit',
                'name': 'Edit Reminders',
                'category': 'reminders',
                'description': 'Allow user to edit existing reminders'
            },
            {
                'code': 'reminders.delete',
                'name': 'Delete Reminders',
                'category': 'reminders',
                'description': 'Allow user to delete reminders'
            },
            {
                'code': 'reminders.send',
                'name': 'Send Reminders',
                'category': 'reminders',
                'description': 'Allow user to send reminders'
            },
            {
                'code': 'reminders.view_all',
                'name': 'View All Reminders',
                'category': 'reminders',
                'description': 'Allow user to view all reminders in the company (not just their own)'
            },
            {
                'code': 'reminders.approve',
                'name': 'Approve Reminders',
                'category': 'reminders',
                'description': 'Allow user to approve reminders created by subordinates'
            },
            
            # Users
            {
                'code': 'users.create',
                'name': 'Create Users',
                'category': 'users',
                'description': 'Allow user to create new users'
            },
            {
                'code': 'users.view',
                'name': 'View Users',
                'category': 'users',
                'description': 'Allow user to view user list and details'
            },
            {
                'code': 'users.edit',
                'name': 'Edit Users',
                'category': 'users',
                'description': 'Allow user to edit user information'
            },
            {
                'code': 'users.delete',
                'name': 'Delete Users',
                'category': 'users',
                'description': 'Allow user to delete users'
            },
            {
                'code': 'users.manage_roles',
                'name': 'Manage User Roles',
                'category': 'users',
                'description': 'Allow user to assign and remove roles from users'
            },
            {
                'code': 'users.activate_deactivate',
                'name': 'Activate/Deactivate Users',
                'category': 'users',
                'description': 'Allow user to activate or deactivate user accounts'
            },
            
            # Departments
            {
                'code': 'departments.create',
                'name': 'Create Departments',
                'category': 'departments',
                'description': 'Allow user to create new departments'
            },
            {
                'code': 'departments.view',
                'name': 'View Departments',
                'category': 'departments',
                'description': 'Allow user to view departments'
            },
            {
                'code': 'departments.edit',
                'name': 'Edit Departments',
                'category': 'departments',
                'description': 'Allow user to edit departments'
            },
            {
                'code': 'departments.delete',
                'name': 'Delete Departments',
                'category': 'departments',
                'description': 'Allow user to delete departments'
            },
            
            # Company Settings
            {
                'code': 'company.view',
                'name': 'View Company Settings',
                'category': 'company',
                'description': 'Allow user to view company settings'
            },
            {
                'code': 'company.edit',
                'name': 'Edit Company Settings',
                'category': 'company',
                'description': 'Allow user to edit company settings'
            },
            {
                'code': 'company.manage_domains',
                'name': 'Manage Domain Settings',
                'category': 'company',
                'description': 'Allow user to manage domain authentication and verification'
            },
            
            # Reports
            {
                'code': 'reports.view',
                'name': 'View Reports',
                'category': 'reports',
                'description': 'Allow user to view reports'
            },
            {
                'code': 'reports.export',
                'name': 'Export Reports',
                'category': 'reports',
                'description': 'Allow user to export reports'
            },
            
            # System Settings (Superuser only typically)
            {
                'code': 'settings.manage_permissions',
                'name': 'Manage Permissions',
                'category': 'settings',
                'description': 'Allow user to create and manage permissions (typically superuser only)'
            },
            {
                'code': 'settings.manage_roles',
                'name': 'Manage Roles',
                'category': 'settings',
                'description': 'Allow user to create and manage roles'
            },
        ]

        # Create permissions
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for perm_data in permissions_data:
            permission, created = Permission.objects.get_or_create(
                code=perm_data['code'],
                defaults={
                    'name': perm_data['name'],
                    'category': perm_data['category'],
                    'description': perm_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created permission: {permission.code}'))
            else:
                # Update existing permission
                permission.name = perm_data['name']
                permission.category = perm_data['category']
                permission.description = perm_data['description']
                permission.is_active = True
                permission.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated permission: {permission.code}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Permissions setup complete: {created_count} created, {updated_count} updated'
        ))

        # Create default roles if requested
        if create_roles:
            self.create_default_roles()

    def create_default_roles(self):
        """Create default system roles with appropriate permissions"""
        self.stdout.write(self.style.SUCCESS('\nCreating default roles...'))

        # Get all permissions
        all_perms = Permission.objects.filter(is_active=True)
        reminder_perms = all_perms.filter(category='reminders')
        user_perms = all_perms.filter(category='users')
        dept_perms = all_perms.filter(category='departments')
        company_perms = all_perms.filter(category='company')
        report_perms = all_perms.filter(category='reports')

        # 1. Employee Role (Basic user - can only view and create their own reminders)
        employee_role, created = Role.objects.get_or_create(
            name='Employee',
            company=None,  # System role
            defaults={
                'description': 'Basic employee role with limited permissions',
                'is_system_role': True,
                'is_active': True
            }
        )
        if created:
            employee_perms = reminder_perms.filter(code__in=['reminders.create', 'reminders.view'])
            employee_role.permissions.set(employee_perms)
            self.stdout.write(self.style.SUCCESS(f'✓ Created role: {employee_role.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'↻ Role already exists: {employee_role.name}'))

        # 2. Manager Role (Can manage reminders and view reports)
        manager_role, created = Role.objects.get_or_create(
            name='Manager',
            company=None,  # System role
            defaults={
                'description': 'Manager role with reminder management and reporting access',
                'is_system_role': True,
                'is_active': True
            }
        )
        if created:
            manager_perms = reminder_perms.filter(
                code__in=['reminders.create', 'reminders.view', 'reminders.edit', 
                         'reminders.delete', 'reminders.view_all']
            ) | report_perms.filter(code='reports.view')
            manager_role.permissions.set(manager_perms)
            self.stdout.write(self.style.SUCCESS(f'✓ Created role: {manager_role.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'↻ Role already exists: {manager_role.name}'))

        # 3. HR Manager Role (Can manage users, departments, and reminders)
        hr_manager_role, created = Role.objects.get_or_create(
            name='HR Manager',
            company=None,  # System role
            defaults={
                'description': 'HR Manager role with user and department management access',
                'is_system_role': True,
                'is_active': True
            }
        )
        if created:
            hr_perms = (
                reminder_perms.all() |
                user_perms.filter(code__in=['users.create', 'users.view', 'users.edit', 'users.manage_roles']) |
                dept_perms.all() |
                report_perms.all()
            )
            hr_manager_role.permissions.set(hr_perms)
            self.stdout.write(self.style.SUCCESS(f'✓ Created role: {hr_manager_role.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'↻ Role already exists: {hr_manager_role.name}'))

        # 4. Admin Role (Almost full access, except system settings)
        admin_role, created = Role.objects.get_or_create(
            name='Admin',
            company=None,  # System role
            defaults={
                'description': 'Admin role with full company management access',
                'is_system_role': True,
                'is_active': True
            }
        )
        if created:
            admin_perms = all_perms.exclude(category='settings')
            admin_role.permissions.set(admin_perms)
            self.stdout.write(self.style.SUCCESS(f'✓ Created role: {admin_role.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'↻ Role already exists: {admin_role.name}'))

        # 5. Subsidiary Role (Subordinate)
        subsidiary_role, created = Role.objects.get_or_create(
            name='Subsidiary',
            company=None,
            defaults={
                'description': 'Subsidiary role (subordinate) with create and view permissions',
                'is_system_role': True,
                'is_active': True
            }
        )
        if created:
            subsidiary_perms = reminder_perms.filter(code__in=['reminders.create', 'reminders.view'])
            subsidiary_role.permissions.set(subsidiary_perms)
            self.stdout.write(self.style.SUCCESS(f'✓ Created role: {subsidiary_role.name}'))

        # 6. Approver Role
        approver_role, created = Role.objects.get_or_create(
            name='Approver',
            company=None,
            defaults={
                'description': 'Approver role with create, view, and approve permissions',
                'is_system_role': True,
                'is_active': True
            }
        )
        if created:
            approver_perms = reminder_perms.filter(code__in=['reminders.create', 'reminders.view', 'reminders.approve'])
            approver_role.permissions.set(approver_perms)
            self.stdout.write(self.style.SUCCESS(f'✓ Created role: {approver_role.name}'))

        self.stdout.write(self.style.SUCCESS('\n✓ Default roles created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nYou can now assign these roles to users via:'))
        self.stdout.write(self.style.SUCCESS('  - Admin interface: /adrian-holovaty/app/userrole/'))
        self.stdout.write(self.style.SUCCESS('  - GraphQL: assignRoleToUser mutation'))

