import React from 'react';
import { X, Minus, Plus, Clock } from 'lucide-react';

const DAYS = [
    { label: 'S', value: 0 },
    { label: 'M', value: 1 },
    { label: 'T', value: 2 },
    { label: 'W', value: 3 },
    { label: 'T', value: 4 },
    { label: 'F', value: 5 },
    { label: 'S', value: 6 },
];

const UNITS = ['day', 'week', 'month', 'year'];

export default function CustomRecurrenceModal({ isOpen, onClose, onSave, initialData }) {
    const [repeatEvery, setRepeatEvery] = React.useState(initialData?.repeatEvery || 1);
    const [repeatUnit, setRepeatUnit] = React.useState(initialData?.repeatUnit || 'week');
    const [repeatDays, setRepeatDays] = React.useState(initialData?.repeatDays || []);
    const [endCondition, setEndCondition] = React.useState(initialData?.endCondition || 'never');
    const [endDate, setEndDate] = React.useState(initialData?.endDate || new Date().toISOString().split('T')[0]);
    const [endOccurrences, setEndOccurrences] = React.useState(initialData?.endOccurrences || 13);

    if (!isOpen) return null;

    const handleToggleDay = (day) => {
        if (repeatDays.includes(day)) {
            setRepeatDays(repeatDays.filter(d => d !== day));
        } else {
            setRepeatDays([...repeatDays, day]);
        }
    };

    const generateSummary = () => {
        let summary = `Repeats every ${repeatEvery || 1} ${repeatUnit}${repeatEvery > 1 ? 's' : ''}`;
        
        if ((repeatUnit === 'week' || repeatUnit === 'month') && repeatDays.length > 0) {
            const dayLabels = repeatDays.map(d => DAYS.find(day => day.value === d)?.label).join(', ');
            summary += ` on ${dayLabels}`;
        }

        if (endCondition === 'on_date') {
            summary += `, until ${new Date(endDate).toLocaleDateString()}`;
        } else if (endCondition === 'after_count') {
            summary += `, for ${endOccurrences} occurrences`;
        }

        return summary;
    };

    const handleSave = () => {
        onSave({
            repeatEvery: parseInt(repeatEvery) || 1,
            repeatUnit,
            repeatDays,
            endCondition,
            endDate,
            endOccurrences
        });
        onClose();
    };

    return (
        <div className="modal-overlay" style={{ zIndex: 1200 }} onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-container animate-scale" style={{ maxWidth: '440px', padding: '32px' }}>
                <button onClick={onClose} className="modal-close">
                    <X size={20} />
                </button>

                <div className="modal-header">
                    <h2>Custom Recurrence</h2>
                    <p>Fine-tune how often this reminder repeats.</p>
                </div>

                <div className="form-group">
                    <label>Repeat every</label>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <div className="stepper-container">
                            <button 
                                type="button"
                                className="stepper-btn" 
                                onClick={() => setRepeatEvery(prev => Math.max(1, (parseInt(prev) || 1) - 1))}
                            >
                                <Minus size={16} />
                            </button>
                            <input 
                                type="number" 
                                className="stepper-input"
                                value={repeatEvery} 
                                readOnly
                                min="1"
                                max={repeatUnit === 'month' ? 12 : undefined}
                            />
                            <button 
                                type="button"
                                className="stepper-btn" 
                                onClick={() => setRepeatEvery(prev => {
                                    const current = parseInt(prev) || 0;
                                    if (repeatUnit === 'month') return Math.min(12, current + 1);
                                    return current + 1;
                                })}
                            >
                                <Plus size={16} />
                            </button>
                        </div>
                        
                        <div className="option-group" style={{ flex: 1 }}>
                            {UNITS.map(unit => (
                                <button
                                    key={unit}
                                    type="button"
                                    className={`option-item ${repeatUnit === unit ? 'active' : ''}`}
                                    onClick={() => {
                                        setRepeatUnit(unit);
                                        if (unit === 'month' && repeatEvery > 12) {
                                            setRepeatEvery(12);
                                        }
                                    }}
                                >
                                    {unit}s
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {(repeatUnit === 'week' || repeatUnit === 'month') && (
                    <div className="form-group">
                        <label>Repeat on</label>
                        <div className="day-selector">
                            {DAYS.map(day => (
                                <button
                                    key={day.value}
                                    type="button"
                                    onClick={() => handleToggleDay(day.value)}
                                    className={`day-btn ${repeatDays.includes(day.value) ? 'active' : ''}`}
                                >
                                    {day.label}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <div className="form-group">
                    <label>Ends</label>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div 
                            className={`selection-control ${endCondition === 'never' ? 'active' : ''}`}
                            onClick={() => setEndCondition('never')}
                        >
                            <div className="radio-circle" />
                            <span style={{ fontSize: '14px', fontWeight: '600' }}>Never</span>
                        </div>

                        <div 
                            className={`selection-control ${endCondition === 'on_date' ? 'active' : ''}`}
                            onClick={() => setEndCondition('on_date')}
                        >
                            <div className="radio-circle" />
                            <span style={{ fontSize: '14px', fontWeight: '600', width: '40px' }}>On</span>
                            <div style={{ flex: 1, position: 'relative' }}>
                                <input 
                                    type="date" 
                                    value={endDate}
                                    onChange={e => setEndDate(e.target.value)}
                                    disabled={endCondition !== 'on_date'}
                                    style={{ 
                                        padding: '8px 12px', 
                                        opacity: endCondition === 'on_date' ? 1 : 0.4,
                                        width: '100%',
                                        pointerEvents: endCondition === 'on_date' ? 'auto' : 'none'
                                    }}
                                />
                            </div>
                        </div>

                        <div 
                            className={`selection-control ${endCondition === 'after_count' ? 'active' : ''}`}
                            onClick={() => setEndCondition('after_count')}
                        >
                            <div className="radio-circle" />
                            <span style={{ fontSize: '14px', fontWeight: '600', width: '40px' }}>After</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                                <div className="stepper-container">
                                    <button 
                                        type="button"
                                        className="stepper-btn" 
                                        disabled={endCondition !== 'after_count'}
                                        onClick={(e) => { e.stopPropagation(); setEndOccurrences(Math.max(1, endOccurrences - 1)); }}
                                    >
                                        <Minus size={14} />
                                    </button>
                                    <input 
                                        type="number" 
                                        className="stepper-input"
                                        value={endOccurrences}
                                        readOnly
                                        style={{ 
                                            padding: 0, 
                                            width: '40px', 
                                            fontSize: '14px',
                                            opacity: endCondition === 'after_count' ? 1 : 0.4 
                                        }}
                                        min="1"
                                    />
                                    <button 
                                        type="button"
                                        className="stepper-btn" 
                                        disabled={endCondition !== 'after_count'}
                                        onClick={(e) => { e.stopPropagation(); setEndOccurrences(endOccurrences + 1); }}
                                    >
                                        <Plus size={14} />
                                    </button>
                                </div>
                                <span style={{ fontSize: '13px', color: 'var(--text-dim)', fontWeight: '600' }}>occurrences</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="summary-banner" style={{ 
                    marginTop: '24px', 
                    padding: '12px 16px', 
                    background: 'var(--primary-glow)', 
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                }}>
                    <Clock size={16} color="var(--primary)" />
                    <span style={{ fontSize: '13px', fontWeight: 'bold', color: 'var(--primary)' }}>
                        {generateSummary()}
                    </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px' }}>
                    <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
                    <button type="button" onClick={handleSave} className="btn-primary">Done</button>
                </div>
            </div>
        </div>
    );
}

