# NotifyHub API - Frontend Integration Guide

## 🎯 Overview
NotifyHub is a reminder management system with OAuth2 authentication, real-time processing, and company-based multi-tenancy. This guide will help frontend developers integrate with the API.

## 🏗️ Architecture
- **Backend**: Django + GraphQL + OAuth2
- **Authentication**: OAuth2 only (no JWT)
- **API Style**: REST for auth, GraphQL for data operations
- **Multi-tenancy**: Users belong to companies (automatic company creation)

---

## 🔐 Authentication Flow

### 1. User Registration
```javascript
// POST /signup/
const signupUser = async (userData) => {
  const response = await fetch('/signup/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: userData.username,
      email: userData.email,
      password: userData.password,
      captcha_token: userData.captchaToken // Optional if reCAPTCHA enabled
    })
  });
  
  const result = await response.json();
  
  if (result.ok) {
    console.log('User created:', result.user);
    // Auto-creates company: "{username}'s Company"
  } else {
    console.error('Signup failed:', result.message);
  }
  
  return result;
};
```

### 2. Login (Get OAuth2 Token)
```javascript
// POST /o/token/
const loginUser = async (credentials) => {
  const formData = new URLSearchParams({
    grant_type: 'password',
    username: credentials.username,
    password: credentials.password,
    client_id: 'test_client_id',
    client_secret: 'test_client_secret'
  });
  
  const response = await fetch('/o/token/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData
  });
  
  const tokens = await response.json();
  
  if (tokens.access_token) {
    // Store tokens securely
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    
    return {
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresIn: tokens.expires_in
    };
  } else {
    throw new Error('Login failed');
  }
};
```

### 3. Token Refresh
```javascript
// POST /o/token/ (refresh_token grant)
const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const formData = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: 'test_client_id',
    client_secret: 'test_client_secret'
  });
  
  const response = await fetch('/o/token/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData
  });
  
  const tokens = await response.json();
  
  if (tokens.access_token) {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    return tokens.access_token;
  } else {
    // Redirect to login
    throw new Error('Token refresh failed');
  }
};
```

---

## 📊 GraphQL API Usage

### Authentication Header
All GraphQL requests require the OAuth2 Bearer token:

```javascript
const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
};
```

### 1. Get Current User
```javascript
const getCurrentUser = async () => {
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      query: `
        {
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
      `
    })
  });
  
  const result = await response.json();
  return result.data.me;
};
```

### 2. List Reminders
```javascript
const getReminders = async (activeOnly = null) => {
  const query = activeOnly !== null 
    ? `{ reminders(active: ${activeOnly}) { id title description reminderStartDate active } }`
    : `{ reminders { id title description reminderStartDate active } }`;
  
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ query })
  });
  
  const result = await response.json();
  return result.data.reminders;
};
```

### 3. Create Reminder
```javascript
const createReminder = async (reminderData) => {
  const mutation = `
    mutation {
      createReminder(
        title: "${reminderData.title}"
        description: "${reminderData.description}"
        senderEmail: "${reminderData.senderEmail}"
        receiverEmail: "${reminderData.receiverEmail}"
        intervalType: "${reminderData.intervalType}"
        reminderStartDate: "${reminderData.reminderStartDate}"
      ) {
        ok
        reminder {
          id
          title
          description
          reminderStartDate
          active
        }
      }
    }
  `;
  
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ query: mutation })
  });
  
  const result = await response.json();
  
  if (result.data.createReminder.ok) {
    return result.data.createReminder.reminder;
  } else {
    throw new Error('Failed to create reminder');
  }
};
```

### 4. Update Reminder
```javascript
const updateReminder = async (id, updates) => {
  const fields = Object.entries(updates)
    .map(([key, value]) => `${key}: "${value}"`)
    .join('\n        ');
  
  const mutation = `
    mutation {
      updateReminder(
        id: "${id}"
        ${fields}
      ) {
        ok
        reminder {
          id
          title
          description
          active
        }
      }
    }
  `;
  
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ query: mutation })
  });
  
  const result = await response.json();
  return result.data.updateReminder;
};
```

### 5. Delete Reminder
```javascript
const deleteReminder = async (id) => {
  const mutation = `
    mutation {
      deleteReminder(id: "${id}") {
        ok
      }
    }
  `;
  
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ query: mutation })
  });
  
  const result = await response.json();
  return result.data.deleteReminder.ok;
};
```

---

## 🛡️ Security Features

### Rate Limiting
- **Signup**: 3 attempts per minute per IP
- **Response**: `{"ok": false, "code": "RATE_LIMIT_EXCEEDED", "message": "Too many attempts"}`

### reCAPTCHA (Optional)
- Configured via environment variables
- Include `captcha_token` in signup requests when enabled
- Frontend should integrate with Google reCAPTCHA v2

---

## 📱 Complete Frontend Example

### React Hook Example
```javascript
import { useState, useEffect } from 'react';

export const useNotifyHub = () => {
  const [user, setUser] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(false);

  // Check if user is authenticated
  const isAuthenticated = () => {
    return !!localStorage.getItem('access_token');
  };

  // Login function
  const login = async (username, password) => {
    setLoading(true);
    try {
      const tokens = await loginUser({ username, password });
      const userData = await getCurrentUser();
      setUser(userData);
      return { success: true, user: userData };
    } catch (error) {
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  // Signup function
  const signup = async (userData) => {
    setLoading(true);
    try {
      const result = await signupUser(userData);
      if (result.ok) {
        // Auto-login after signup
        return await login(userData.username, userData.password);
      }
      return { success: false, error: result.message };
    } catch (error) {
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  // Load reminders
  const loadReminders = async () => {
    if (!isAuthenticated()) return;
    
    setLoading(true);
    try {
      const data = await getReminders();
      setReminders(data);
    } catch (error) {
      console.error('Failed to load reminders:', error);
    } finally {
      setLoading(false);
    }
  };

  // Create reminder
  const createReminder = async (reminderData) => {
    if (!isAuthenticated()) return { success: false, error: 'Not authenticated' };
    
    try {
      const newReminder = await createReminder(reminderData);
      setReminders(prev => [...prev, newReminder]);
      return { success: true, reminder: newReminder };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  // Logout
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    setReminders([]);
  };

  // Auto-load user on mount
  useEffect(() => {
    if (isAuthenticated()) {
      getCurrentUser().then(setUser);
      loadReminders();
    }
  }, []);

  return {
    user,
    reminders,
    loading,
    isAuthenticated: isAuthenticated(),
    login,
    signup,
    logout,
    loadReminders,
    createReminder,
    updateReminder,
    deleteReminder
  };
};
```

---

## 🔧 Environment Setup

### Required Environment Variables
```bash
# OAuth2 Client Credentials (for frontend)
OAUTH_CLIENT_ID=test_client_id
OAUTH_CLIENT_SECRET=test_client_secret

# Optional: reCAPTCHA
RECAPTCHA_SITE_KEY=your_recaptcha_site_key
```

### API Base URL
- **Development**: `http://localhost:8000`
- **Production**: Your deployed domain

---

## 📋 API Endpoints Summary

| Method | Endpoint | Purpose | Auth Required | Rate Limited |
|--------|----------|---------|---------------|--------------|
| `GET` | `/health/` | Health check | ❌ | ❌ |
| `POST` | `/signup/` | User registration | ❌ | ✅ (3/min) |
| `POST` | `/o/token/` | OAuth2 token exchange | ❌ | ❌ |
| `POST` | `/graphql/` | GraphQL API | ✅ | ❌ |
| `POST` | `/webhook/process-reminders/` | Process reminders | ❌ | ❌ |

---

## 🚨 Error Handling

### Common Error Codes
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `USERNAME_TAKEN`: Username already exists
- `EMAIL_TAKEN`: Email already exists
- `CAPTCHA_FAILED`: reCAPTCHA verification failed
- `INVALID_CREDENTIALS`: Wrong username/password

### Error Response Format
```json
{
  "ok": false,
  "code": "ERROR_CODE",
  "message": "Human readable error message"
}
```

---

## 🎯 Key Points for Frontend Developers

1. **OAuth2 Only**: No JWT tokens, use OAuth2 access tokens
2. **Company Auto-Creation**: Each user gets their own company automatically
3. **Multi-tenancy**: Users only see their company's data
4. **Real-time Processing**: Reminders are processed by background tasks
5. **Rate Limited**: Signup is limited to 3 attempts per minute
6. **GraphQL**: All data operations use GraphQL with OAuth2 Bearer tokens

---

## 🧪 Testing

Use the provided Postman collection: `notifyhub_oauth2_only_collection.json`

1. Import the collection
2. Set environment variables
3. Test the complete flow: Signup → Login → GraphQL operations

---

## 📞 Support

For any questions or issues:
1. Check this guide first
2. Test with the Postman collection
3. Verify environment variables
4. Check server logs for detailed error messages
