import React from 'react';

/**
 * ErrorBoundary — catches any unhandled JavaScript errors in the React tree
 * and shows a friendly recovery screen instead of a blank white page.
 *
 * Usage (in main.jsx or App.jsx):
 *   <ErrorBoundary>
 *     <App />
 *   </ErrorBoundary>
 *
 * Error boundaries must be class components — React does not support the
 * getDerivedStateFromError / componentDidCatch lifecycle in function components.
 */
export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, info) {
        // Log the error so it appears in Cloud Run / browser console
        console.error('[ErrorBoundary] Uncaught error:', error, info?.componentStack);
    }

    handleReload = () => {
        // Reset state and attempt a full reload
        this.setState({ hasError: false, error: null });
        window.location.reload();
    };

    handleGoHome = () => {
        this.setState({ hasError: false, error: null });
        window.location.href = '/';
    };

    render() {
        if (!this.state.hasError) return this.props.children;

        return (
            <div style={styles.root}>
                <div style={styles.card}>
                    {/* Bell icon */}
                    <div style={styles.iconWrap}>
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="white" stroke="none">
                            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
                            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                        </svg>
                    </div>

                    <h1 style={styles.heading}>Something went wrong</h1>
                    <p style={styles.sub}>
                        An unexpected error occurred. Your data is safe — this is a display
                        issue only.
                    </p>

                    {/* Show error message in development */}
                    {import.meta.env.DEV && this.state.error && (
                        <pre style={styles.devError}>
                            {this.state.error.toString()}
                        </pre>
                    )}

                    <div style={styles.actions}>
                        <button style={styles.btnPrimary} onClick={this.handleReload}>
                            Reload page
                        </button>
                        <button style={styles.btnSecondary} onClick={this.handleGoHome}>
                            Go to dashboard
                        </button>
                    </div>

                    <p style={styles.footer}>
                        If this keeps happening, please contact support.
                    </p>
                </div>
            </div>
        );
    }
}

const styles = {
    root: {
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#E9F1FA',
        padding: '20px',
        fontFamily: "'Outfit', 'Inter', system-ui, sans-serif",
    },
    card: {
        background: '#ffffff',
        border: '1px solid rgba(0,171,228,0.2)',
        borderRadius: '24px',
        padding: '40px 36px',
        maxWidth: '460px',
        width: '100%',
        textAlign: 'center',
        boxShadow: '0 8px 32px rgba(0,171,228,0.1)',
    },
    iconWrap: {
        width: '64px',
        height: '64px',
        background: 'linear-gradient(135deg, #00ABE4, #0090c4)',
        borderRadius: '18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 20px',
        boxShadow: '0 4px 16px rgba(0,171,228,0.35)',
    },
    heading: {
        fontSize: '22px',
        fontWeight: '700',
        color: '#0d1f2d',
        marginBottom: '10px',
    },
    sub: {
        fontSize: '14px',
        color: '#6b8099',
        lineHeight: '1.6',
        marginBottom: '24px',
    },
    devError: {
        background: '#f4f8fc',
        border: '1px solid rgba(0,171,228,0.2)',
        borderRadius: '10px',
        padding: '12px 16px',
        fontSize: '12px',
        color: '#c0392b',
        textAlign: 'left',
        overflowX: 'auto',
        marginBottom: '24px',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
    },
    actions: {
        display: 'flex',
        gap: '12px',
        justifyContent: 'center',
        marginBottom: '20px',
    },
    btnPrimary: {
        padding: '11px 24px',
        background: '#00ABE4',
        color: '#fff',
        border: 'none',
        borderRadius: '12px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
        boxShadow: '0 4px 12px rgba(0,171,228,0.35)',
    },
    btnSecondary: {
        padding: '11px 24px',
        background: '#fff',
        color: '#0d1f2d',
        border: '1.5px solid rgba(0,171,228,0.3)',
        borderRadius: '12px',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
    },
    footer: {
        fontSize: '12px',
        color: 'rgba(107,128,153,0.6)',
    },
};
