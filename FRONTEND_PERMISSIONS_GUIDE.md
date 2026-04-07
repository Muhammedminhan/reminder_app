# Frontend RBAC Implementation Guide

**Constraint**: The backend logic is pre-configured. The frontend must implement role-based visibility and actions using the existing schema.

## 1. Permission Matrix (Frontend Logic)

The frontend must enforce these rules by checking `me.permissions`.

| Feature | Company Admin | Department Admin | User | Permission Check |
| :--- | :--- | :--- | :--- | :--- |
| **Manage Users** | ✅ Yes | ❌ No | ❌ No | `users.create`, `users.edit` |
| **Manage Departments** | ✅ Yes | ❌ No | ❌ No | `departments.create`, `departments.edit` |
| **View All Reminders** | ✅ Yes (Company) | ✅ Yes (Dept Only) | ✅ Yes (Dept Only) | `reminders.view_all` (CA), `reminders.view_department` (DA/User) |
| **Edit/Delete Reminders**| ✅ Yes (Company) | ✅ Yes (Dept Only) | ❌ Own Only | `reminders.manage_company` (CA), `reminders.manage_department` (DA) |

---

## 2. Required GraphQL Schema

### A. Fetching User Context
**Use Case**: On login, determine what UI elements to show.
```graphql
query GetUserContext {
  me {
    id
    username
    company { id name }
    department { id name }
    roles { name }
    permissions # <--- CRITICAL: Array of permission codes
  }
}
```

### B. Managing Users (Company Admin Only)
**Use Case**: Dashboard > Users > Add User
```graphql
mutation CreateUser($username: String!, $password: String!, $email: String!, $deptId: ID) {
  createUser(username: $username, password: $password, email: $email, department: $deptId) {
    ok
    user { id username }
  }
}
```

### C. Managing Departments (Company Admin Only)
**Use Case**: Dashboard > Departments > Add Department
```graphql
mutation CreateDepartment($name: String!) {
  createDepartment(name: $name) {
    ok
    department { id name }
  }
}
```

### D. Managing Reminders
**Use Case**: Dashboard > Reminders > Create/Edit

**Create Reminder (All Roles)**
```graphql
mutation AddReminder($title: String!, $senderEmail: String!, $receiverEmail: String!, $deptVisible: Boolean) {
  createReminder(
    title: $title, 
    senderEmail: $senderEmail, 
    receiverEmail: $receiverEmail,
    visibleToDepartment: $deptVisible
  ) {
    ok
    reminder { id }
  }
}
```

**Edit Reminder**
*Frontend Rule*: Only allow calling this if User is Owner OR User has `manage_department` (and target is in dept) OR User has `manage_company`.
```graphql
mutation EditReminder($id: ID!, $title: String, $active: Boolean) {
  updateReminder(id: $id, title: $title, active: $active) {
    ok
    reminder { id title }
  }
}
```

---

## 3. Implementation Checklist
1.  **Login**: Fetch `me { permissions, department { id } }`.
2.  **Dashboard**:
    *   Show **"Users"** tab IF `permissions.includes('users.create')`.
    *   Show **"Departments"** tab IF `permissions.includes('departments.create')`.
3.  **Reminders List**:
    *   Show **"Edit/Delete"** buttons on *other users' items* ONLY IF `permissions.includes('reminders.manage_department')` (and same dept) OR `permissions.includes('reminders.manage_company')`.

> **Note**: Since backend enforcement is permissive, the Frontend MUST STRICTLY hide these buttons to prevent unauthorized edits.
