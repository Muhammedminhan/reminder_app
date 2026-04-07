import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { resetPassword } from '../lib/api';
import { Bell, Lock, ArrowRight, RefreshCw, CheckCircle, ChevronLeft } from 'lucide-react';

export default function ResetPasswordPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!token) {
            setError('Invalid or missing reset token.');
        }
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters long.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            await resetPassword(token, password);
            setSuccess(true);
            setTimeout(() => {
                navigate('/login');
            }, 3000);
        } catch (err) {
            setError(err.message || 'Failed to reset password.');
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="login-page">
                <div className="login-card animate-fade">
                    <div className="login-brand-container">
                        <div className="login-logo-box">
                            <Bell size={32} fill="white" strokeWidth={1} />
                        </div>
                        <span className="login-brand-name">Notify<span className="text-gradient">Hub</span></span>
                    </div>
                    <div style={{ textAlign: 'center', marginTop: '40px' }}>
                        <div style={{ color: 'var(--success)', marginBottom: '20px' }}>
                            <CheckCircle size={64} style={{ margin: '0 auto' }} />
                        </div>
                        <h1 className="login-title">Password Reset!</h1>
                        <p className="login-subtitle">Your password has been successfully updated. Redirecting you to login...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="login-page">
            <div className="login-card">
                <div className="login-brand-container">
                    <button
                        className="back-button"
                        onClick={() => navigate('/login')}
                        style={{ position: 'absolute', left: '24px', top: '24px' }}
                        title="Back to Login"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <div className="login-logo-box">
                        <Bell size={32} fill="white" strokeWidth={1} />
                    </div>
                    <span className="login-brand-name">Notify<span className="text-gradient">Hub</span></span>
                </div>

                <div className="login-heading">
                    <h1 className="login-title">New Password</h1>
                    <p className="login-subtitle">Create a strong, new password for your account</p>
                </div>

                {error && (
                    <div className="alert alert-danger animate-fade">
                        <Lock size={16} />
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>New Password</label>
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

                    <div className="form-group">
                        <label>Confirm Password</label>
                        <div className="input-with-icon">
                            <Lock size={18} className="input-icon" />
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading || !token}>
                        {loading ? (
                            <>
                                <RefreshCw size={20} className="loading-spinner" />
                                <span>Updating...</span>
                            </>
                        ) : (
                            <>
                                <span>Update Password</span>
                                <ArrowRight size={20} />
                            </>
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <p>&copy; 2024 NotifyHub Enterprise. Built for excellence.</p>
                </div>
            </div>
        </div>
    );
}
