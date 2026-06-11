import React, { useState } from 'react';
import { gql, useMutation, useQuery } from '@apollo/client';
import { X, Paperclip, Loader2, Plus, Info, Calendar, Send, Shield, Hash } from 'lucide-react';
import { uploadReminderAttachment } from '../lib/api';
import CustomRecurrenceModal from './CustomRecurrenceModal';

const MultiSelectDropdown = ({ options, selectedValues, onChange, placeholder }) => {
    const [isOpen, setIsOpen] = React.useState(false);

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
                className={`form-control ${isOpen ? 'active' : ''}`}
                style={{ 
                    minHeight: '44px', 
                    height: 'auto',
                    display: 'flex', 
                    flexWrap: 'wrap', 
                    alignItems: 'center',
                    gap: '6px', 
                    padding: '8px 12px',
                    cursor: 'pointer',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    transition: 'var(--transition)'
                }}
                onClick={() => setIsOpen(!isOpen)}
            >
                {selectedValues.length === 0 && <span style={{ color: 'var(--text-dim)', fontSize: '14px' }}>{placeholder}</span>}
                {selectedValues.map(val => (
                    <span 
                        key={val} 
                        className="badge badge-active"
                        style={{ 
                            padding: '4px 10px', 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '6px',
                            textTransform: 'none',
                            fontSize: '12px'
                        }}
                        onClick={(e) => { e.stopPropagation(); }}
                    >
                        {options.find(o => o.value === val)?.label || val}
                        <X size={12} onClick={(e) => toggleOption(val, e)} style={{ cursor: 'pointer' }} />
                    </span>
                ))}
            </div>

            {isOpen && (
                <div className="filter-dropdown" style={{ width: '100%', marginTop: '4px', maxHeight: '200px', overflowY: 'auto' }}>
                    {options.length === 0 && <div style={{ padding: '12px', color: 'var(--text-dim)', textAlign: 'center', fontSize: '13px' }}>No items found</div>}
                    {options.map(opt => (
                        <button 
                            key={opt.value} 
                            type="button"
                            className={selectedValues.includes(opt.value) ? 'active' : ''}
                            style={{ width: '100%' }}
                            onClick={(e) => {
                                e.stopPropagation();
                                toggleOption(opt.value);
                            }}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};


const GET_FORM_OPTIONS = gql`
  query GetFormOptions {
    slackConfigured
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
    groups {
      id
      name
    }
    departments {
      id
      name
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
    $receiverEmail: String!
    $intervalType: String
    $reminderStartDate: DateTime
    $slackChannels: String
    $slackUserId: String
    $visibleToGroups: [ID]
    $visibleToDepartment: Boolean
    $senderName: String
    $tags: [String]
    $attachmentIds: [ID]
    $customRepeatEvery: Int
    $customRepeatUnit: String
    $customRepeatDays: String
    $customEndCondition: String
    $customEndOccurrences: Int
    $reminderEndDate: DateTime
    $isFormal: Boolean
  ) {
    createReminder(
      title: $title
      description: $description
      senderName: $senderName
      receiverEmail: $receiverEmail
      intervalType: $intervalType
      reminderStartDate: $reminderStartDate
      slackChannels: $slackChannels
      slackUserId: $slackUserId
      visibleToGroups: $visibleToGroups
      visibleToDepartment: $visibleToDepartment
      tags: $tags
      attachmentIds: $attachmentIds
      customRepeatEvery: $customRepeatEvery
      customRepeatUnit: $customRepeatUnit
      customRepeatDays: $customRepeatDays
      customEndCondition: $customEndCondition
      customEndOccurrences: $customEndOccurrences
      reminderEndDate: $reminderEndDate
      isFormal: $isFormal
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
        receiverEmail: '',
        intervalType: 'one_time',
        reminderStartDate: new Date().toISOString().split('T')[0],
        slackChannels: '',
        slackUserId: '',
        visibleToGroups: [],
        visibleToDepartment: false,
        selectedDepartmentId: '',
        senderName: '',
        tags: [],
        attachments: [],
        customRecurrence: {
            repeatEvery: 1,
            repeatUnit: 'week',
            repeatDays: [],
            endCondition: 'never',
            endDate: new Date().toISOString().split('T')[0],
            endOccurrences: 13
        },
        isFormal: false
    });
    const [isUploading, setIsUploading] = useState(false);
    const [showCustomModal, setShowCustomModal] = useState(false);

    const [createReminder, { loading }] = useMutation(CREATE_REMINDER, {
        refetchQueries: [{ query: INITIAL_QUERY }],
        onCompleted: () => {
            if (onSuccess) onSuccess();
            onClose();
            setFormData({
                title: '',
                description: '',
                receiverEmail: '',
                intervalType: 'one_time',
                reminderStartDate: new Date().toISOString().split('T')[0],
                slackChannels: '',
                slackUserId: '',
                visibleToGroups: [],
                visibleToDepartment: false,
                selectedDepartmentId: '',
                senderName: '',
                tags: [],
                attachments: []
            });
        },
        onError: (error) => {
            console.error('Mutation error:', error);
        }
    });

    if (!isOpen) return null;

    const getFrequencyLabel = (type) => {
        if (!formData.reminderStartDate) return type;
        const dt = new Date(formData.reminderStartDate);
        const dayName = dt.toLocaleDateString('en-US', { weekday: 'long' });
        const monthName = dt.toLocaleDateString('en-US', { month: 'long' });
        const dayOfMonth = dt.getDate();
        
        const weekNum = Math.ceil(dayOfMonth / 7);
        const weekOrdinals = ["", "first", "second", "third", "fourth", "last"];
        const weekOrdName = (weekNum > 4) ? "last" : weekOrdinals[weekNum];

        switch(type) {
            case 'one_time': return 'Does not repeat';
            case 'daily': return 'Daily';
            case 'weekly': return 'Weekly';
            case 'monthly': return 'Monthly';
            case 'yearly': return 'Annually';
            case 'weekday': return 'Every weekday (Monday to Friday)';
            case 'custom': return 'Custom...';
            default: return type;
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const vars = {
            ...formData,
            reminderStartDate: new Date(formData.reminderStartDate).toISOString(),
            attachmentIds: formData.attachments.map(a => a.id)
        };

        if (formData.intervalType === 'custom') {
            vars.customRepeatEvery = formData.customRecurrence.repeatEvery;
            vars.customRepeatUnit = formData.customRecurrence.repeatUnit;
            vars.customRepeatDays = formData.customRecurrence.repeatDays.join(',');
            vars.customEndCondition = formData.customRecurrence.endCondition;
            vars.customEndOccurrences = formData.customRecurrence.endOccurrences;
            if (formData.customRecurrence.endCondition === 'on_date') {
                vars.reminderEndDate = new Date(formData.customRecurrence.endDate).toISOString();
            }
        }
        delete vars.customRecurrence;
        delete vars.attachments;

        createReminder({
            variables: vars
        });
    };

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsUploading(true);
        try {
            const result = await uploadReminderAttachment(file);
            setFormData(prev => ({
                ...prev,
                attachments: [...prev.attachments, { id: result.id, filename: result.filename }]
            }));
        } catch (error) {
            console.error('File upload failed:', error);
            alert('File upload failed: ' + error.message);
        } finally {
            setIsUploading(false);
        }
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

                <form onSubmit={handleSubmit} style={{ paddingBottom: '20px' }}>
                    <div className="form-section-title">
                        <Info size={14} /> Identification
                    </div>
                    
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
                        <label>Recipient Emails</label>
                        <input
                            type="text"
                            placeholder="user1@company.com, user2@company.com"
                            required
                            value={formData.receiverEmail}
                            onChange={e => setFormData({ ...formData, receiverEmail: e.target.value })}
                        />
                        <small className="help-text">
                            Separate multiple emails with commas. Example: <b>john@example.com, sarah@example.com</b>
                        </small>
                    </div>

                    <div className="form-row">

                        <div className="form-group">
                            <label>Sender Name (Display)</label>
                            <input
                                type="text"
                                placeholder="E.g. HR | NotifyHub"
                                value={formData.senderName}
                                onChange={e => setFormData({ ...formData, senderName: e.target.value })}
                            />
                            <small className="help-text">
                                Meaningful names (e.g., HR | Company) help identification.
                            </small>
                        </div>
                    </div>

                    <div className="form-section-title">
                        <Calendar size={14} /> Schedule
                    </div>

                    <div className="form-row" style={{ marginBottom: 0 }}>
                        <div className="form-group">
                            <label>Frequency</label>
                            <select
                                value={formData.intervalType}
                                onChange={e => {
                                    setFormData({ ...formData, intervalType: e.target.value });
                                    if (e.target.value === 'custom') {
                                        setShowCustomModal(true);
                                    }
                                }}
                            >
                                <option value="one_time">{getFrequencyLabel('one_time')}</option>
                                <option value="daily">{getFrequencyLabel('daily')}</option>
                                <option value="weekly">{getFrequencyLabel('weekly')}</option>
                                <option value="monthly">{getFrequencyLabel('monthly')}</option>
                                <option value="custom">{getFrequencyLabel('custom')}</option>
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

                    <div className="form-section-title">
                        <Send size={14} /> Notifications
                    </div>

                    {optionsData?.slackConfigured === false ? (
                        /* Slack not connected — show banner instead of broken pickers */
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: '10px',
                            padding: '12px 16px',
                            background: 'rgba(0,171,228,0.06)',
                            border: '1px solid rgba(0,171,228,0.2)',
                            borderRadius: '12px',
                            marginBottom: '4px',
                        }}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00ABE4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                            <span style={{ fontSize: '13px', color: '#4d7a96' }}>
                                Slack is not connected.{' '}
                                <a href="/settings" style={{ color: '#00ABE4', fontWeight: 600, textDecoration: 'none' }}>
                                    Connect Slack in Settings → Integration
                                </a>{' '}
                                to enable channel and user notifications.
                            </span>
                        </div>
                    ) : (
                        <div className="form-row" style={{ marginBottom: 0 }}>
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
                    )}

                    <div className="form-section-title">
                        <Shield size={14} /> Access & Collaboration
                    </div>

                    {/* ── Access row: Department only ── */}
                    <div className="form-row" style={{ alignItems: 'flex-start' }}>
                        {/* Department — checkbox first, then picker appears when ticked */}
                        <div className="form-group">
                            <label style={{ marginBottom: '8px' }}>Department Visibility</label>

                            {/* Step 1: Show the checkbox */}
                            <label className="toggle-label" style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '12px',
                                cursor: 'pointer',
                                padding: '12px 14px',
                                background: formData.visibleToDepartment ? 'rgba(0,171,228,0.06)' : 'var(--bg-card)',
                                borderRadius: 'var(--radius-md)',
                                border: formData.visibleToDepartment ? '1px solid rgba(0,171,228,0.35)' : '1px solid var(--border)',
                                margin: 0,
                                transition: 'all 0.2s ease'
                            }}>
                                <input
                                    type="checkbox"
                                    checked={formData.visibleToDepartment}
                                    onChange={e => setFormData({
                                        ...formData,
                                        visibleToDepartment: e.target.checked,
                                        // clear the selected department when unchecking
                                        selectedDepartmentId: e.target.checked ? formData.selectedDepartmentId : '',
                                    })}
                                    style={{ width: 'auto', margin: '2px 0 0 0', flexShrink: 0, accentColor: '#00ABE4' }}
                                />
                                <div>
                                    <div style={{ fontSize: '13.5px', fontWeight: '600', color: 'var(--text-main)', textTransform: 'none', letterSpacing: 'normal' }}>
                                        Share with my department
                                    </div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '3px', fontWeight: '400' }}>
                                        {formData.visibleToDepartment
                                            ? 'Select which department below'
                                            : 'Tick to restrict visibility to a specific department'}
                                    </div>
                                </div>
                            </label>

                            {/* Step 2: Department picker — only shown when checkbox is ticked */}
                            {formData.visibleToDepartment && (
                                <div style={{ marginTop: '10px', animation: 'fadeIn 0.2s ease' }}>
                                    <select
                                        value={formData.selectedDepartmentId}
                                        onChange={e => setFormData({ ...formData, selectedDepartmentId: e.target.value })}
                                        style={{
                                            width: '100%',
                                            padding: '11px 14px',
                                            borderRadius: 'var(--radius-md)',
                                            border: '1.5px solid rgba(0,171,228,0.35)',
                                            background: 'var(--bg-card)',
                                            color: 'var(--text-main)',
                                            fontSize: '14px',
                                            outline: 'none',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        <option value="">— Select a department —</option>
                                        {(optionsData?.departments || []).map(d => (
                                            <option key={d.id} value={d.id}>{d.name}</option>
                                        ))}
                                    </select>
                                    <small className="help-text">Only members of the selected department will see this reminder</small>
                                </div>
                            )}
                        </div>
                        <div className="form-group">
                            <label style={{ marginBottom: '12px' }}>Formal Task</label>
                            <label className="toggle-label" style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '12px', 
                                cursor: 'pointer', 
                                padding: '10px 14px',
                                background: 'var(--bg-card)',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid var(--border)',
                                margin: 0
                            }}>
                                <input 
                                    type="checkbox" 
                                    checked={formData.isFormal}
                                    onChange={e => setFormData({ ...formData, isFormal: e.target.checked })}
                                    style={{ width: 'auto', margin: 0 }}
                                />
                                <span style={{ fontSize: '13px', fontWeight: 'bold', color: 'var(--text-main)', textTransform: 'none', letterSpacing: 'normal' }}>Mark as Formal (Task)</span>
                            </label>
                            <small className="help-text">Formal reminders appear in Pending Tasks and require completion.</small>
                        </div>
                    </div>

                    <div className="form-section-title">
                        <Hash size={14} /> Details & Assets
                    </div>

                    <div className="form-group">
                        <label>Description (Optional)</label>
                        <textarea
                            rows="3"
                            placeholder="Provide additional context for this reminder..."
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                        ></textarea>
                    </div>

                    <div className="form-group">
                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Paperclip size={16} />
                            Attachments
                        </label>
                        
                        <div className="attachments-list" style={{ marginBottom: '10px' }}>
                            {formData.attachments.map((file, idx) => (
                                <div key={file.id} style={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    gap: '8px', 
                                    padding: '6px 12px', 
                                    background: 'var(--card-bg)', 
                                    borderRadius: 'var(--radius-sm)',
                                    marginBottom: '4px',
                                    border: '1px solid var(--border)',
                                    fontSize: '13px'
                                }}>
                                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.filename}</span>
                                    <X size={14} style={{ cursor: 'pointer', color: 'var(--text-dim)' }} onClick={() => setFormData(prev => ({ ...prev, attachments: prev.attachments.filter(a => a.id !== file.id) }))} />
                                </div>
                            ))}
                        </div>

                        <label className="file-upload-label" style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center', 
                            gap: '8px', 
                            padding: '12px', 
                            border: '2px dashed var(--border)', 
                            borderRadius: 'var(--radius-md)',
                            cursor: 'pointer',
                            color: 'var(--text-dim)',
                            transition: 'var(--transition)'
                        }}>
                            {isUploading ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                            <span>{isUploading ? 'Uploading...' : 'Add File'}</span>
                            <input type="file" style={{ display: 'none' }} onChange={handleFileChange} disabled={isUploading} />
                        </label>
                    </div>

                    <div className="form-group">
                        <label>Tags / Labels</label>
                        <div className="tags-container" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
                            {formData.tags.map(tag => (
                                <span key={tag} className="tag-chip" style={{ 
                                    background: 'var(--primary-glow)', 
                                    padding: '4px 10px', 
                                    borderRadius: '12px',
                                    fontSize: '12px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}>
                                    {tag}
                                    <X size={12} style={{ cursor: 'pointer' }} onClick={() => setFormData({...formData, tags: formData.tags.filter(t => t !== tag)})} />
                                </span>
                            ))}
                        </div>
                        <input
                            type="text"
                            placeholder="Type a tag and press Enter..."
                            onKeyDown={e => {
                                if (e.key === 'Enter' && e.target.value.trim()) {
                                    e.preventDefault();
                                    const val = e.target.value.trim();
                                    if (!formData.tags.includes(val)) {
                                        setFormData({...formData, tags: [...formData.tags, val]});
                                        e.target.value = '';
                                    }
                                }
                            }}
                        />
                    </div>

                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Creating...' : 'Create Reminder'}
                        </button>
                    </div>
                </form>
            </div>

            <CustomRecurrenceModal 
                isOpen={showCustomModal}
                onClose={() => setShowCustomModal(false)}
                initialData={formData.customRecurrence}
                onSave={(data) => setFormData({ ...formData, customRecurrence: data })}
                startingDate={formData.reminderStartDate}
            />
        </div>
    );
}
