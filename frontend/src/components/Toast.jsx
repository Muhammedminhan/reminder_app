import React, { useState, useEffect, useRef } from 'react';
import {
    CheckCircle,
    AlertCircle,
    X
} from 'lucide-react';



export const useToast = () => {
    const [toast, setToast] = useState(null);
    const timeoutRef = useRef(null);

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => setToast(null), 3000);
    };

    const hideToast = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setToast(null);
    };

    // Cleanup on unmount
    useEffect(() => () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
    }, []);

    return { toast, showToast, hideToast };
};

export default function Toast({ toast, onClose }) {
    if (!toast) return null;

    const icons = {
        success: <CheckCircle color="var(--success)" size={20} />,
        error: <AlertCircle color="var(--danger)" size={20} />,
        warning: <AlertCircle color="var(--warning)" size={20} />
    };

    return (
        <div className={`toast toast-${toast.type}`} onClick={onClose}>
            {icons[toast.type]}
            <span style={{ fontSize: '14px', fontWeight: '500', marginLeft: '8px' }}>{toast.message}</span>
            <button onClick={onClose} style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>
                <X size={16} />
            </button>
        </div>
    );
}
