# Next Steps After Migration

## ✅ Completed Steps

1. ✓ Migration created and applied
2. ✓ Default permissions created (23 permissions)
3. ✓ Default roles created (4 roles: Employee, Manager, HR Manager, Admin)
4. ✓ GraphQL API updated with permission/role queries and mutations
5. ✓ Admin interface configured for managing permissions and roles
6. ✓ UserType updated to include roles and permissions

## 🎯 Immediate Next Steps

### 1. Assign Roles to Existing Users

You can assign roles to users in two ways:

#### Option A: Via Admin Interface
1. Navigate to: `/adrian-holovaty/app/userrole/`
2. Click "Add User Role Assignment"
3. Select user, role, and company
4. Save

#### Option B: Via GraphQL
```graphql
mutation {
  assignRoleToUser(
    userId: "1"
    roleId: "1"
    notes: "Initial role assignment"
  ) {
    ok
    userRole {
      id
      user { username }
      role { name }
    }
  }
}
```

**Tip:** Find role IDs:
```graphql
query {
  roles {
    id
    name
    description
  }
}
```

### 2. Test the Permission System

#### Check User Permissions
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

#### Test Permission Checking
```python
from app.models import user_has_permission, get_user_permissions

user = User.objects.get(username='testuser')
print(f"Has reminders.create: {user_has_permission(user, 'reminders.create')}")
print(f"All permissions: {get_user_permissions(user)}")
```

### 3. Update Frontend Integration

#### Get User Permissions on Login
```javascript
const getUserPermissions = async (token) => {
  const response = await fetch(`${API_BASE}/graphql/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: `
        query {
          me {
            id
            username
            permissions
            roles {
              id
              name
            }
          }
        }
      `
    })
  });
  
  const result = await response.json();
  return result.data.me;
};
```

#### Show/Hide Features Based on Permissions
```javascript
const canCreateReminders = user.permissions.includes('reminders.create');
const canManageUsers = user.permissions.includes('users.create');

// In your component
{canCreateReminders && (
  <button onClick={createReminder}>Create Reminder</button>
)}

{canManageUsers && (
  <button onClick={createUser}>Add User</button>
)}
```

### 4. Add Permission Checks to Existing Mutations

Update your GraphQL mutations to check permissions:

```python
# In app/schema.py, update CreateReminder mutation
from app.models import user_has_permission

class CreateReminder(graphene.Mutation):
    def mutate(root, info, **kwargs):
        user = get_authenticated_user(info)
        if not user:
            raise Exception('Authentication required')
        
        # Add permission check
        if not user_has_permission(user, 'reminders.create'):
            raise Exception('Permission denied: reminders.create')
        
        # ... rest of mutation
```

Apply this pattern to:
- `CreateReminder` → check `reminders.create`
- `UpdateReminder` → check `reminders.edit`
- `DeleteReminder` → check `reminders.delete`
- `CreateUser` → check `users.create`
- `UpdateUser` → check `users.edit`
- `CreateDepartment` → check `departments.create`
- etc.

### 5. Migrate Existing Company Admins

If you have users in the "Company Admin" group, you can:

**Option A:** Keep them as-is (they automatically get all permissions)

**Option B:** Assign them the "Admin" role for consistency:
```graphql
# Get Admin role ID first
query {
  roles(name: "Admin") {
    id
  }
}

# Then assign to all company admins
mutation {
  assignRoleToUser(userId: "1", roleId: "2") {
    ok
  }
}
```

## 📋 Permission Reference

### Reminder Permissions
- `reminders.create` - Create new reminders
- `reminders.view` - View reminders
- `reminders.edit` - Edit reminders
- `reminders.delete` - Delete reminders
- `reminders.send` - Send reminders
- `reminders.view_all` - View all company reminders (not just own)

### User Permissions
- `users.create` - Create users
- `users.view` - View user list
- `users.edit` - Edit users
- `users.delete` - Delete users
- `users.manage_roles` - Assign/remove roles
- `users.activate_deactivate` - Activate/deactivate users

### Department Permissions
- `departments.create` - Create departments
- `departments.view` - View departments
- `departments.edit` - Edit departments
- `departments.delete` - Delete departments

### Company Permissions
- `company.view` - View company settings
- `company.edit` - Edit company settings
- `company.manage_domains` - Manage domain authentication

### Report Permissions
- `reports.view` - View reports
- `reports.export` - Export reports

## 🔧 Management Commands

### View All Permissions
```bash
python manage.py shell
```
```python
from app.models import Permission
for p in Permission.objects.all():
    print(f"{p.code}: {p.name}")
```

### View All Roles
```python
from app.models import Role
for r in Role.objects.all():
    print(f"{r.name}: {r.permissions.count()} permissions")
```

### Create Custom Permission
```python
from app.models import Permission
Permission.objects.create(
    code='custom.permission',
    name='Custom Permission',
    category='settings',
    description='My custom permission'
)
```

### Create Custom Role
```python
from app.models import Role, Permission

# Get permissions
perms = Permission.objects.filter(code__in=['reminders.create', 'reminders.view'])

# Create role
role = Role.objects.create(
    name='Custom Role',
    description='My custom role',
    company=None  # System role
)
role.permissions.set(perms)
```

## 📚 Documentation Files

- `PERMISSION_ROLE_SYSTEM.md` - Complete system documentation
- `SETUP_PERMISSIONS.md` - Setup and initialization guide
- `NEXT_STEPS.md` - This file

## 🎉 You're Ready!

The permission system is now fully set up and ready to use. Start by:
1. Assigning roles to your users
2. Testing permissions in GraphQL
3. Integrating permission checks into your frontend
4. Adding permission checks to mutations

For questions or issues, refer to the documentation files or check the admin interface at `/adrian-holovaty/`.

