# 🛡️ NotifyHub Admin Panel — Comprehensive Guide

> **Audience:** Superusers and Staff administrators of the NotifyHub platform.  
> **Last updated:** June 2026

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Access & Login](#access--login)
3. [Admin Tabs Reference](#admin-tabs-reference)
   - [Users](#1-users)
   - [Departments](#2-departments)
   - [Roles & Permissions](#3-roles--permissions)
   - [Companies](#4-companies)
   - [Reminders](#5-reminders)
   - [OAuth Apps](#6-oauth-apps)
   - [User Roles](#7-user-roles)
   - [SendGrid](#8-sendgrid)
   - [Audit Log](#9-audit-log)
   - [Access Tokens](#10-access-tokens)
   - [Permissions](#11-permissions)
4. [How to Make Someone a Superuser](#how-to-make-someone-a-superuser)
5. [Common Admin Tasks](#common-admin-tasks)
6. [Security Notes](#security-notes)

---

## 🔭 Overview

The **Admin Panel** is a superuser-only section inside NotifyHub's Settings page. It provides full visibility and control over all entities in the system — users, companies, departments, roles, permissions, reminders, OAuth integrations, email domain authentication, and audit trails.

The panel is **built directly into the frontend dashboard** (not a separate Django `/admin` interface) and communicates entirely through the GraphQL API at `/graphql/`.

### Who can access it?

| Role | Access Level |
|------|-------------|
| `isSuperuser = True` | Full access to all 11 admin tabs |
| `isStaff = True` | Full access to all 11 admin tabs (same as superuser for this panel) |
| Regular user | Cannot see the Admin tab at all |

The Admin tab only appears in **Settings → Admin** when the logged-in user has `isSuperuser` or `isStaff` set to `true`.

---

## 🔐 Access & Login

### How to reach the Admin Panel

1. Log in to NotifyHub at your deployment URL (e.g., `https://app.notifyhub.yougotagift.com`)
2. In the left sidebar, click **Settings** (gear icon)
3. In the Settings top navigation, click the **Admin** tab (only visible to superusers/staff)
4. The Admin sub-panel opens with 11 tabs along the top

### Credentials format

```
Username: <your_admin_username>
Password: <your_password>
```

Authentication uses JWT Bearer tokens. After login, the token is stored in `localStorage` as `access_token` and sent with every API request.

### First superuser setup (shell)

If no superuser exists yet, create one via Django management commands on the server:

```bash
python manage.py createsuperuser
```

Or promote an existing user:

```python
python manage.py shell
>>> from app.models import User
>>> u = User.objects.get(username='yourusername')
>>> u.is_superuser = True
>>> u.is_staff = True
>>> u.save()
```

---

## 🗂️ Admin Tabs Reference

### 1. 👤 Users

**What it shows:** A full list of all users in the workspace (scoped to the admin's company for staff; all users for superusers). Each row shows the user's avatar initial, full name, `@username`, email, and status badges.

**Status badges:**
- 🔴 `Superuser` — user has `isSuperuser = true`
- 🔵 `Staff` — user has `isStaff = true` (but not superuser)
- ⚫ `Inactive` — user's account is disabled (`isActive = false`)

**Available actions:**

| Action | Description |
|--------|-------------|
| **Create User** | Opens an inline form to create a new user |
| **Toggle Active / Inactive** | Lock/unlock icon — enables or disables the user's account instantly |
| **Delete User** | Permanently deletes the user (soft delete — sets `is_deleted = true` and `is_active = false`). You cannot delete your own account. |

**Create User form fields:**

| Field | Required | Notes |
|-------|----------|-------|
| Username | Yes | Must be unique across the platform |
| Email | No | Used for notifications |
| Password | Yes | Minimum 8 characters recommended |
| First Name | No | Display name |
| Last Name | No | Display name |
| Staff checkbox | No | Grants staff privileges (sees Admin tab) |
| Superuser checkbox | No | Grants full platform control |

> **Note:** New users are automatically added to the `User` Django group. The company is automatically set to the creating admin's company.

---

### 2. 🏢 Departments

**What it shows:** All departments in the system, displayed as a grid of cards. Each card shows the department name and a delete button.

**Available actions:**

| Action | Description |
|--------|-------------|
| **New Department** | Opens an inline form with a single name field |
| **Delete Department** | Permanently removes the department (confirmation required) |

**Create Department form fields:**

| Field | Required | Notes |
|-------|----------|-------|
| Department Name | Yes | Must be unique within a company (e.g., "Engineering", "HR") |

> **Note:** Departments are scoped to the admin's company automatically. A superuser creating a department will associate it with their own company. The combination of `name + company` must be unique.

---

### 3. 🛡️ Roles & Permissions

**What it shows:** All active roles in the system. Each role card shows the role name, an optional description, and the list of permissions currently assigned to that role as blue badge tags.

**Available actions:**

| Action | Description |
|--------|-------------|
| **New Role** | Opens an inline form to define a new role |
| **Delete Role** | Soft-deletes the role (sets `is_active = false`) — confirmation required |

**Create Role form fields:**

| Field | Required | Notes |
|-------|----------|-------|
| Role Name | Yes | E.g., `HR Manager`, `Viewer`, `Department Head` |
| Description | No | Human-readable explanation of what this role can do |

> **Note:** To assign permissions to a role after creation, use the GraphQL API directly (the UI creates roles without permissions; permissions can be added via `updateRole` mutation with `permissionIds`). Seed default roles using:
> ```bash
> python manage.py setup_permissions --create-roles
> ```

> **System roles** (`is_system_role = true`) cannot be deleted or modified by company admins — only superusers can change them.

---

### 4. 🏗️ Companies

**What it shows:** All registered companies. Each row shows the company initial avatar, name, email, website link, and counts of departments and users.

**Available actions:**

| Action | Description |
|--------|-------------|
| **Add Company** | Opens an inline form to register a new company |
| **Delete Company** | Permanently deletes a company (only if it has no users) |

**Create Company form fields:**

| Field | Required | Notes |
|-------|----------|-------|
| Company Name | Yes | E.g., `Acme Corp` |
| Email | No | Primary contact email for the company |
| Address | No | Physical address |
| Website | No | Must be a valid URL (e.g., `https://company.com`) |

> **Restriction:** A company cannot be deleted if it has any users assigned to it. You must reassign or delete all users first. This action is **superuser-only**.

---

### 5. 🔔 Reminders

**What it shows:** A read-only table of all reminders across all companies (superuser view). Columns include: Title, Recipient (email), Company, Status, Cadence (interval type), and Created By.

**Status badges:**
- 🟢 `Active` — reminder is active and not completed
- ✅ `Completed` — reminder has been marked as done
- 🔴 `Inactive` — reminder has been paused (`active = false`)

**Available actions:**

This tab is **read-only** in the admin panel. No add/edit/delete buttons are present. To manage individual reminders, use the main Notifications view.

**Columns displayed:**

| Column | Description |
|--------|-------------|
| Title | Reminder title (truncated if long) |
| Recipient | Receiver email address(es) |
| Company | Company the reminder belongs to |
| Status | Active / Completed / Inactive |
| Cadence | Interval type (daily, weekly, monthly, etc.) |
| Created By | Username of the creator |

---

### 6. 🔑 OAuth Apps

**What it shows:** All registered OAuth 2.0 applications (from `django-oauth-toolkit`). Displayed as a list of cards with the app name, a partially masked client ID (first 8 + last 4 characters), client type badge, and authorization grant type badge.

**Available actions:**

This tab is **read-only**. OAuth applications must be created and managed via the Django admin at `/admin/oauth2_provider/application/` or via the OAuth toolkit's API.

**Columns displayed:**

| Column | Description |
|--------|-------------|
| Name | Application name |
| Client ID | Masked (e.g., `abcd1234••••••••5678`) |
| Client Type | `confidential` or `public` |
| Authorization Grant Type | E.g., `authorization-code`, `client-credentials`, `password` |

---

### 7. 👥 User Roles

**What it shows:** All active user-to-role assignments. A table listing the user (username + email), the assigned role, the company context, assignment status, and when it was assigned.

**Available actions:**

| Action | Description |
|--------|-------------|
| **Assign Role** | Opens a form with dropdowns to pick a user and a role |
| **Remove** | Soft-removes the role assignment (`is_active = false`) |

**Assign Role form fields:**

| Field | Required | Notes |
|-------|----------|-------|
| User | Yes | Dropdown of all users in the workspace |
| Role | Yes | Dropdown of all active roles |

> **Note:** A user must belong to a company before a role can be assigned to them. The role must belong to the same company as the user, or be a system-wide role (`company = null`). Re-assigning an already-assigned role simply reactivates it.

---

### 8. 📧 SendGrid

**What it shows:** All SendGrid domain authentication records. These are used to configure custom sending domains so that reminder emails are delivered from a company's own domain (e.g., `noreply@company.com`).

**Available actions:**

This tab is **read-only** in the admin panel. Domain auth records are created via the `createSendGridDomainAuth` GraphQL mutation (superuser only) or via the Django admin.

**Columns displayed:**

| Column | Description |
|--------|-------------|
| Domain | The configured sending domain (e.g., `notifyhub.company.com`) |
| Customer ID | Optional customer identifier linked to this domain |
| Verified | `Verified` (green) or `Pending` (yellow) |
| User | The superuser who created this record |
| Created At | Date the record was created |

> **Note:** Domain names must follow the format `notifyhub.<customer-domain>.com`. Only superusers can create domain auth records.

---

### 9. 📜 Audit Log

**What it shows:** The last 50 audit log entries across the entire platform (powered by `django-auditlog`). All model changes — creates, updates, and deletes — are automatically captured.

**Available actions:**

This tab is **read-only**. The audit log cannot be modified from the UI.

**Columns displayed:**

| Column | Description |
|--------|-------------|
| Actor | Username of the person who performed the action |
| Action | Color-coded badge: 🟢 Create / 🔵 Update / 🔴 Delete |
| Object | String representation of the affected record |
| Type | Model name (e.g., `Reminder`, `User`, `Department`) |
| Timestamp | Date and time of the action |

**Models tracked by audit log:**
`User`, `Company`, `Reminder`, `Department`, `Group`, `ReminderDelivery`, `JiraIntegration`, `CompanySSOSettings`, `Permission`, `Role`, `ReminderAttachment`, `ScheduledTask`, `Comment`, `UserRole`

---

### 10. 🎫 Access Tokens

**What it shows:** The most recent 100 OAuth access tokens issued by the platform. Token values are masked for security (first 8 characters + `••••`).

**Available actions:**

This tab is **read-only**. Token revocation must be done via the Django admin or the OAuth toolkit API.

**Columns displayed:**

| Column | Description |
|--------|-------------|
| User | Username the token was issued to |
| Token | Masked token value (e.g., `abcd1234••••`) |
| Expires | Token expiration date and time |
| Scope | OAuth scopes granted to this token |

---

### 11. 🔒 Permissions

**What it shows:** All active custom permissions defined in the system. A table listing the permission code, name, category badge, active status, and a delete button.

**Available actions:**

| Action | Description |
|--------|-------------|
| **Create Permission** | Opens an inline form to define a new permission |
| **Delete** | Soft-deletes the permission (`is_active = false`) — confirmation required. **Superuser only.** |

**Create Permission form fields:**

| Field | Required | Notes |
|-------|----------|-------|
| Code | Yes | Unique dot-notation identifier (e.g., `users.manage_roles`, `reminders.approve`) |
| Name | Yes | Human-readable label (e.g., "Manage User Roles") |
| Category | Yes | One of: `reminders`, `users`, `departments`, `company`, `reports`, `settings` |
| Description | No | Optional explanation of what this permission grants |

**Columns displayed:**

| Column | Description |
|--------|-------------|
| Code | Machine-readable permission code (monospace) |
| Name | Human-readable name |
| Category | Color-coded category badge |
| Status | Active (green) or Inactive (red) |
| Action | Delete button (superuser only) |

---

## 🚀 How to Make Someone a Superuser

### Option A — Via the Admin Panel UI (recommended)

You cannot directly set `isSuperuser` from the UI on an existing user (the toggle only controls `isActive`). Use Option B or C for this.

### Option B — Via Django Shell (server access required)

```bash
# SSH into your server or Cloud Run instance, then:
python manage.py shell

>>> from app.models import User
>>> u = User.objects.get(username='target_username')
>>> u.is_superuser = True
>>> u.is_staff = True   # Also grant staff to ensure Admin tab appears
>>> u.save()
>>> print(f"Done. {u.username} is now superuser: {u.is_superuser}")
```

### Option C — Via Django Admin (if `/admin` is accessible)

1. Go to `https://your-domain.com/admin/`
2. Log in with an existing superuser account
3. Navigate to **App → Users**
4. Find the user and open their record
5. Check both **Superuser status** and **Staff status**
6. Click **Save**

### Option D — Create a new superuser from scratch

```bash
python manage.py createsuperuser
# Follow prompts for username, email, password
```

---

## 📖 Common Admin Tasks

### ➕ Creating a New Company

1. Go to **Settings → Admin → Company** tab
2. Click **Add Company**
3. Fill in the form:
   - **Company Name** (required): e.g., `Acme Corp`
   - **Email**: e.g., `hello@acme.com`
   - **Address**: e.g., `123 Main St, Dubai`
   - **Website**: e.g., `https://acme.com`
4. Click **Save Company**
5. The new company will appear in the list immediately

---

### 👤 Creating a New User and Assigning Them to a Company

1. Go to **Settings → Admin → Users** tab
2. Click **Create User**
3. Fill in the form:
   - **Username** (required): unique identifier
   - **Email**: user's work email
   - **Password** (required): temporary password (user should change on first login)
   - **First Name / Last Name**: display name
   - **Staff / Superuser**: leave unchecked for regular users
4. Click **Save User**
5. The user is automatically assigned to the **same company as the creating admin**

> To assign a user to a *different* company, use the GraphQL mutation directly:
> ```graphql
> mutation {
>   createUser(
>     username: "jdoe"
>     email: "jdoe@othercorp.com"
>     password: "securepass123"
>     companyId: "<company_uuid>"
>   ) {
>     ok
>     user { id username }
>   }
> }
> ```

---

### 🏢 Creating a Department and Adding Users to It

**Step 1 — Create the department:**

1. Go to **Settings → Admin → Departments** tab
2. Click **New Department**
3. Enter the department name (e.g., `Engineering`)
4. Click **Save**

**Step 2 — Add users to the department:**

The Admin UI does not currently have a direct "add user to department" button in the Departments tab. Use one of these methods:

- **Via Users tab:** When creating a new user, pass `departmentIds` via GraphQL
- **Via GraphQL mutation:**
  ```graphql
  mutation {
    updateUser(id: "<user_uuid>", departmentIds: ["<dept_uuid>"]) {
      ok
      user { username departments { name } }
    }
  }
  ```
- **Via Django admin:** Go to `/admin/app/user/`, open the user, and assign departments in the M2M field

---

### 🛡️ Creating a Role and Assigning Permissions

**Step 1 — Create the role:**

1. Go to **Settings → Admin → Roles** tab
2. Click **New Role**
3. Enter:
   - **Role Name**: e.g., `HR Manager`
   - **Description**: e.g., `Can manage users and view reports`
4. Click **Save Role**

**Step 2 — Assign permissions to the role (via GraphQL):**

```graphql
# First, get permission IDs from the Permissions tab or:
query { permissions { id code name } }

# Then update the role with permission IDs:
mutation {
  updateRole(
    id: "<role_uuid>"
    permissionIds: ["<perm_uuid_1>", "<perm_uuid_2>"]
  ) {
    ok
    role { name permissions { code name } }
  }
}
```

---

### 👥 Assigning a Role to a User

1. Go to **Settings → Admin → User Roles** tab
2. Click **Assign Role**
3. Select the **User** from the dropdown (shows `username (email)`)
4. Select the **Role** from the dropdown
5. Click **Assign**
6. The new assignment appears in the table with an `Active` badge

> To remove a role: click the **Remove** button in the corresponding row. The assignment is soft-deleted (not permanently removed).

---

### 🔍 Viewing and Filtering Reminders

**Via Admin Panel (read-only view):**

1. Go to **Settings → Admin → Reminders** tab
2. The table shows all reminders across all companies
3. Use browser `Ctrl+F` to search within the visible table

**Via main Notifications view (with filters):**

1. Click **Notifications** in the left sidebar
2. Click the **Filters** button (funnel icon) to open the filter dropdown:
   - **All Triggers** — shows everything
   - **Active Only** — shows only non-completed reminders
   - **Finalized Only** — shows only completed reminders
3. Use the **Search** bar at the top to filter by title, sender email, or receiver email

---

## 🔒 Security Notes

### What superusers CAN do

- Create, update, and soft-delete any user (except themselves)
- Create and delete companies (subject to restrictions)
- Create and manage departments for any company
- Create, update, and soft-delete roles and permissions
- Assign and remove roles from any user
- View all reminders across all companies
- View all OAuth applications and access tokens (read-only)
- View the full audit log (read-only)
- Create SendGrid domain authentication records
- Access the GraphQL API with unrestricted query scope

### What superusers CANNOT do

- **Delete a company that has users** — companies with existing users cannot be deleted; you must first reassign or delete all users
- **Delete their own account** — the `deleteUser` mutation explicitly blocks self-deletion
- **Modify the audit log** — the audit log is strictly append-only and read-only through the UI
- **View or copy full OAuth access tokens** — tokens are masked in the UI (first 8 chars + `••••`); full token values are never exposed after issuance
- **Bypass rate limiting** — signup/creation endpoints are rate-limited even for admins

### Staff vs Superuser distinction (in the Admin Panel)

Both `isStaff` and `isSuperuser` users see all 11 Admin tabs. However, at the **GraphQL resolver level**, some operations are restricted to `isSuperuser` only:

| Operation | Required Role |
|-----------|--------------|
| Create company | `isSuperuser` only |
| Delete company | `isSuperuser` only |
| Create SendGrid domain auth | `isSuperuser` only |
| Create/delete permissions | `isSuperuser` only |
| Modify system roles | `isSuperuser` only |
| View OAuth apps & access tokens | `isSuperuser` or `isStaff` |
| View audit log | `isSuperuser` or `isStaff` |

### Role deletion is a soft delete

Deleting a role via the Admin Panel sets `is_active = false` — it does **not** permanently remove it from the database. Existing `UserRole` assignments for that role remain in the database but will no longer be active.

### Data scoping for non-superuser staff

Staff users (`isStaff = true` but `isSuperuser = false`) see data scoped to **their own company** in most GraphQL resolvers. Only true superusers (`isSuperuser = true`) can see cross-company data (e.g., all companies, all users globally).

### Audit trail

Every create, update, and delete action on core models is automatically logged to the Audit Log. Admin actions are attributed to the actor's username and include a timestamp and object representation. This log cannot be cleared or modified from the UI.

---

*For questions or issues with the Admin Panel, contact the platform team or refer to the source at `frontend/src/pages/Dashboard.jsx` (admin tab section) and `app/schema.py` (GraphQL mutations).*
