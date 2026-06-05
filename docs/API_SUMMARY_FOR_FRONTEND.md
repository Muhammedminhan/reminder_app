# NotifyHub API - Quick Summary for Frontend

## 🔄 Authentication Flow (Simple)

```
1. User Signup → POST /signup/
   ↓
2. Get Token → POST /o/token/
   ↓  
3. Use Token → POST /graphql/ (with Bearer token)
```

## 📝 Key Code Examples

### 1. Login & Get Token
```javascript
// Step 1: Get OAuth2 token
const response = await fetch('/o/token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'grant_type=password&username=user&password=pass&client_id=test_client_id&client_secret=test_client_secret'
});

const { access_token } = await response.json();

// Step 2: Use token for GraphQL
const graphqlResponse = await fetch('/graphql/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: '{ me { id username email } }'
  })
});
```

### 2. Create Reminder
```javascript
const createReminder = async (token, reminderData) => {
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: `
        mutation {
          createReminder(
            title: "${reminderData.title}"
            senderEmail: "${reminderData.senderEmail}"
            receiverEmail: "${reminderData.receiverEmail}"
            intervalType: "ONCE"
            reminderStartDate: "${reminderData.date}"
            visibleToDepartment: ${reminderData.visibleToDepartment || false}
          ) {
            ok
            reminder { id title visibleToDepartment }
          }
        }
      `
    })
  });
  
  return await response.json();
};
```

## 🎯 What Frontend Needs to Know

1. **Authentication**: OAuth2 only (no JWT)
2. **Signup**: Creates user + company automatically
3. **GraphQL**: All data operations require Bearer token
4. **Multi-tenant**: Users only see their company's data
5. **Rate Limited**: Max 3 signup attempts per minute
6. **Reminder Visibility**: Use `visibleToDepartment` flag to control department-wide visibility

## 🚀 Quick Start

1. **Signup**: `POST /signup/` with username, email, password
2. **Login**: `POST /o/token/` to get access_token
3. **API Calls**: Use `Authorization: Bearer {token}` header
4. **GraphQL**: All queries/mutations require authentication

## 📊 Available Operations

| Operation | GraphQL Query/Mutation |
|-----------|------------------------|
| Get User | `{ me { id username email } }` |
| List Users | `{ users { id username email company { id name } department { id name } } }` |
| Get User by ID | `{ user(id: 1) { id username email company { id name } department { id name } } }` |
| List Reminders | `{ reminders { id title description } }` |
| Create Reminder | `mutation { createReminder(...) }` |
| Update Reminder | `mutation { updateReminder(...) }` |
| Delete Reminder | `mutation { deleteReminder(...) }` |
| List Companies | `{ companies { id name } }` |
| Get Company by ID | `{ company(id: 1) { id name website } }` |
| Update Me | `mutation { updateMe(firstName: "A" lastName: "B") { ok user { id firstName lastName } } }` |

## 👥 Reminder Visibility Control

The `visibleToDepartment` field controls who can see reminders:

- **`false` (default)**: Private reminder - only visible to the creator
- **`true`**: Department-visible - visible to all members of the creator's department

### Visibility Rules:
1. **Personal Reminders**: Always visible to the creator (regardless of setting)
2. **Department Reminders**: Visible to all users in the same department when `visibleToDepartment = true`
3. **Company Isolation**: Users only see reminders from their own company

### Example Usage:
```javascript
// Private reminder (only creator can see)
const privateReminder = {
  title: "Personal Task",
  visibleToDepartment: false
};

// Department-wide reminder (all department members can see)
const deptReminder = {
  title: "Team Meeting",
  visibleToDepartment: true
};
```

## 🛡️ Security

- **Rate Limiting**: 3 signups per minute per IP
- **reCAPTCHA**: Optional, configurable
- **Company Isolation**: Users only see their own data
- **Token Expiry**: 1 hour (use refresh token)

## 📁 Files to Share with Frontend

1. `FRONTEND_INTEGRATION_GUIDE.md` - Complete guide
2. `notifyhub_oauth2_only_collection.json` - Postman collection
3. `API_SUMMARY_FOR_FRONTEND.md` - This quick reference

## 🔧 Environment Setup

```bash
# Frontend needs these
API_BASE_URL=http://localhost:8000
OAUTH_CLIENT_ID=test_client_id
OAUTH_CLIENT_SECRET=test_client_secret
```

## 💡 Pro Tips

1. Store tokens in localStorage/sessionStorage
2. Implement token refresh logic
3. Handle rate limiting gracefully
4. Use GraphQL for flexible data fetching
5. Test with Postman collection first
