import React, { useState, useEffect } from 'react';
import { login, signup, forgotPassword } from '../lib/api';
import { Bell, Lock, User, Mail, ArrowRight, RefreshCw, ChevronLeft, Shield } from 'lucide-react';

export default function LoginPage() {
    const [mode, setMode] = useState('login'); // 'login', 'signup', 'forgot'
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const [mfaToken, setMfaToken] = useState('');
    const [mfaCode, setMfaCode] = useState('');

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
        // Redirect to backend init endpoint — using build-time env or fallback
        const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
        window.location.href = `${API_BASE}/google/login/`;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setSuccess('');
        try {
            if (mode === 'mfa') {
                const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
                const resp = await fetch(`${API_BASE}/mfa/verify/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mfa_challenge_id: mfaToken, totp_code: mfaCode })
                });
                const data = await resp.json();
                if (!data.ok) throw new Error(data.message || 'Verification failed');
                // The backend currently issues an mfa_token which can be used for /o/token/ 
                // For now, we will notify the user they are verified.
                setSuccess('Security verification successful! Finalizing session...');
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                window.location.href = '/';
                return;
            }

            if (mode === 'login') {
                const data = await login(username, password);
                if (data?.mfa_required) {
                    setMfaToken(data.mfa_token);
                    setMode('mfa');
                    return;
                }
                window.location.href = '/';
            } else if (mode === 'signup') {
                try {
                    await signup(username, email, password);
                } catch (err) {
                    if (err.message && (err.message.includes('exists') || err.message.includes('taken'))) {
                        const data = await login(username, password);
                        if (data?.mfa_required) {
                            setMfaToken(data.mfa_token);
                            setMode('mfa');
                            return;
                        }
                        window.location.href = '/';
                        return;
                    }
                    throw err;
                }
                const data = await login(username, password);
                if (data?.mfa_required) {
                    setMfaToken(data.mfa_token);
                    setMode('mfa');
                    return;
                }
                window.location.href = '/';
            } else if (mode === 'forgot') {
                await forgotPassword(email);
                setSuccess('Password reset link has been sent to your email.');
                setEmail('');
            }
        } catch (err) {
            setError(err.message || 'Action failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const renderForm = () => {
        if (mode === 'forgot') {
            return (
                <form onSubmit={handleSubmit} className="animate-fade">
                    <div className="form-group">
                        <label>Email Address</label>
                        <div className="input-with-icon">
                            <Mail size={18} className="input-icon" />
                            <input
                                type="email"
                                placeholder="Enter your email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                    </div>
                    <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                        {loading ? <RefreshCw size={20} className="loading-spinner" /> : <span>Reset Password</span>}
                    </button>
                    <div style={{ marginTop: '24px', textAlign: 'center' }}>
                    </div>
                </form>
            );
        }

        return (
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Username</label>
                    <div className="input-with-icon">
                        <User size={18} className="input-icon" />
                        <input
                            type="text"
                            placeholder="Enter your username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                </div>

                {mode === 'signup' && (
                    <div className="form-group animate-fade">
                        <label>Email Address</label>
                        <div className="input-with-icon">
                            <Mail size={18} className="input-icon" />
                            <input
                                type="email"
                                placeholder="Enter your email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                    </div>
                )}

                <div className="form-group">
                    <label>Password</label>
                    <div className="input-with-icon">
                        <Lock size={18} className="input-icon" />
                        <input
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                </div>

                <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }} disabled={loading}>
                    {loading ? (
                        <>
                            <RefreshCw size={20} className="loading-spinner" />
                            <span>{mode === 'login' ? 'Authenticating...' : 'Creating Account...'}</span>
                        </>
                    ) : (
                        <>
                            <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                            <ArrowRight size={20} />
                        </>
                    )}
                </button>

                {mode === 'login' && (
                    <div style={{ marginTop: '20px', textAlign: 'center' }}>
                        <button type="button" onClick={() => setMode('forgot')} className="text-gradient hover-underline" style={{ fontSize: '13px', fontWeight: '800', cursor: 'pointer', border: 'none', background: 'none' }}>Trouble signing in?</button>
                    </div>
                )}

                <div className="login-divider" style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    margin: '32px 0 24px', 
                    color: 'var(--text-dim)', 
                    fontSize: '12px', 
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                }}>
                    <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
                    <span style={{ padding: '0 16px' }}>Or continue with</span>
                    <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
                </div>

                <div style={{ marginBottom: '20px' }}>
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
                        <span>{mode === 'login' ? 'Continue with Google' : 'Sign up with Google'}</span>
                    </button>
                </div>

                <div style={{ textAlign: 'center' }}>
                    <p style={{ color: 'var(--text-dim)', fontSize: '13px', marginBottom: '16px' }}>
                        {mode === 'login' ? "New to NotifyHub? Launch your workspace today." : mode === 'mfa' ? "Having trouble with your device?" : "Already have a verified account?"}
                    </p>
                    <button
                        type="button"
                        onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
                        className="btn-secondary"
                        style={{ width: '100%', justifyContent: 'center' }}
                    >
                        {mode === 'login' ? 'Create New Account' : mode === 'mfa' ? 'Back to Sign In' : 'Sign In Now'}
                    </button>
                </div>
            </form>
        );
    };

    const renderMfaForm = () => (
        <form onSubmit={handleSubmit}>
            <div className="form-group">
                <label>Security Code</label>
                <div className="input-with-icon">
                    <Shield size={18} className="input-icon" />
                    <input
                        type="text"
                        placeholder="Enter 6-digit code"
                        value={mfaCode}
                        onChange={(e) => setMfaCode(e.target.value)}
                        required
                        autoFocus
                    />
                </div>
            </div>

            <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '16px' }} disabled={loading}>
                {loading ? <RefreshCw size={20} className="loading-spinner" /> : <span>Verify and Connect</span>}
            </button>

            <div style={{ textAlign: 'center', marginTop: '24px' }}>
                <button
                    type="button"
                    onClick={() => setMode('login')}
                    className="text-gradient hover-underline"
                    style={{ fontSize: '14px', fontWeight: '800', cursor: 'pointer', border: 'none', background: 'none' }}
                >
                    Cancel and go back
                </button>
            </div>
        </form>
    );

    return (
        <div className="login-page">
            <div className="login-card animate-fade">
                <div className="login-brand-container">
                    {mode !== 'login' && (
                        <button
                            className="back-button"
                            onClick={() => setMode('login')}
                            style={{ position: 'absolute', left: '24px', top: '24px' }}
                            title="Go Back"
                        >
                            <ChevronLeft size={20} />
                        </button>
                    )}
                    <div className="login-logo-box">
                        <Bell size={32} fill="white" strokeWidth={1} />
                    </div>
                    <span className="login-brand-name">Notify<span className="text-gradient">Hub</span></span>
                </div>

                <div className="login-heading">
                    <h1 className="login-title">
                        {mode === 'login' ? 'Welcome Back' : mode === 'signup' ? 'Join NotifyHub' : mode === 'mfa' ? 'Security Check' : 'Reset Password'}
                    </h1>
                    <p className="login-subtitle">
                        {mode === 'login' ? 'Securely log in to your premium workspace' : mode === 'signup' ? 'Create a premium account to start tracking' : mode === 'mfa' ? 'Please enter the code from your authenticator app' : 'Enter your email to receive a reset link'}
                    </p>
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

                {mode === 'mfa' ? renderMfaForm() : renderForm()}

                <div className="login-footer">
                    <p>&copy; 2024 NotifyHub Enterprise. Built for excellence.</p>
                </div>
            </div>
        </div>
    );
}
