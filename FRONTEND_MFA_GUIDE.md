# Frontend MFA (TOTP) Integration Guide

This guide explains how to integrate the Multi-Factor Authentication (MFA) flow using TOTP (Time-based One-Time Password) in your frontend application.

## Overview

The MFA flow has two main phases:
1. **Enrollment** (one-time, after signup): User scans QR code to set up authenticator app
2. **Login** (every time): User enters 6-digit code from authenticator app

---

## Phase 1: MFA Enrollment (After Signup)

### Step 1: Get QR Code

**Endpoint:** `GET /app/mfa/setup`

**Authentication:** Required (Bearer token from signup/login)

**Request:**
```javascript
const response = await fetch('/app/mfa/setup', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
```

**Response:**
```json
{
  "ok": true,
  "otpauth_uri": "otpauth://totp/NotifyHub:username?secret=ABCDEF123456&issuer=NotifyHub",
  "qrcode_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "secret": "ABCDEF123456"
}
```

### Step 2: Display QR Code

You have **two options** to display the QR code:

#### Option A: Use qrcode_data_url (Recommended - Easiest)

The backend provides a ready-to-use base64-encoded PNG image. Simply use it as an image source:

```html
<img id="mfa-qr" alt="Scan this QR code with your authenticator app" />
```

```javascript
if (data.ok && data.qrcode_data_url) {
  // Directly set the image source - no library needed!
  document.getElementById('mfa-qr').src = data.qrcode_data_url;
}
```

**How it works:**
- `qrcode_data_url` is a [Data URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs) in the format: `data:image/png;base64,<base64-encoded-image>`
- Browsers can display Data URLs directly in `<img>` tags
- No additional libraries or processing required
- The image is embedded in the response, so it works immediately

#### Option B: Generate QR Code on Client (Fallback)

If `qrcode_data_url` is not provided, use the `otpauth_uri` with a QR code library:

```javascript
import QRCode from 'qrcode'; // or any QR library

if (data.ok && data.otpauth_uri) {
  // Generate QR code from otpauth_uri
  QRCode.toCanvas(document.getElementById('mfa-qr-canvas'), data.otpauth_uri, {
    width: 256,
    errorCorrectionLevel: 'M'
  });
}
```

**Recommended QR Libraries:**
- `qrcode` (npm: `qrcode`)
- `qrcode.react` (React component)
- `vue-qrcode` (Vue component)

### Step 3: User Scans QR Code

1. Display the QR code image
2. Show instructions: "Scan this QR code with Google Authenticator, Authy, or any authenticator app"
3. Wait for user to scan and add to their app

### Step 4: Confirm MFA Setup

**Endpoint:** `POST /app/mfa/confirm`

**Authentication:** Required (Bearer token)

**Request:**
```javascript
const code = document.getElementById('mfa-code-input').value; // User enters 6-digit code

const response = await fetch('/app/mfa/confirm', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    code: code // e.g., "123456"
  })
});

const result = await response.json();
```

**Response:**
```json
{
  "ok": true,
  "message": "MFA enabled successfully"
}
```

**Error Response (if code is wrong):**
```json
{
  "ok": false,
  "code": "INVALID_CODE",
  "message": "Invalid TOTP code"
}
```

**Complete Enrollment Flow Example:**

```javascript
async function setupMFA(accessToken) {
  try {
    // Step 1: Get QR code
    const setupRes = await fetch('/app/mfa/setup', {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const setupData = await setupRes.json();
    
    if (!setupData.ok) {
      throw new Error(setupData.message || 'Failed to setup MFA');
    }
    
    // Step 2: Display QR code
    if (setupData.qrcode_data_url) {
      // Option A: Use provided data URL (easiest)
      document.getElementById('mfa-qr').src = setupData.qrcode_data_url;
    } else if (setupData.otpauth_uri) {
      // Option B: Generate QR on client
      await QRCode.toCanvas(document.getElementById('mfa-qr-canvas'), setupData.otpauth_uri);
    }
    
    // Step 3: Wait for user to scan and enter code
    const userCode = prompt('Enter the 6-digit code from your authenticator app:');
    
    // Step 4: Confirm setup
    const confirmRes = await fetch('/app/mfa/confirm', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ code: userCode })
    });
    
    const confirmData = await confirmRes.json();
    
    if (confirmData.ok) {
      alert('MFA enabled successfully! You will need to enter a code on every login.');
    } else {
      alert('Invalid code. Please try again.');
    }
  } catch (error) {
    console.error('MFA setup error:', error);
    alert('Failed to setup MFA: ' + error.message);
  }
}
```

---

## Phase 2: Login with MFA (Every Login)

### Step 1: Check Password

**Endpoint:** `POST /app/login/password`

**Request:**
```javascript
const response = await fetch('/app/login/password', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'user@example.com',
    password: 'userpassword'
  })
});

const data = await response.json();
```

**Response (if MFA is enabled):**
```json
{
  "ok": true,
  "mfa_required": true,
  "mfa_challenge_id": "abc123xyz"
}
```

**Response (if MFA is NOT enabled):**
```json
{
  "ok": true,
  "mfa_required": false
}
```

### Step 2: Verify TOTP Code (if MFA required)

**Endpoint:** `POST /app/mfa/verify`

**Request:**
```javascript
const totpCode = document.getElementById('totp-input').value; // User enters 6-digit code

const response = await fetch('/app/mfa/verify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    mfa_challenge_id: data.mfa_challenge_id,
    totp_code: totpCode
  })
});

const verifyData = await response.json();
```

**Response:**
```json
{
  "ok": true,
  "mfa_token": "short-lived-token-xyz123"
}
```

**Error Response:**
```json
{
  "ok": false,
  "code": "INVALID_CODE",
  "message": "Invalid TOTP code"
}
```

### Step 3: Get OAuth2 Access Token

**Endpoint:** `POST /o/token/`

**Request:**
```javascript
const formData = new URLSearchParams();
formData.append('grant_type', 'password');
formData.append('username', 'user@example.com');
formData.append('password', 'userpassword');
formData.append('client_id', 'your_client_id');
formData.append('client_secret', 'your_client_secret');
formData.append('mfa_token', verifyData.mfa_token); // Include MFA token

const response = await fetch('/o/token/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded'
  },
  body: formData
});

const tokenData = await response.json();
// { access_token: "...", token_type: "Bearer", expires_in: 3600 }
```

**Complete Login Flow Example:**

```javascript
async function loginWithMFA(username, password) {
  try {
    // Step 1: Check password
    const loginRes = await fetch('/app/login/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const loginData = await loginRes.json();
    
    if (!loginData.ok) {
      throw new Error(loginData.message || 'Login failed');
    }
    
    // Step 2: If MFA required, get code from user
    let mfaToken = null;
    if (loginData.mfa_required) {
      const totpCode = prompt('Enter the 6-digit code from your authenticator app:');
      
      const verifyRes = await fetch('/app/mfa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mfa_challenge_id: loginData.mfa_challenge_id,
          totp_code: totpCode
        })
      });
      const verifyData = await verifyRes.json();
      
      if (!verifyData.ok) {
        throw new Error('Invalid TOTP code');
      }
      
      mfaToken = verifyData.mfa_token;
    }
    
    // Step 3: Get OAuth2 token
    const formData = new URLSearchParams();
    formData.append('grant_type', 'password');
    formData.append('username', username);
    formData.append('password', password);
    formData.append('client_id', 'your_client_id');
    formData.append('client_secret', 'your_client_secret');
    if (mfaToken) {
      formData.append('mfa_token', mfaToken);
    }
    
    const tokenRes = await fetch('/o/token/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    });
    
    const tokenData = await tokenRes.json();
    
    // Store access token for future API calls
    localStorage.setItem('access_token', tokenData.access_token);
    
    return tokenData.access_token;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}
```

---

## React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function MFASetup({ accessToken }) {
  const [qrCode, setQrCode] = useState(null);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    // Fetch QR code on mount
    fetch('/app/mfa/setup', {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    })
      .then(res => res.json())
      .then(data => {
        if (data.ok && data.qrcode_data_url) {
          setQrCode(data.qrcode_data_url);
        }
      });
  }, [accessToken]);
  
  const handleConfirm = async () => {
    setLoading(true);
    try {
      const res = await fetch('/app/mfa/confirm', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      });
      const data = await res.json();
      
      if (data.ok) {
        alert('MFA enabled successfully!');
      } else {
        alert('Invalid code. Please try again.');
      }
    } catch (error) {
      alert('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <h2>Set Up Two-Factor Authentication</h2>
      <p>Scan this QR code with your authenticator app:</p>
      {qrCode && <img src={qrCode} alt="MFA QR Code" style={{ width: 256, height: 256 }} />}
      <div>
        <input
          type="text"
          placeholder="Enter 6-digit code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          maxLength={6}
        />
        <button onClick={handleConfirm} disabled={loading || code.length !== 6}>
          Confirm
        </button>
      </div>
    </div>
  );
}

export default MFASetup;
```

---

## Important Notes

1. **TOTP Codes:**
   - Codes are generated by the user's authenticator app (Google Authenticator, Authy, 1Password, etc.)
   - Codes rotate every 30 seconds
   - Codes are 6 digits
   - Users do NOT receive codes via SMS/email - they come from their app

2. **qrcode_data_url Format:**
   - Format: `data:image/png;base64,<base64-encoded-png-data>`
   - Can be used directly in `<img src="...">` tags
   - No additional processing needed
   - Works in all modern browsers

3. **Error Handling:**
   - Always check `ok` field in responses
   - Handle `INVALID_CODE` errors gracefully
   - Allow users to retry if code is wrong

4. **Security:**
   - Never log or expose the `secret` field
   - Store `access_token` securely (localStorage/sessionStorage)
   - Always use HTTPS in production

5. **User Experience:**
   - Show clear instructions: "Scan QR code with your authenticator app"
   - Allow users to skip MFA setup (optional, but recommended)
   - Provide help text: "Lost your authenticator? Contact support"

---

## API Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/app/mfa/setup` | GET | Bearer | Get QR code for enrollment |
| `/app/mfa/confirm` | POST | Bearer | Confirm MFA setup with code |
| `/app/login/password` | POST | None | Check password, get MFA challenge |
| `/app/mfa/verify` | POST | None | Verify TOTP code, get mfa_token |
| `/o/token/` | POST | None | Exchange credentials + mfa_token for access_token |

---

## Testing

1. **Test QR Code Display:**
   - Verify `qrcode_data_url` renders correctly in `<img>` tag
   - Test with different screen sizes
   - Ensure QR code is scannable

2. **Test MFA Flow:**
   - Signup → Setup MFA → Login with MFA
   - Test invalid code handling
   - Test expired code (wait 30+ seconds)

3. **Test Error Cases:**
   - Invalid username/password
   - Invalid TOTP code
   - Missing mfa_token when required
   - Network errors

---

## Support

If you encounter issues:
1. Check browser console for errors
2. Verify Authorization headers are correct
3. Ensure access_token is valid and not expired
4. Check network tab for API responses
5. Contact backend team with error codes and messages

