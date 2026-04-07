# Permission and Role System (Zoho Payroll Style)

## Overview

A comprehensive Role-Based Access Control (RBAC) system similar to Zoho Payroll, allowing fine-grained permission management and role assignments for users.

## Features

### 1. **Permission Model**
- Custom permissions with unique codes (e.g., `reminders.create`, `users.manage_roles`)
- Categorized by type: Reminders, Users, Departments, Company Settings, Reports, System Settings
- Active/inactive status for soft deletion
- Superuser-only management

### 2. **Role Model**
- Roles group multiple permissions together
- Can be system-wide or company-specific
- System roles cannot be modified by company admins
- Tracks creator and creation date

### 3. **UserRole Model**
- Assigns roles to users within company context
- Users can have multiple roles
- Tracks who assigned the role and when
- Supports notes for audit trail

## Models

### Permission
```python
- code: Unique permission code (e.g., 'reminders.create')
- name: Human-readable name
- category: Permission category
- description: Detailed description
- is_active: Active status
```

### Role
```python
- name: Role name (e.g., 'HR Manager', 'Employee')
- description: Role description
- company: Company (null for system roles)
- permissions: Many-to-many relationship with Permission
- is_system_role: Whether it's a system role
- created_by: User who created the role
```

### UserRole
```python
- user: User being assigned the role
- role: Role being assigned
- company: Company context
- assigned_by: User who assigned the role
- is_active: Active status
- notes: Optional notes
```

## GraphQL API

### Queries

#### Get All Permissions
```graphql
query {
  permissions(category: "reminders") {
    id
    code
    name
    category
    description
  }
}
```

#### Get Permission by Code
```graphql
query {
  permission(code: "reminders.create") {
    id
    code
    name
  }
}
```

#### Get All Roles
```graphql
query {
  roles(company: "1") {
    id
    name
    description
    company { id name }
    permissions {
      id
      code
      name
    }
    permissionCount
  }
}
```

#### Get User Roles
```graphql
query {
  userRoles(user: "1", company: "1") {
    id
    user { id username }
    role { id name }
    company { id name }
    assignedBy { id username }
    assignedAt
    isActive
  }
}
```

#### Get My Permissions
```graphql
query {
  myPermissions
}
```

#### Get My Roles
```graphql
query {
  myRoles {
    id
    name
    description
    permissions {
      code
      name
    }
  }
}
```

### Mutations

#### Create Permission (Superuser Only)
```graphql
mutation {
  createPermission(
    code: "reminders.create"
    name: "Create Reminders"
    category: "reminders"
    description: "Allow user to create reminders"
  ) {
    ok
    permission {
      id
      code
      name
    }
  }
}
```

#### Create Role
```graphql
mutation {
  createRole(
    name: "HR Manager"
    description: "HR Manager role with full access"
    company: "1"
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

#### Update Role
```graphql
mutation {
  updateRole(
    id: "1"
    name: "Updated Role Name"
    permissionIds: ["1", "2", "3", "4"]
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

#### Assign Role to User
```graphql
mutation {
  assignRoleToUser(
    userId: "1"
    roleId: "1"
    notes: "Promoted to HR Manager"
  ) {
    ok
    userRole {
      id
      user { id username }
      role { id name }
      assignedAt
    }
  }
}
```

#### Remove Role from User
```graphql
mutation {
  removeRoleFromUser(
    userId: "1"
    roleId: "1"
  ) {
    ok
  }
}
```

## Admin Interface

### Permission Admin
- **Access**: Superuser only
- **Features**:
  - List all permissions with filtering by category
  - Create, edit, and manage permissions
  - Search by code, name, or description

### Role Admin
- **Access**: Superusers and Company Admins
- **Features**:
  - List roles (filtered by company for non-superusers)
  - Create company-specific or system roles
  - Assign permissions to roles using filter_horizontal widget
  - View permission count
  - Company admins can only modify their company's roles

### UserRole Admin
- **Access**: Superusers and Company Admins
- **Features**:
  - View all role assignments
  - Assign roles to users
  - Filter by company, user, or role
  - Track who assigned roles and when
  - Add notes to assignments

## Permission Checking

### Python Functions

```python
from app.models import user_has_permission, user_has_role, get_user_permissions

# Check if user has a specific permission
if user_has_permission(user, 'reminders.create'):
    # User can create reminders
    pass

# Check if user has a specific role
if user_has_role(user, 'HR Manager', company=company):
    # User has HR Manager role
    pass

# Get all permissions for a user
permissions = get_user_permissions(user)
```

### Permission Hierarchy

1. **Superusers**: Have all permissions automatically
2. **Company Admins**: Have all permissions for their company (backward compatibility)
3. **Role-based**: Users get permissions through assigned roles
4. **Direct permissions**: Can be added in the future if needed

## Default Permissions (To Be Created)

Recommended permission codes to create:

### Reminders
- `reminders.create` - Create reminders
- `reminders.view` - View reminders
- `reminders.edit` - Edit reminders
- `reminders.delete` - Delete reminders
- `reminders.send` - Send reminders

### Users
- `users.create` - Create users
- `users.view` - View users
- `users.edit` - Edit users
- `users.delete` - Delete users
- `users.manage_roles` - Assign/remove roles

### Departments
- `departments.create` - Create departments
- `departments.view` - View departments
- `departments.edit` - Edit departments
- `departments.delete` - Delete departments

### Company Settings
- `company.view` - View company settings
- `company.edit` - Edit company settings

### Reports
- `reports.view` - View reports
- `reports.export` - Export reports

## Migration

The migration file has been created:
- `app/migrations/0017_add_permission_role_system.py`

To apply:
```bash
python manage.py migrate
```

## Usage Examples

### Creating a Role for HR Managers

1. **Create Permissions** (Superuser):
```graphql
mutation {
  createPermission(code: "users.create", name: "Create Users", category: "users") {
    ok
  }
  createPermission(code: "users.view", name: "View Users", category: "users") {
    ok
  }
  createPermission(code: "reminders.create", name: "Create Reminders", category: "reminders") {
    ok
  }
}
```

2. **Create Role** (Company Admin or Superuser):
```graphql
mutation {
  createRole(
    name: "HR Manager"
    description: "Manages users and reminders"
    permissionIds: ["1", "2", "3"]  # IDs from step 1
  ) {
    ok
    role { id name }
  }
}
```

3. **Assign Role to User**:
```graphql
mutation {
  assignRoleToUser(
    userId: "5"
    roleId: "1"
    notes: "Promoted to HR Manager"
  ) {
    ok
  }
}
```

### Checking Permissions in Code

```python
from app.models import user_has_permission

def create_reminder(request):
    user = request.user
    if not user_has_permission(user, 'reminders.create'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    # Create reminder...
```

## Security Notes

1. **Superusers** have full access and can manage all permissions
2. **Company Admins** can manage roles and assignments for their company only
3. **System Roles** can only be modified by superusers
4. **Company-specific roles** are isolated per company
5. All operations are logged via auditlog

## Next Steps

1. Run migration: `python manage.py migrate`
2. Create default permissions via admin or GraphQL
3. Create default roles (e.g., "Employee", "Manager", "HR Manager")
4. Integrate permission checks into existing views/mutations
5. Update frontend to show/hide features based on permissions

## Integration with Existing Code

The system is backward compatible:
- Existing Company Admin group still works
- Superusers still have full access
- Can gradually migrate to permission-based checks

To integrate permission checks into existing mutations, add:

```python
from app.models import user_has_permission

def mutate(root, info, ...):
    user = get_authenticated_user(info)
    if not user_has_permission(user, 'reminders.create'):
        raise Exception('Permission denied: reminders.create')
    # ... rest of mutation
```

