// ── API helpers for NotifyHub ─────────────────────────────────────────────────
//
// Auth model: OAuth2 Password Grant (CLIENT_PUBLIC — no client_secret).
// Django OAuth Toolkit with CLIENT_PUBLIC type does not require a client_secret
// for the password grant, so we never include one here.  Vite inlines every
// VITE_* env var into the production JS bundle, so a secret would be readable
// by anyone with DevTools — we simply don't use one.
//
// Token lifecycle:
//   access_token  — 30-minute lifetime, stored in localStorage
//   refresh_token — 7-day lifetime, stored in localStorage, rotated on use
//   Refresh happens automatically in refreshAccessToken() which is called by
//   apollo.js on every 401 before the request is retried.

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Only the client_id is needed — CLIENT_PUBLIC apps have no secret.
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID || '';

// ── Token storage helpers ─────────────────────────────────────────────────────

export const getAccessToken  = () => localStorage.getItem('access_token');
export const getRefreshToken = () => localStorage.getItem('refresh_token');

const saveTokens = ({ access_token, refresh_token }) => {
    localStorage.setItem('access_token', access_token);
    if (refresh_token) localStorage.setItem('refresh_token', refresh_token);
};

const clearTokens = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
};

// ── isAuthenticated — checks presence AND expiry ──────────────────────────────
// Decodes the JWT payload (base-64 middle section) and compares `exp` against
// the current time.  Returns false if:
//   - no token in localStorage
//   - token is not a valid JWT
//   - token has already expired
//
// Note: this does NOT verify the signature — that happens on the server.
// The client-side check is purely to avoid sending obviously dead tokens.

export const isAuthenticated = () => {
    const token = getAccessToken();
    if (!token) return false;

    const parts = token.split('.');
    // If it's not a JWT (e.g. Django OAuth Toolkit opaque token), just assume it's valid.
    // Apollo 401 interceptor will handle actual expiration.
    if (parts.length !== 3) return true;

    try {
        // atob requires standard base64; JWT uses base64url — fix the padding
        const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (!payload.exp) return true; // no exp claim → treat as valid

        // Give a 30-second grace window to account for clock skew
        return payload.exp > (Date.now() / 1000) + 30;
    } catch {
        return false;
    }
};

// ── refreshAccessToken ────────────────────────────────────────────────────────
// Called automatically by apollo.js on 401.  Returns the new access token or
// throws if the refresh itself fails (session truly expired).

export const refreshAccessToken = async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) throw new Error('No refresh token available');

    const body = new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: CLIENT_ID,
    });

    const response = await fetch(`${API_BASE}/o/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
    });

    if (!response.ok) {
        // Refresh token is invalid or expired — force a fresh login
        clearTokens();
        throw new Error('Session expired. Please log in again.');
    }

    const data = await response.json();
    saveTokens(data);
    return data.access_token;
};

// ── login ─────────────────────────────────────────────────────────────────────

export const login = async (username, password) => {
    const body = new URLSearchParams({
        grant_type: 'password',
        username,
        password,
        client_id: CLIENT_ID,
        // No client_secret — CLIENT_PUBLIC type doesn't require it, and
        // including one would expose it in the compiled JS bundle.
    });

    const response = await fetch(`${API_BASE}/o/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error_description || err.message || 'Login failed');
    }

    const data = await response.json();
    saveTokens(data);
    return data;
};

// ── logout ────────────────────────────────────────────────────────────────────
// Best-effort token revocation on the server, then clears local state.

export const logout = async () => {
    const token = getAccessToken();
    if (token) {
        try {
            await fetch(`${API_BASE}/o/revoke_token/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ token, client_id: CLIENT_ID }),
            });
        } catch {
            // Ignore network errors on logout — we clear local state regardless
        }
    }
    clearTokens();
    window.location.href = '/login';
};

// ── signup ────────────────────────────────────────────────────────────────────

export const signup = async (username, email, password) => {
    const response = await fetch(`${API_BASE}/signup/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Signup failed');
    return data;
};

// ── password reset ────────────────────────────────────────────────────────────

export const forgotPassword = async (email) => {
    const response = await fetch(`${API_BASE}/auth/forgot-password/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Request failed');
    return data;
};

export const resetPassword = async (token, password) => {
    const response = await fetch(`${API_BASE}/auth/reset-password/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Reset failed');
    return data;
};

// ── file upload ───────────────────────────────────────────────────────────────

export const uploadReminderAttachment = async (file) => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/reminder/upload-attachment/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Upload failed');
    return data;
};
