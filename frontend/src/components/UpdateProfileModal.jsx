import React, { useState, useEffect, useRef } from 'react';
import { gql, useMutation } from '@apollo/client';
import { X, User, Mail, Shield, Camera, Trash2 } from 'lucide-react';

const UPDATE_ME = gql`
  mutation UpdateMe($firstName: String, $lastName: String, $email: String) {
    updateMe(firstName: $firstName, lastName: $lastName, email: $email) {
      ok
      user {
        id
        firstName
        lastName
        email
        profilePicture
      }
    }
  }
`;

const INITIAL_QUERY = gql`
  query GetInitialData {
    reminders {
      id
      title
      description
      senderEmail
      receiverEmail
      intervalType
      reminderStartDate
      active
      completed
    }
    me {
      id
      username
      email
      firstName
      lastName
      profilePicture
      company {
        name
      }
      departments {
        id
        name
      }
    }
    users {
      id
      username
      email
      firstName
      lastName
      profilePicture
      departments {
        id
        name
      }
    }
  }
`;

export default function UpdateProfileModal({ isOpen, onClose, user, onSuccess }) {
    const fileInputRef = useRef(null);
    const [formData, setFormData] = useState({
        firstName: '',
        lastName: '',
        email: ''
    });
    const [uploading, setUploading] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const [isTrashHovered, setIsTrashHovered] = useState(false);

    useEffect(() => {
        if (user) {
            setFormData({
                firstName: user.firstName || user.first_name || '',
                lastName: user.lastName || user.last_name || '',
                email: user.email || ''
            });
        }
    }, [user, isOpen]);

    const [updateMe, { loading }] = useMutation(UPDATE_ME, {
        refetchQueries: [{ query: INITIAL_QUERY }],
        onCompleted: () => {
            if (onSuccess) onSuccess('Profile updated successfully');
            onClose();
        },
        onError: (error) => {
            console.error('Update error:', error);
            if (onSuccess) onSuccess('Failed to update profile');
        }
    });

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        updateMe({
            variables: formData
        });
    };

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('profile_picture', file);

        setUploading(true);
        try {
            const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/user/profile-picture/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: formData
            });

            const data = await response.json();
            if (data.ok) {
                if (onSuccess) onSuccess('Profile picture updated');
                // Force state update if needed, but refetch should handle it
            } else {
                if (onSuccess) onSuccess(data.message || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            if (onSuccess) onSuccess('Server error during upload');
        } finally {
            setUploading(false);
        }
    };

    const handleRemovePicture = async () => {
        if (!window.confirm('Are you sure you want to remove your profile picture?')) return;

        setUploading(true);
        try {
            const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
            const response = await fetch(`${API_BASE}/user/profile-picture/`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            const data = await response.json();
            if (data.ok) {
                if (onSuccess) onSuccess('Profile picture removed');
            } else {
                if (onSuccess) onSuccess(data.message || 'Removal failed');
            }
        } catch (error) {
            console.error('Removal error:', error);
            if (onSuccess) onSuccess('Server error during removal');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-container animate-fade">
                <button onClick={onClose} className="modal-close">
                    <X size={20} />
                </button>

                <div className="modal-header" style={{ textAlign: 'center' }}>
                    <div className="profile-upload-wrapper">
                        <div className="profile-avatar-large">
                            {(user?.profilePicture || user?.avatar) ? (
                                <img src={`${(user.profilePicture || user.avatar).startsWith('http') ? '' : (import.meta.env.VITE_API_BASE || 'http://localhost:8000')}${user.profilePicture || user.avatar}${(user.profilePicture || user.avatar).includes('?') ? '&' : '?'}t=${Date.now()}`} alt="Profile" />
                            ) : (
                                <div className="avatar-placeholder">
                                    <User size={48} />
                                </div>
                            )}
                        </div>
                        <div className="avatar-actions">
                            <button
                                type="button"
                                className="action-btn-primary"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                                title="Upload Photo"
                            >
                                <Camera size={18} />
                            </button>
                            {(user?.profilePicture || user?.avatar) && (
                                <button
                                    type="button"
                                    className="action-btn-danger"
                                    onClick={handleRemovePicture}
                                    disabled={uploading}
                                    title="Remove Photo"
                                >
                                    <Trash2 size={18} />
                                </button>
                            )}
                        </div>
                        <input
                            type="file"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            accept="image/*"
                            onChange={handleFileChange}
                        />
                    </div>
                    <h2>Update Profile</h2>
                    <p>Modify your personal account information.</p>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-row">
                        <div className="form-group">
                            <label>First Name</label>
                            <div className="input-with-icon">
                                <User size={16} className="input-icon" />
                                <input
                                    type="text"
                                    placeholder="John"
                                    value={formData.firstName}
                                    onChange={e => setFormData({ ...formData, firstName: e.target.value })}
                                />
                            </div>
                        </div>
                        <div className="form-group">
                            <label>Last Name</label>
                            <input
                                type="text"
                                placeholder="Doe"
                                value={formData.lastName}
                                onChange={e => setFormData({ ...formData, lastName: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Email Address</label>
                        <div className="input-with-icon">
                            <Mail size={16} className="input-icon" />
                            <input
                                type="email"
                                placeholder="john.doe@notfiyhub.com"
                                required
                                value={formData.email}
                                onChange={e => setFormData({ ...formData, email: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Assigned Departments</label>
                        <div className="depts-display-grid" style={{ 
                            display: 'flex', 
                            flexWrap: 'wrap', 
                            gap: '8px', 
                            marginTop: '8px',
                            minHeight: '40px',
                            padding: '8px',
                            backgroundColor: 'var(--bg-card)',
                            borderRadius: '8px',
                            border: '1px solid var(--border)'
                        }}>
                            {user?.departments?.map(d => (
                                <span key={d.id} className="dept-tag" style={{ 
                                    backgroundColor: 'var(--primary-glow)', 
                                    color: 'var(--primary)', 
                                    padding: '4px 12px', 
                                    borderRadius: '16px', 
                                    fontSize: '12px',
                                    fontWeight: '600',
                                    border: '1px solid var(--primary)'
                                }}>{d.name}</span>
                            ))}
                            {(!user?.departments || user.departments.length === 0) && (
                                <span style={{ color: 'var(--text-dim)', fontSize: '13px' }}>No departments assigned.</span>
                            )}
                        </div>
                        <small className="help-text">Contact your administrator to change department assignments.</small>
                    </div>

                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Updating...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
