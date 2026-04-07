# Frontend MFA (TOTP) Integration Guide

Use this document when wiring the React/Vue/Vanilla frontend to the Django backend’s MFA endpoints. The backend already supports TOTP provisioning, confirmation, and login-time verification; the frontend just needs to call the endpoints at the right time.

---

## 1. Signup Flow (The "Silent Login" Pattern)

**Context**: When a user signs up, they are not yet logged in. To confirm the QR code, they need an Access Token.
**Solution**: The frontend must perform a "Silent Login" immediately after signup, using the credentials the user *just entered*.

### Complete Code Example (Signup Page)
```javascript
// 1. User fills form and clicks "Sign Up"
async function handleSignupSubmit(username, email, password) {
    
    // Step A: Create User
    const signupResp = await fetch('/app/signup/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
    });
    const signupData = await signupResp.json();
    if (!signupData.ok) throw new Error(signupData.message);

    // Step B: Display QR Code
    // signupData.mfa.qrcode_data_url contains the image
    showQrCode(signupData.mfa.qrcode_data_url);

    // Step C: Silent Login (Background)
    // Use the SAME password to get a token immediately
    const tokenResp = await fetch('/o/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            grant_type: 'password',
            username: username,
            password: password,
            client_id: process.env.CLIENT_ID, // from .env
            client_secret: process.env.CLIENT_SECRET // from .env
        })
    });
    const tokenData = await tokenResp.json();
    if (!tokenData.access_token) throw new Error("Silent login failed");
    
    // Store token for the next step
    const accessToken = tokenData.access_token;
    
    // Wait for User to Scan & Enter Code...
    return accessToken; 
}

// 2. User Scans QR, Enters Code, Clicks "Confirm"
async function handleConfirmClick(userEnteredCode, accessToken) {
    const resp = await fetch('/app/mfa/confirm/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`, // <--- Use the token from Step C
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: userEnteredCode }),
    });
    const data = await resp.json();
    
    if (data.ok) {
        alert("Setup Complete! Redirecting...");
        window.location.href = "/dashboard";
    } else {
        alert("Invalid Code. Please try again.");
    }
}
```

### Flow Breakdown
1.  **Signup**: Creates the account. Returns QR data.
2.  **Display**: Frontend shows the QR code image to the user.
3.  **Silent Login**: Frontend *automatically* calls `/o/token/` using the password from the form. The user does not see this.
4.  **Confirm**: When the user types the 6-digit code and hits "Verify", the frontend sends it specifically to `/app/mfa/confirm/` authenticated with the token from Step 3.

---

## 2. Login Flow (Password + OTP)

### 2.1 Validate Password
```ts
const passwordStep = async (username, password) => {
  const resp = await fetch('/app/login/password/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return resp.json(); // { ok, mfa_required, mfa_challenge_id }
};
```

### 2.2 Verify OTP When Required
```ts
const verifyTotp = async (challengeId, totpCode) => {
  const resp = await fetch('/app/mfa/verify/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mfa_challenge_id: challengeId,
      totp_code: totpCode,
    }),
  });
  const data = await resp.json(); // { ok, mfa_token }
  if (!data.ok) throw new Error(data.message || 'Invalid OTP');
  return data.mfa_token;
};
```

### 2.3 Exchange for OAuth Token
```ts
const fetchAccessToken = async ({ username, password, mfaToken }) => {
  const params = new URLSearchParams({
    grant_type: 'password',
    username,
    password,
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
  });
  if (mfaToken) params.append('mfa_token', mfaToken);

  const resp = await fetch('/o/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  });
  const data = await resp.json(); // { access_token, refresh_token, ... }
  if (!resp.ok) throw new Error(data.error_description || 'OAuth error');
  return data;
};
```

---

## 3. End-to-End Login Example
```ts
async function login(username, password, getTotpFromUser) {
  const step1 = await passwordStep(username, password);
  if (!step1.ok) throw new Error(step1.message || 'Login failed');

  let mfaToken;
  if (step1.mfa_required) {
    const totp = await getTotpFromUser(); // show modal/input
    mfaToken = await verifyTotp(step1.mfa_challenge_id, totp);
  }

  return fetchAccessToken({ username, password, mfaToken });
}
```

`getTotpFromUser` is any UI that prompts for the 6-digit code.

---

## 4. Notes & UX Tips
- Always show the QR code immediately after signup while you still have the user’s attention.
- Store `mfa_challenge_id` only until the OTP is verified; it expires after ~2 minutes.
- `mfa_token` also expires quickly; use it immediately when calling `/o/token/`.
- The same QR code/secret remains valid; if users need to rescan later, call `GET /app/mfa/setup/` again.
- Protect every GraphQL/REST call with `Authorization: Bearer <access_token>`.

Following this document ensures frontend signup + login flows are in sync with the backend’s TOTP logic.

---

## 5. Common Issues & Troubleshooting

### "Invalid Code" (401 Unauthorized)
If the backend rejects a valid code:
1.  **Time Sync**: TOTP relies on the current time. Ensure the user's device clock is set to automatic.
2.  **Server Drift**: The backend has been configured with a tolerance of ±30 seconds. If users still report issues, their device might be significantly out of sync.
3.  **Re-Use**: TOTP codes are single-use. The backend caches used codes to prevent replay attacks.

### "500 Server Error" during Login
This usually indicates a backend misconfiguration (e.g., database schema mismatch or missing dependencies).
- Report this immediately to the backend team.
- Check if `mfa_verify` succeeds but the subsequent `fetchAccessToken` call fails.

### "mfa_challenge_id" Expired
The challenge ID is valid for only **120 seconds**. If the user takes too long to enter the code, they must restart the login process from Step 2.1.


