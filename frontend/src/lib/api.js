// API configuration — sourced from .env at build time (never hardcoded in source)
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID || '';
const CLIENT_SECRET = import.meta.env.VITE_CLIENT_SECRET || '';

export const login = async (username, password) => {
    const formData = new URLSearchParams({
        grant_type: 'password',
        username,
        password,
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
    });

    const response = await fetch(`${API_BASE}/o/token/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Login error details:', errorData);
        throw new Error(errorData.error_description || errorData.message || 'Login failed');
    }

    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
};

export const signup = async (username, email, password) => {
    const response = await fetch(`${API_BASE}/signup/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, email, password }),
    });

    const data = await response.json();
    if (!response.ok) {
        console.error('Signup error details:', data);
        throw new Error(data.message || 'Signup failed');
    }
    return data;
};

export const forgotPassword = async (email) => {
    const response = await fetch(`${API_BASE}/auth/forgot-password/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
    });

    const data = await response.json();
    if (!response.ok) {
        console.error('Forgot password error details:', data);
        throw new Error(data.message || 'Request failed');
    }
    return data;
};

export const resetPassword = async (token, password) => {
    const response = await fetch(`${API_BASE}/auth/reset-password/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token, password }),
    });

    const data = await response.json();
    if (!response.ok) {
        console.error('Reset password error details:', data);
        throw new Error(data.message || 'Reset failed');
    }
    return data;
};

export const uploadReminderAttachment = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
    const token = localStorage.getItem('access_token');

    const response = await fetch(`${API_BASE}/reminder/upload-attachment/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || 'Upload failed');
    }
    return data;
};

export const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
};

export const isAuthenticated = () => !!localStorage.getItem('access_token');
