# Complete API Coverage for All Models

## ✅ All Models Now Have Full CRUD API

### 1. Company
**Queries:**
- `companies` - List all companies
- `company(id)` - Get single company

**Mutations:**
- ✅ `createCompany` - Create new company (superuser only)
- ✅ `updateCompany` - Update company (superuser or company admin with permission)
- ✅ `deleteCompany` - Delete company (superuser only, checks for users)

### 2. Reminder
**Queries:**
- `reminders(active)` - List reminders (optionally filtered by active status)
- `reminder(id)` - Get single reminder

**Mutations:**
- ✅ `createReminder` - Create new reminder
- ✅ `updateReminder` - Update reminder
- ✅ `deleteReminder` - Delete reminder

### 3. Department
**Queries:**
- `departments` - List departments
- `department(id)` - Get single department

**Mutations:**
- ✅ `createDepartment` - Create new department
- ✅ `updateDepartment` - Update department
- ✅ `deleteDepartment` - Delete department

### 4. User
**Queries:**
- `me` - Get current user (with roles and permissions)
- `users` - List users
- `user(id)` - Get single user

**Mutations:**
- ✅ `createUser` - Create new user
- ✅ `updateUser` - Update user (admin only)
- ✅ `deleteUser` - Delete user (admin only, cannot delete self)
- ✅ `updateMe` - Update current user's own profile

### 5. SendGridDomainAuth
**Queries:**
- `sendgridDomainAuths` - List domain authentications
- `sendgridDomainAuth(id)` - Get single domain authentication

**Mutations:**
- ✅ `createSendGridDomainAuth` - Create new domain auth
- ✅ `updateSendGridDomainAuth` - Update domain auth
- ✅ `deleteSendGridDomainAuth` - Delete domain auth

### 6. ScheduledTask
**Queries:**
- `scheduledTasks(taskType, isCompleted)` - List scheduled tasks (with filters)
- `scheduledTask(id)` - Get single scheduled task

**Mutations:**
- ✅ `createScheduledTask` - Create new scheduled task
- ✅ `updateScheduledTask` - Update scheduled task
- ✅ `deleteScheduledTask` - Delete scheduled task

### 7. Permission
**Queries:**
- `permissions(category)` - List permissions (optionally filtered by category)
- `permission(id, code)` - Get permission by ID or code

**Mutations:**
- ✅ `createPermission` - Create new permission (superuser only)
- ✅ `updatePermission` - Update permission (superuser only)
- ✅ `deletePermission` - Delete permission (soft delete, superuser only)

### 8. Role
**Queries:**
- `roles(company)` - List roles (optionally filtered by company)
- `role(id)` - Get single role (with permissions)

**Mutations:**
- ✅ `createRole` - Create new role
- ✅ `updateRole` - Update role
- ✅ `deleteRole` - Delete role (soft delete)

### 9. UserRole
**Queries:**
- `userRoles(user, company)` - List user role assignments (with filters)
- `myRoles` - Get current user's roles

**Mutations:**
- ✅ `assignRoleToUser` - Assign role to user
- ✅ `removeRoleFromUser` - Remove role from user (soft delete)

## GraphQL Examples

### Company Operations

#### Create Company
```graphql
mutation {
  createCompany(
    name: "Acme Corp"
    email: "contact@acme.com"
    address: "123 Main St"
    website: "https://acme.com"
    taxIdentification: "TAX123"
  ) {
    ok
    company {
      id
      name
      email
    }
  }
}
```

#### Update Company
```graphql
mutation {
  updateCompany(
    id: "1"
    name: "Acme Corporation"
    email: "info@acme.com"
  ) {
    ok
    company {
      id
      name
      email
    }
  }
}
```

#### Delete Company
```graphql
mutation {
  deleteCompany(id: "1") {
    ok
  }
}
```

### User Operations

#### Update User
```graphql
mutation {
  updateUser(
    id: "1"
    email: "newemail@example.com"
    firstName: "John"
    lastName: "Doe"
    department: "2"
    isActive: true
  ) {
    ok
    user {
      id
      username
      email
      firstName
      lastName
    }
  }
}
```

#### Delete User
```graphql
mutation {
  deleteUser(id: "1") {
    ok
  }
}
```

### Permission Operations

#### Delete Permission
```graphql
mutation {
  deletePermission(id: "1") {
    ok
  }
}
```

## Permission Checks

All mutations include appropriate permission checks:

- **Company**: 
  - Create/Delete: Superuser only
  - Update: Superuser or company admin with `company.edit` permission

- **User**:
  - Create: Superuser or company admin
  - Update/Delete: Superuser, company admin, or user with `users.edit`/`users.delete` permission

- **Permission**:
  - All operations: Superuser only

- **Other models**: Check existing permission system or company admin status

## Summary

✅ **9 Models** - All have complete CRUD operations
✅ **27 Mutations** - Full create, update, delete coverage
✅ **18 Queries** - List and single item queries
✅ **Permission checks** - All mutations include proper authorization
✅ **Company isolation** - Non-superusers can only access their company's data

All models now have complete API coverage through GraphQL!

