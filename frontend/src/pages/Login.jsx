import React, { useState, useEffect } from 'react';
import { Bell, Lock, User, Mail, ArrowRight, RefreshCw, ChevronLeft, Shield } from 'lucide-react';

export default function LoginPage() {
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        // Check if we are returning from Google OAuth
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            localStorage.setItem('access_token', token);
            window.location.href = '/';
        }
    }, []);

    const handleGoogleLogin = () => {
        // Redirect to backend init endpoint
        const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
        window.location.href = `${API_BASE}/google/login/`;
    };

    return (
        <div className="login-page">
            <div className="login-card animate-fade">
                <div className="login-brand-container">
                    <div className="login-logo-box">
                        <Bell size={32} fill="white" strokeWidth={1} />
                    </div>
                    <span className="login-brand-name">Notify<span className="text-gradient">Hub</span></span>
                </div>

                <div className="login-heading">
                    <h1 className="login-title">Welcome</h1>
                    <p className="login-subtitle">Securely log in to your premium workspace</p>
                </div>

                {error && (
                    <div className="alert alert-danger animate-fade">
                        <Lock size={16} />
                        {error}
                    </div>
                )}

                {success && (
                    <div className="alert alert-success animate-fade">
                        <Bell size={16} />
                        {success}
                    </div>
                )}

                <div style={{ marginBottom: '20px', marginTop: '20px' }}>
                    <button
                        type="button"
                        onClick={handleGoogleLogin}
                        className="google-signin-btn"
                        style={{ 
                            width: '100%', 
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center', 
                            gap: '12px',
                            padding: '12px 24px',
                            backgroundColor: 'white',
                            color: '#374151',
                            border: '1px solid #d1d5db',
                            borderRadius: 'var(--radius-md)',
                            fontSize: '14px',
                            fontWeight: '700',
                            cursor: 'pointer',
                            transition: 'var(--transition)',
                            boxShadow: 'var(--shadow-sm)'
                        }}
                        onMouseOver={(e) => {
                            e.currentTarget.style.backgroundColor = '#f9fafb';
                            e.currentTarget.style.borderColor = '#9ca3af';
                        }}
                        onMouseOut={(e) => {
                            e.currentTarget.style.backgroundColor = 'white';
                            e.currentTarget.style.borderColor = '#d1d5db';
                        }}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        <span>Continue with Google</span>
                    </button>
                </div>

                <div className="login-footer">
                    <p>&copy; 2024 NotifyHub Enterprise. Built for excellence.</p>
                </div>
            </div>
        </div>
    );
}
