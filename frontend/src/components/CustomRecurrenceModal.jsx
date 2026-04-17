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

export default function CustomRecurrenceModal({ isOpen, onClose, onSave, initialData, startingDate }) {
    const [repeatEvery, setRepeatEvery] = React.useState(initialData?.repeatEvery || 1);
    const [repeatUnit, setRepeatUnit] = React.useState(initialData?.repeatUnit || 'week');
    const [repeatDays, setRepeatDays] = React.useState(initialData?.repeatDays || []);
    const [endCondition, setEndCondition] = React.useState(initialData?.endCondition || 'never');
    const [endDate, setEndDate] = React.useState(initialData?.endDate || new Date().toISOString().split('T')[0]);
    const [endOccurrences, setEndOccurrences] = React.useState(initialData?.endOccurrences || 13);
    const [monthlyType, setMonthlyType] = React.useState('day_of_month'); // 'day_of_month' or 'day_of_week'

    const dateAnchor = React.useMemo(() => startingDate ? new Date(startingDate) : new Date(), [startingDate]);
    const dayOfMonth = dateAnchor.getDate();
    const dayName = dateAnchor.toLocaleDateString('en-US', { weekday: 'long' });
    
    // Heuristic for "third Friday" etc
    const weekNum = Math.ceil(dayOfMonth / 7);
    const ordinals = ["", "first", "second", "third", "fourth", "last"];
    const weekOrdName = (weekNum > 4) ? "last" : ordinals[weekNum];

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
        
        if (repeatUnit === 'week' && repeatDays.length > 0) {
            const dayLabels = repeatDays.map(d => DAYS.find(day => day.value === d)?.label).join(', ');
            summary += ` on ${dayLabels}`;
        } else if (repeatUnit === 'month') {
            if (monthlyType === 'day_of_month') {
                summary += ` on day ${dayOfMonth}`;
            } else {
                summary += ` on the ${weekOrdName} ${dayName}`;
            }
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

                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <label style={{ margin: 0, whiteSpace: 'nowrap' }}>Repeat every</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                        <div className="stepper-container" style={{ width: '120px' }}>
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
                        
                        <select 
                            value={repeatUnit} 
                            onChange={(e) => {
                                setRepeatUnit(e.target.value);
                                if (e.target.value === 'month' && repeatEvery > 12) {
                                    setRepeatEvery(12);
                                }
                            }}
                            style={{ flex: 1, minWidth: '100px' }}
                        >
                            {UNITS.map(unit => (
                                <option key={unit} value={unit}>{unit}{repeatEvery > 1 ? 's' : ''}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {repeatUnit === 'week' && (
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

                {repeatUnit === 'month' && (
                    <div className="form-group">
                        <select 
                            value={monthlyType} 
                            onChange={(e) => setMonthlyType(e.target.value)}
                            style={{ width: '100%', marginTop: '4px' }}
                        >
                            <option value="day_of_month">Monthly on day {dayOfMonth}</option>
                            <option value="day_of_week">Monthly on the {weekOrdName} {dayName}</option>
                        </select>
                    </div>
                )}

                <div className="form-group" style={{ marginTop: '24px' }}>
                    <label style={{ marginBottom: '16px' }}>Ends</label>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div 
                            className={`selection-control ${endCondition === 'never' ? 'active' : ''}`}
                            onClick={() => setEndCondition('never')}
                            style={{ padding: '4px 0', background: 'none', border: 'none' }}
                        >
                            <div className="radio-circle" />
                            <span style={{ fontSize: '15px', fontWeight: '500' }}>Never</span>
                        </div>

                        <div 
                            className={`selection-control ${endCondition === 'on_date' ? 'active' : ''}`}
                            onClick={() => setEndCondition('on_date')}
                            style={{ padding: '4px 0', background: 'none', border: 'none' }}
                        >
                            <div className="radio-circle" />
                            <span style={{ fontSize: '15px', fontWeight: '500', width: '60px' }}>On</span>
                            <div style={{ flex: 1 }}>
                                <input 
                                    type="date" 
                                    value={endDate}
                                    onChange={e => setEndDate(e.target.value)}
                                    disabled={endCondition !== 'on_date'}
                                    style={{ 
                                        padding: '8px 12px', 
                                        opacity: endCondition === 'on_date' ? 1 : 0.4,
                                        width: '100%',
                                        pointerEvents: endCondition === 'on_date' ? 'auto' : 'none',
                                        background: 'var(--bg-card)'
                                    }}
                                />
                            </div>
                        </div>

                        <div 
                            className={`selection-control ${endCondition === 'after_count' ? 'active' : ''}`}
                            onClick={() => setEndCondition('after_count')}
                            style={{ padding: '4px 0', background: 'none', border: 'none' }}
                        >
                            <div className="radio-circle" />
                            <span style={{ fontSize: '15px', fontWeight: '500', width: '60px' }}>After</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                                <div className="stepper-container" style={{ width: '100px' }}>
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
                                <span style={{ fontSize: '14px', color: 'var(--text-dim)', fontWeight: '500' }}>occurrences</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="summary-banner" style={{ 
                    marginTop: '32px', 
                    padding: '16px', 
                    background: 'var(--primary-glow)', 
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                }}>
                    <Clock size={18} color="var(--primary)" />
                    <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--primary)' }}>
                        {generateSummary()}
                    </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', marginTop: '40px' }}>
                    <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: '10px 24px' }}>Cancel</button>
                    <button type="button" onClick={handleSave} className="btn-primary" style={{ padding: '10px 24px' }}>Done</button>
                </div>
            </div>
        </div>
    );
}

