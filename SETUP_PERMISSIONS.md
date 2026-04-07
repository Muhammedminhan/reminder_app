# Setting Up Permissions and Roles System

## Quick Start

After migrating the database, follow these steps to initialize the permission system:

### Step 1: Run the Migration

```bash
python manage.py migrate
```

This will create the `Permission`, `Role`, and `UserRole` tables.

### Step 2: Create Default Permissions

```bash
python manage.py setup_permissions
```

This command will:
- Create all default permissions (reminders, users, departments, company, reports, settings)
- Create default system roles (Employee, Manager, HR Manager, Admin)
- Assign appropriate permissions to each role

### Step 3: Verify Setup

Check that permissions were created:

```bash
python manage.py shell
```

```python
from app.models import Permission, Role

# Check permissions
print(f"Total permissions: {Permission.objects.count()}")
print(f"Active permissions: {Permission.objects.filter(is_active=True).count()}")

# Check roles
print(f"Total roles: {Role.objects.count()}")
for role in Role.objects.all():
    print(f"{role.name}: {role.permissions.count()} permissions")
```

## Command Options

### Create Permissions Only

```bash
python manage.py setup_permissions
```

### Create Permissions + Default Roles

```bash
python manage.py setup_permissions --create-roles
```

### Reset and Recreate Everything

⚠️ **WARNING**: This will delete all existing permissions!

```bash
python manage.py setup_permissions --reset --create-roles
```

## Default Permissions Created

### Reminders (6 permissions)
- `reminders.create` - Create reminders
- `reminders.view` - View reminders
- `reminders.edit` - Edit reminders
- `reminders.delete` - Delete reminders
- `reminders.send` - Send reminders
- `reminders.view_all` - View all company reminders

### Users (6 permissions)
- `users.create` - Create users
- `users.view` - View users
- `users.edit` - Edit users
- `users.delete` - Delete users
- `users.manage_roles` - Assign/remove roles
- `users.activate_deactivate` - Activate/deactivate users

### Departments (4 permissions)
- `departments.create` - Create departments
- `departments.view` - View departments
- `departments.edit` - Edit departments
- `departments.delete` - Delete departments

### Company Settings (3 permissions)
- `company.view` - View company settings
- `company.edit` - Edit company settings
- `company.manage_domains` - Manage domain settings

### Reports (2 permissions)
- `reports.view` - View reports
- `reports.export` - Export reports

### System Settings (2 permissions)
- `settings.manage_permissions` - Manage permissions (superuser only)
- `settings.manage_roles` - Manage roles

## Default Roles Created

### 1. Employee
**Permissions:**
- `reminders.create`
- `reminders.view`

**Description:** Basic employee with minimal access - can only create and view their own reminders.

### 2. Manager
**Permissions:**
- `reminders.create`
- `reminders.view`
- `reminders.edit`
- `reminders.delete`
- `reminders.view_all`
- `reports.view`

**Description:** Can manage all reminders and view reports.

### 3. HR Manager
**Permissions:**
- All reminder permissions
- `users.create`
- `users.view`
- `users.edit`
- `users.manage_roles`
- All department permissions
- All report permissions

**Description:** Can manage users, departments, reminders, and view reports.

### 4. Admin
**Permissions:**
- All permissions except system settings

**Description:** Full company management access (similar to Company Admin group).

## Assigning Roles to Users

### Via Admin Interface

1. Go to `/adrian-holovaty/app/userrole/`
2. Click "Add User Role Assignment"
3. Select user, role, and company
4. Add optional notes
5. Save

### Via GraphQL

```graphql
mutation {
  assignRoleToUser(
    userId: "1"
    roleId: "1"
    notes: "Promoted to Manager"
  ) {
    ok
    userRole {
      id
      user { username }
      role { name }
      assignedAt
    }
  }
}
```

### Check User Permissions

```graphql
query {
  me {
    id
    username
    roles {
      id
      name
      permissions {
        code
        name
      }
    }
    permissions
  }
}
```

## Creating Custom Roles

### Via Admin Interface

1. Go to `/adrian-holovaty/app/role/`
2. Click "Add Role"
3. Enter name and description
4. Select company (or leave blank for system role)
5. Select permissions
6. Save

### Via GraphQL

```graphql
mutation {
  createRole(
    name: "Custom Role"
    description: "My custom role"
    permissionIds: ["1", "2", "3"]
  ) {
    ok
    role {
      id
      name
      permissions {
        code
        name
      }
    }
  }
}
```

## Integration Checklist

- [x] Run migration
- [x] Run `setup_permissions` command
- [ ] Assign roles to existing users
- [ ] Update frontend to check permissions
- [ ] Add permission checks to GraphQL mutations
- [ ] Test permission system

## Next Steps

1. **Assign Roles to Existing Users**
   - Use admin interface or GraphQL to assign appropriate roles
   - Company Admins can be assigned "Admin" role for backward compatibility

2. **Update Frontend**
   - Use `myPermissions` query to get user permissions
   - Show/hide features based on permissions
   - Example: Only show "Create User" button if user has `users.create` permission

3. **Add Permission Checks to Mutations**
   ```python
   from app.models import user_has_permission
   
   def mutate(root, info, ...):
       user = get_authenticated_user(info)
       if not user_has_permission(user, 'reminders.create'):
           raise Exception('Permission denied: reminders.create')
       # ... rest of mutation
   ```

4. **Test the System**
   - Create test users with different roles
   - Verify permissions work correctly
   - Test role assignments and removals

## Troubleshooting

### Permissions Not Showing Up

1. Check if permissions are active:
   ```python
   Permission.objects.filter(is_active=True).count()
   ```

2. Check if user has active roles:
   ```python
   from app.models import UserRole
   UserRole.objects.filter(user=user, is_active=True).count()
   ```

### Roles Not Working

1. Verify role has permissions assigned:
   ```python
   role = Role.objects.get(name="Manager")
   role.permissions.count()
   ```

2. Check if role is active:
   ```python
   role.is_active
   ```

### Company Admins Not Getting Permissions

Company Admins automatically get all permissions (backward compatibility). If they're not getting permissions, check:
- User is in "Company Admin" group
- User has a company assigned

## Support

For issues or questions:
1. Check `PERMISSION_ROLE_SYSTEM.md` for detailed documentation
2. Review GraphQL schema in `app/schema.py`
3. Check admin interface at `/adrian-holovaty/`

