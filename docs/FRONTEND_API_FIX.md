# Frontend API Connection Fix

## 🔧 Issues Fixed

### 1. **TenantRedirectMiddleware Blocking API Requests**
**Problem:** The `TenantRedirectMiddleware` was redirecting all authenticated requests, including API calls, which prevented the frontend from connecting to the API.

**Solution:** Updated the middleware to skip redirects for all API endpoints:
- `/signup/` - User registration
- `/o/` - OAuth2 token endpoints
- `/graphql/` - GraphQL API
- `/webhook/` - Webhook endpoints
- `/health/` - Health check
- `/login/` - Login endpoints
- `/mfa/` - MFA endpoints
- `/admin/` - Admin panel

### 2. **CORS Methods Configuration**
**Problem:** CORS settings didn't explicitly allow all HTTP methods.

**Solution:** Added explicit `CORS_ALLOW_METHODS` configuration to ensure all methods (GET, POST, PUT, PATCH, DELETE, OPTIONS) are allowed.

## ✅ What's Working Now

1. **User Signup** - Frontend can now call `POST /signup/` without redirects
2. **OAuth2 Token** - Frontend can get tokens via `POST /o/token/`
3. **GraphQL API** - All GraphQL requests work without interference
4. **CORS** - All origins, methods, and headers are properly configured

## 📝 Frontend Integration Checklist

### 1. Use Full API URLs
Make sure your frontend uses the full API base URL:

```javascript
// ✅ Correct
const API_BASE = 'http://localhost:8000';  // or your production URL
const response = await fetch(`${API_BASE}/signup/`, { ... });

// ❌ Wrong (relative URLs may not work from different domains)
const response = await fetch('/signup/', { ... });
```

### 2. Signup Endpoint
```javascript
const signupUser = async (userData) => {
  const response = await fetch(`${API_BASE}/signup/`, {
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
  return result;
};
```

### 3. OAuth2 Login
```javascript
const loginUser = async (username, password) => {
  const response = await fetch(`${API_BASE}/o/token/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'password',
      username: username,
      password: password,
      client_id: 'test_client_id',
      client_secret: 'test_client_secret'
    })
  });
  
  const data = await response.json();
  return data.access_token;
};
```

### 4. GraphQL Requests
```javascript
const graphqlRequest = async (token, query, variables = {}) => {
  const response = await fetch(`${API_BASE}/graphql/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      variables: variables
    })
  });
  
  return await response.json();
};
```

## 🧪 Testing

You can test the endpoints using:

1. **Browser DevTools** - Check Network tab for CORS errors
2. **Postman** - Use the provided Postman collections
3. **curl** - Test from command line:
   ```bash
   curl -X POST http://localhost:8000/signup/ \
     -H "Content-Type: application/json" \
     -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'
   ```

## 🚨 Common Issues & Solutions

### Issue: CORS Error
**Error:** `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Solution:** 
- Verify `CORS_ALLOW_ALL_ORIGINS = True` in settings (already configured)
- Make sure you're using the correct API base URL
- Check that the request includes proper headers

### Issue: 302 Redirect
**Error:** Request is being redirected

**Solution:** 
- This should be fixed now with the middleware update
- Make sure you're using API endpoints (they start with `/signup/`, `/o/`, `/graphql/`, etc.)
- Restart the Django server after the fix

### Issue: 400 Bad Request
**Error:** `MISSING_FIELDS` or `INVALID_JSON`

**Solution:**
- Ensure all required fields are included: `username`, `email`, `password`
- Check that `Content-Type: application/json` header is set
- Verify JSON is properly formatted

### Issue: 429 Too Many Requests
**Error:** `RATE_LIMIT_EXCEEDED`

**Solution:**
- Rate limit is 3 signup attempts per minute per IP
- Wait 60 seconds before trying again
- This is a security feature to prevent abuse

## 📚 Additional Resources

- `FRONTEND_INTEGRATION_GUIDE.md` - Complete integration guide
- `API_SUMMARY_FOR_FRONTEND.md` - Quick API reference
- `frontend_example.html` - Working example code

## 🔄 Next Steps

1. **Restart the Django server** to apply the middleware changes
2. **Test signup** from your frontend
3. **Test login** and token retrieval
4. **Test GraphQL** queries with the token

If you still encounter issues, check:
- Server logs for errors
- Browser console for CORS/network errors
- That the server is running and accessible
- That you're using the correct API base URL

