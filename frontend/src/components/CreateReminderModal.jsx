import React, { useState } from 'react';
import { gql, useMutation, useQuery } from '@apollo/client';
import { X } from 'lucide-react';

const MultiSelectDropdown = ({ options, selectedValues, onChange, placeholder }) => {
    const [isOpen, setIsOpen] = useState(false);

    const toggleOption = (val, e) => {
        if (e) e.stopPropagation();
        if (selectedValues.includes(val)) {
            onChange(selectedValues.filter(v => v !== val));
        } else {
            onChange([...selectedValues, val]);
        }
    };

    return (
        <div style={{ position: 'relative', width: '100%' }}>
            <div 
                className="form-control"
                style={{ 
                    minHeight: '40px', 
                    height: 'auto',
                    display: 'flex', 
                    flexWrap: 'wrap', 
                    alignItems: 'center',
                    gap: '6px', 
                    padding: '8px',
                    cursor: 'pointer'
                }}
                onClick={() => setIsOpen(!isOpen)}
            >
                {selectedValues.length === 0 && <span style={{ color: 'var(--text-dim)' }}>{placeholder}</span>}
                {selectedValues.map(val => (
                    <span 
                        key={val} 
                        style={{ 
                            backgroundColor: 'var(--primary)', 
                            color: 'white', 
                            padding: '4px 10px', 
                            borderRadius: '20px', 
                            fontSize: '11px', 
                            fontWeight: '800',
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '4px' 
                        }}
                        onClick={(e) => { e.stopPropagation(); }}
                    >
                        {options.find(o => o.value === val)?.label || val}
                        <X size={12} onClick={(e) => toggleOption(val, e)} style={{ cursor: 'pointer' }} />
                    </span>
                ))}
            </div>

            {isOpen && (
                <div style={{ 
                    position: 'absolute', 
                    top: 'calc(100% + 4px)', 
                    left: 0, 
                    right: 0, 
                    backgroundColor: 'var(--bg-surface)', 
                    border: '1px solid var(--border)', 
                    borderRadius: '8px', 
                    zIndex: 50, 
                    maxHeight: '180px', 
                    overflowY: 'auto',
                    boxShadow: 'var(--shadow-md)',
                    color: 'var(--text-main)'
                }}>
                    {options.length === 0 && <div style={{ padding: '8px', color: 'var(--text-dim)', textAlign: 'center', fontSize: '13px' }}>No items found</div>}
                    {options.map(opt => (
                        <div 
                            key={opt.value} 
                            style={{ 
                                padding: '8px 12px', 
                                cursor: 'pointer', 
                                fontSize: '14px',
                                backgroundColor: selectedValues.includes(opt.value) ? 'var(--bg-card-hover)' : 'transparent',
                                borderBottom: '1px solid var(--border)'
                            }}
                            onClick={() => {
                                toggleOption(opt.value);
                            }}
                            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)'}
                            onMouseLeave={e => e.currentTarget.style.backgroundColor = selectedValues.includes(opt.value) ? 'var(--bg-card-hover)' : 'transparent'}
                        >
                            {opt.label}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const GET_FORM_OPTIONS = gql`
  query GetFormOptions {
    slackChannels {
      id
      name
    }
    users {
      id
      firstName
      lastName
      email
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
      slackChannels
      slackUserId
    }
  }
`;

const CREATE_REMINDER = gql`
  mutation CreateReminder(
    $title: String!
    $description: String
    $senderEmail: String!
    $receiverEmail: String!
    $intervalType: String
    $reminderStartDate: DateTime
    $slackChannels: String
    $slackUserId: String
  ) {
    createReminder(
      title: $title
      description: $description
      senderEmail: $senderEmail
      receiverEmail: $receiverEmail
      intervalType: $intervalType
      reminderStartDate: $reminderStartDate
      slackChannels: $slackChannels
      slackUserId: $slackUserId
    ) {
      ok
      reminder {
        id
        title
      }
    }
  }
`;

export default function CreateReminderModal({ isOpen, onClose, onSuccess }) {
    const { data: optionsData } = useQuery(GET_FORM_OPTIONS, { skip: !isOpen });

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        senderEmail: 'admin@example.com',
        receiverEmail: '',
        intervalType: 'daily',
        reminderStartDate: new Date().toISOString().split('T')[0],
        slackChannels: '',
        slackUserId: ''
    });

    const [createReminder, { loading }] = useMutation(CREATE_REMINDER, {
        refetchQueries: [{ query: INITIAL_QUERY }],
        onCompleted: () => {
            if (onSuccess) onSuccess();
            onClose();
            setFormData({
                title: '',
                description: '',
                senderEmail: 'admin@example.com',
                receiverEmail: '',
                intervalType: 'daily',
                reminderStartDate: new Date().toISOString().split('T')[0],
                slackChannels: '',
                slackUserId: ''
            });
        },
        onError: (error) => {
            console.error('Mutation error:', error);
        }
    });

    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        createReminder({
            variables: {
                ...formData,
                reminderStartDate: new Date(formData.reminderStartDate).toISOString()
            }
        });
    };

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-container animate-fade">
                <button
                    onClick={onClose}
                    className="modal-close"
                >
                    <X size={20} />
                </button>

                <div className="modal-header">
                    <h2>Create New Reminder</h2>
                    <p>Fill in the details to schedule a new notification.</p>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Title</label>
                        <input
                            type="text"
                            placeholder="E.g. Monthly Business Review"
                            required
                            value={formData.title}
                            onChange={e => setFormData({ ...formData, title: e.target.value })}
                        />
                    </div>

                    <div className="form-group">
                        <label>Recipient Email</label>
                        <input
                            type="email"
                            placeholder="client@company.com"
                            required
                            value={formData.receiverEmail}
                            onChange={e => setFormData({ ...formData, receiverEmail: e.target.value })}
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Frequency</label>
                            <select
                                value={formData.intervalType}
                                onChange={e => setFormData({ ...formData, intervalType: e.target.value })}
                            >
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                                <option value="monthly">Monthly</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Start Date</label>
                            <input
                                type="date"
                                value={formData.reminderStartDate}
                                onChange={e => setFormData({ ...formData, reminderStartDate: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Slack Channels</label>
                            <MultiSelectDropdown
                                placeholder="Select channels..."
                                options={(optionsData?.slackChannels || []).map(ch => ({ value: ch.name, label: ch.name }))}
                                selectedValues={formData.slackChannels ? formData.slackChannels.split(',').filter(Boolean) : []}
                                onChange={values => setFormData({ ...formData, slackChannels: values.join(',') })}
                            />
                        </div>
                        <div className="form-group">
                            <label>Slack Users (Teammates)</label>
                            <MultiSelectDropdown
                                placeholder="Select teammates..."
                                options={(optionsData?.users || []).map(u => ({ value: u.id, label: u.firstName || u.lastName ? `${u.firstName} ${u.lastName}` : u.email }))}
                                selectedValues={formData.slackUserId ? formData.slackUserId.split(',').filter(Boolean) : []}
                                onChange={values => setFormData({ ...formData, slackUserId: values.join(',') })}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Description (Optional)</label>
                        <textarea
                            rows="4"
                            placeholder="Provide additional context for this reminder..."
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                        ></textarea>
                    </div>

                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Creating...' : 'Create Reminder'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
