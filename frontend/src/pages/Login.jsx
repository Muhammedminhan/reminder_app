import React, { useState, useEffect, useRef } from 'react';
import { Bell, Lock } from 'lucide-react';

export default function LoginPage() {
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [btnHovered, setBtnHovered] = useState(false);
    const [cardTilt, setCardTilt] = useState({ x: 0, y: 0 });
    const cardRef = useRef(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            localStorage.setItem('access_token', token);
            window.location.href = '/';
        }
    }, []);

    const handleGoogleLogin = () => {
        const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
        window.location.href = `${API_BASE}/google/login/`;
    };

    const handleMouseMove = (e) => {
        const card = cardRef.current;
        if (!card) return;
        const rect = card.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = (e.clientX - cx) / (rect.width / 2);
        const dy = (e.clientY - cy) / (rect.height / 2);
        setCardTilt({ x: dy * 6, y: -dx * 6 });
    };

    const handleMouseLeave = () => setCardTilt({ x: 0, y: 0 });

    return (
        <div className="lp-root" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
            {/* Animated background orbs */}
            <div className="lp-orb lp-orb1" />
            <div className="lp-orb lp-orb2" />
            <div className="lp-orb lp-orb3" />

            {/* Noise texture overlay */}
            <div className="lp-noise" />

            <div
                ref={cardRef}
                className="lp-card"
                style={{
                    transform: `perspective(900px) rotateX(${cardTilt.x}deg) rotateY(${cardTilt.y}deg) translateZ(0)`,
                }}
            >
                {/* Top shimmer line */}
                <div className="lp-card-shimmer" />

                {/* Logo */}
                <div className="lp-logo-wrap">
                    <div className="lp-logo-ring" />
                    <div className="lp-logo-box">
                        <Bell size={28} fill="white" strokeWidth={0.5} />
                    </div>
                </div>

                {/* Brand */}
                <div className="lp-brand">
                    Notify<span className="lp-brand-accent">Hub</span>
                </div>

                {/* Heading */}
                <div className="lp-heading">
                    <h1 className="lp-title">Welcome back</h1>
                    <p className="lp-subtitle">Sign in to your workspace</p>
                </div>

                {/* Divider */}
                <div className="lp-divider">
                    <span />
                    <small>continue with</small>
                    <span />
                </div>

                {/* Google Button */}
                <button
                    type="button"
                    onClick={handleGoogleLogin}
                    className={`lp-google-btn ${btnHovered ? 'lp-google-btn--hovered' : ''}`}
                    onMouseEnter={() => setBtnHovered(true)}
                    onMouseLeave={() => setBtnHovered(false)}
                >
                    <span className="lp-google-btn-bg" />
                    <svg className="lp-google-icon" width="20" height="20" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    <span className="lp-google-btn-text">Continue with Google</span>
                </button>

                {error && (
                    <div className="lp-alert lp-alert--error">
                        <Lock size={14} /> {error}
                    </div>
                )}
                {success && (
                    <div className="lp-alert lp-alert--success">
                        <Bell size={14} /> {success}
                    </div>
                )}

                <p className="lp-footer">© 2024 NotifyHub Enterprise</p>
            </div>
        </div>
    );
}
