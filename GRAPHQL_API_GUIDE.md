# NotifyHub GraphQL API Guide

## 🚀 Quick Start

Your API is running and working! This guide will help you use it correctly.

## 🔐 Authentication Setup

### Step 1: Create OAuth2 Application

1. Open the admin panel: http://localhost:8000/adrian-holovaty/
2. Navigate to: **OAuth2 Provider → Applications**
3. Click **"Add Application"**
4. Fill in the form:
   - **Name**: `Test Application` (or any name)
   - **Client type**: `Confidential`
   - **Authorization grant type**: `Resource owner password-based`
   - **Skip authorization**: ✅ **Check this box**
   - **Redirect URIs**: Leave empty for password grant
5. Click **Save**
6. **Copy the Client ID and Client Secret** - you'll need these!

### Step 2: Get Access Token

Use the OAuth2 token endpoint to get an access token:

```bash
curl -X POST http://localhost:8000/o/token/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=YOUR_USERNAME" \
  -d "password=YOUR_PASSWORD" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

**Response:**
```json
{
  "access_token": "your-access-token-here",
  "expires_in": 36000,
  "token_type": "Bearer",
  "scope": "read write",
  "refresh_token": "your-refresh-token-here"
}
```

## 📡 Using GraphQL API

### Access the GraphQL Playground

Open in your browser: http://localhost:8000/graphql/

### Add Authentication Header

In the GraphQL playground (or any GraphQL client), add this header:

```json
{
  "Authorization": "Bearer YOUR_ACCESS_TOKEN_HERE"
}
```

**Important:** 
- Use `Bearer` (not just the token)
- No quotes around the token in the header value
- Make sure there's a space between `Bearer` and the token

### Example: GraphiQL Header Configuration

If you're using the built-in GraphiQL interface:

1. Look for the **"Headers"** button at the bottom
2. Click it to open the headers panel
3. Add this JSON:

```json
{
  "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

## 🔍 Common GraphQL Operations

### 1. Get Current User Info

```graphql
query {
  me {
    id
    username
    email
    company {
      id
      name
    }
  }
}
```

### 2. Create a Reminder

```graphql
mutation {
  createReminder(
    title: "Team Meeting Reminder"
    description: "Weekly team sync meeting"
    senderEmail: "admin@company.com"
    senderName: "Admin"
    receiverEmail: "team@company.com"
    intervalType: "weekly"
    active: true
    visibleToDepartment: false
  ) {
    ok
    reminder {
      id
      title
      description
      active
      createdBy {
        username
      }
    }
  }
}
```

### 3. List All Active Reminders

```graphql
query {
  reminders(active: true) {
    id
    title
    description
    senderEmail
    receiverEmail
    intervalType
    reminderStartDate
    active
    createdBy {
      username
    }
  }
}
```

### 4. Update a Reminder

```graphql
mutation {
  updateReminder(
    id: "1"
    title: "Updated Title"
    active: false
  ) {
    ok
    reminder {
      id
      title
      active
    }
  }
}
```

### 5. Delete a Reminder

```graphql
mutation {
  deleteReminder(id: "1") {
    ok
  }
}
```

### 6. List Departments

```graphql
query {
  departments {
    id
    name
    company {
      name
    }
  }
}
```

### 7. Create a Department

```graphql
mutation {
  createDepartment(name: "Engineering") {
    ok
    department {
      id
      name
    }
  }
}
```

## 🐛 Troubleshooting

### Error: "You do not have permission to perform this action"

**Cause:** Missing or invalid authentication token

**Solution:**
1. Make sure you obtained a valid access token
2. Check that the Authorization header is correctly formatted:
   ```
   Authorization: Bearer YOUR_TOKEN
   ```
3. Verify the token hasn't expired (default: 10 hours)
4. If expired, get a new token using the refresh token or re-authenticate

### Error: "Headers are invalid JSON: Unexpected token 'A'"

**Cause:** Incorrect header format in GraphiQL

**Solution:** In GraphiQL, headers must be valid JSON:

❌ **Wrong:**
```
Authorization: Bearer token123
```

✅ **Correct:**
```json
{
  "Authorization": "Bearer token123"
}
```

### Error: "Unknown argument 'captcha_token'"

**Cause:** Your GraphQL API doesn't have a login mutation with captcha

**Solution:** Use the OAuth2 endpoint instead:
- OAuth2 endpoint: `/o/token/`
- GraphQL is for data operations, not login
- Authentication happens via OAuth2, then use the token for GraphQL

### Error: "Authentication required"

**Cause:** No Authorization header or invalid token

**Solution:**
1. Check your token is valid
2. Ensure you're including the Authorization header
3. Verify the token format: `Bearer YOUR_TOKEN`

## 🌐 Frontend Integration

### JavaScript/Fetch Example

```javascript
// Get OAuth2 token
async function login(username, password) {
  const response = await fetch('http://localhost:8000/o/token/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'password',
      username: username,
      password: password,
      client_id: 'YOUR_CLIENT_ID',
      client_secret: 'YOUR_CLIENT_SECRET',
    }),
  });
  
  const data = await response.json();
  return data.access_token;
}

// Use token for GraphQL
async function createReminder(token, reminderData) {
  const response = await fetch('http://localhost:8000/graphql/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      query: `
        mutation CreateReminder($title: String!, $senderEmail: String!, $receiverEmail: String!) {
          createReminder(
            title: $title
            senderEmail: $senderEmail
            receiverEmail: $receiverEmail
          ) {
            ok
            reminder {
              id
              title
            }
          }
        }
      `,
      variables: reminderData,
    }),
  });
  
  return await response.json();
}

// Usage
const token = await login('admin', 'password');
const result = await createReminder(token, {
  title: 'Test Reminder',
  senderEmail: 'sender@example.com',
  receiverEmail: 'receiver@example.com',
});
```

### Apollo Client Example

```javascript
import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';

const httpLink = createHttpLink({
  uri: 'http://localhost:8000/graphql/',
});

const authLink = setContext((_, { headers }) => {
  const token = localStorage.getItem('access_token');
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
    }
  }
});

const client = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache()
});
```

## 🔄 Token Refresh

When your access token expires, use the refresh token:

```bash
curl -X POST http://localhost:8000/o/token/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## 📋 Available Interval Types

When creating reminders, use these interval types:
- `daily` - Every day
- `weekly` - Every week
- `monthly` - Every month
- `yearly` - Every year

## 🔒 Security Notes

1. **Never expose client secrets** in frontend code
2. **Use environment variables** for sensitive data
3. **Implement token refresh** logic in your frontend
4. **Use HTTPS** in production
5. **Store tokens securely** (e.g., httpOnly cookies or secure storage)

## 📚 Additional Resources

- GraphQL Schema Documentation: http://localhost:8000/graphql/
- OAuth2 Endpoints: http://localhost:8000/o/
- Admin Panel: http://localhost:8000/adrian-holovaty/

## ✅ Testing Your Setup

Run the included test script:

```bash
cd /Users/roshan/Desktop/notifyhub
python3 test_api_complete.py
```

This will verify:
- OAuth2 authentication works
- GraphQL queries work
- GraphQL mutations work
- Authorization is properly enforced

