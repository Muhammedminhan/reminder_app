import React, { useState, useEffect } from 'react';
import { useQuery, gql, useMutation } from '@apollo/client';
import {
    Bell,
    Calendar,
    CheckCircle,
    Clock,
    LayoutDashboard,
    LogOut,
    Mail,
    Plus,
    Settings,
    Users,
    Trash2,
    RefreshCw,
    Search,
    Moon,
    Sun,
    MessageSquare,
    Briefcase,
    Flag,
    Activity,
    ChevronDown,
    List,
    User,
    Globe,
    MoreVertical,
    Filter,
    ArrowUpRight,
    Shield,
    Database,
    Building,
    Key,
    ChevronLeft
} from 'lucide-react';
import { logout, isAuthenticated } from '../lib/api';
import { format } from 'date-fns';
import CreateReminderModal from '../components/CreateReminderModal';
import UpdateProfileModal from '../components/UpdateProfileModal';
import Toast, { useToast } from '../components/Toast';

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
    }
    users {
      id
      username
      email
      firstName
      lastName
      profilePicture
    }
    dashboardStats {
      pendingCount
      completedCount
      nextSevenDaysCount
      totalActiveCount
      totalUsersCount
    }
    recentActivities {
      id
      title
      time
      description
      action
    }
  }
`;


const UPDATE_REMINDER = gql`
  mutation UpdateReminder($id: ID!, $completed: Boolean) {
    updateReminder(id: $id, completed: $completed) {
      ok
      reminder {
        id
        completed
      }
    }
  }
`;

const DELETE_REMINDER = gql`
  mutation DeleteReminder($id: ID!) {
    deleteReminder(id: $id) {
      ok
    }
  }
`;

const StatCard = ({ icon, label, value, color, trend }) => (
    <div className="stat-card">
        <div className="stat-header">
            <div className="stat-icon" style={{ backgroundColor: color }}>
                {icon}
            </div>
            {trend && (
                <div className="stat-trend success">
                    <ArrowUpRight size={14} />
                    {trend}%
                </div>
            )}
        </div>
        <div className="stat-content">
            <div className="stat-label">{label}</div>
            <div className="stat-value">{value.toLocaleString()}</div>
        </div>
    </div>
);

const SidebarLink = ({ icon: Icon, label, active, onClick, hasSubmenu }) => (
    <button
        onClick={onClick}
        className={`nav-item ${active ? 'active' : ''}`}
    >
        <span className="nav-item-content">
            <Icon size={18} />
            <span className="nav-label">{label}</span>
        </span>
        {hasSubmenu && <ChevronDown size={14} className="submenu-icon" />}
    </button>
);

export default function Dashboard() {
    const [activeView, setActiveView] = useState('dashboard');
    const [settingsTab, setSettingsTab] = useState('Profile');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterStatus, setFilterStatus] = useState('all');
    const [showFilterDropdown, setShowFilterDropdown] = useState(false);
    const [showNotifications, setShowNotifications] = useState(false);
    const [isDarkMode, setIsDarkMode] = useState(true);
    const [securitySettings, setSecuritySettings] = useState({
        twoFactor: true,
        encryption: true,
        accessControl: false
    });
    const { toast, showToast, hideToast } = useToast();

    useEffect(() => {
        if (!isDarkMode) {
            document.body.classList.add('light-mode');
        } else {
            document.body.classList.remove('light-mode');
        }
    }, [isDarkMode]);

    const { loading, error, data, refetch } = useQuery(INITIAL_QUERY, {
        fetchPolicy: 'network-only',
        notifyOnNetworkStatusChange: true,
        pollInterval: 10000, // Poll every 10 seconds for live updates
    });

    const [updateReminder] = useMutation(UPDATE_REMINDER, {
        onCompleted: () => {
            showToast('Notification status updated');
            refetch();
        }
    });

    const [deleteReminder] = useMutation(DELETE_REMINDER, {
        onCompleted: () => {
            showToast('Notification deleted');
            refetch();
        }
    });

    useEffect(() => {
        if (!loading && data && !data.me && isAuthenticated()) {
            logout();
        }
    }, [loading, data]);

    const reminders = data?.reminders || [];
    const teamUsers = data?.users || [];

    // Dynamic Stats from Backend
    const stats = {
        pending: data?.dashboardStats?.pendingCount || 0,
        completed: data?.dashboardStats?.completedCount || 0,
        active: data?.dashboardStats?.totalActiveCount || 0,
        inSeven: data?.dashboardStats?.nextSevenDaysCount || 0,
        totalUsers: data?.dashboardStats?.totalUsersCount || 0
    };

    const toggleComplete = (id, completed) => {
        updateReminder({ variables: { id, completed: !completed } });
    };

    const handleDelete = (id) => {
        if (window.confirm('Are you sure you want to delete this notification?')) {
            deleteReminder({ variables: { id } });
        }
    };

    const filteredReminders = reminders.filter(r => {
        const matchesSearch = r.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
            r.senderEmail.toLowerCase().includes(searchTerm.toLowerCase()) ||
            r.receiverEmail.toLowerCase().includes(searchTerm.toLowerCase());
        
        const matchesStatus = filterStatus === 'all' || 
            (filterStatus === 'active' && !r.completed) || 
            (filterStatus === 'completed' && r.completed);
            
        return matchesSearch && matchesStatus;
    });

    const toggleSecuritySetting = (key) => {
        setSecuritySettings(prev => {
            const newValue = !prev[key];
            showToast(`${key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())} ${newValue ? 'enabled' : 'disabled'}`);
            return { ...prev, [key]: newValue };
        });
    };

    const [notifications, setNotifications] = useState([]);

    useEffect(() => {
        if (data?.recentActivities) {
            const colorMap = {
                'Created': '#6366f1',
                'Updated': '#10b981',
                'Deleted': '#ef4444'
            };
            
            const realNotifications = data.recentActivities.map(act => ({
                id: act.id,
                title: act.title,
                desc: act.description,
                time: act.time,
                color: colorMap[act.action] || '#3b82f6'
            }));
            
            setNotifications(realNotifications);
        }
    }, [data?.recentActivities]);

    const clearNotifications = () => {
        setNotifications([]);
        showToast('All notifications cleared');
    };

    if (loading && !data) return (
        <div className="loading-screen">
            <div className="loading-logo-wrapper">
                <div className="sidebar-logo-icon animate-pulse">
                    <Bell size={32} fill="white" strokeWidth={1} />
                </div>
            </div>
            <p className="loading-text">Synchronizing Premium Workspace...</p>
        </div>
    );

    return (
        <div className="dashboard-container">
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <div className="sidebar-logo-icon">
                        <Bell size={20} fill="white" strokeWidth={1} />
                    </div>
                    <span className="login-brand-name">Notify<span className="text-gradient">Hub</span></span>
                </div>

                <div className="sidebar-section">
                    <div className="sidebar-section-label">Menu</div>
                    <SidebarLink icon={LayoutDashboard} label="Dashboard" active={activeView === 'dashboard'} onClick={() => setActiveView('dashboard')} />
                    <SidebarLink icon={List} label="Notifications" active={activeView === 'notifications'} onClick={() => setActiveView('notifications')} />
                    <SidebarLink icon={Clock} label="Pending Tasks" active={activeView === 'pending'} onClick={() => setActiveView('pending')} />
                </div>

                <div className="sidebar-section">
                    <div className="sidebar-section-label">System</div>
                    <SidebarLink icon={Settings} label="Settings" active={activeView === 'settings'} onClick={() => setActiveView('settings')} hasSubmenu />
                </div>

                <div className="sidebar-user-card" onClick={() => setActiveView('settings')}>
                    <div className="user-avatar">
                        {data?.me?.profilePicture ? (
                            <img src={data.me.profilePicture} alt="User" />
                        ) : (
                            <User size={20} color="white" />
                        )}
                    </div>
                    <div className="user-info">
                        <div className="user-name">{data?.me?.username || 'Admin'}</div>
                        <div className="user-role">{data?.me?.company?.name || 'Workspace'}</div>
                    </div>
                    <button className="logout-btn" onClick={logout} title="Logout">
                        <LogOut size={16} />
                    </button>
                </div>
            </aside>

            <main className="main-content">
                <header className="main-header">
                    <div className="header-content-left">
                        {activeView !== 'dashboard' && (
                            <button
                                className="back-button animate-fade"
                                onClick={() => setActiveView('dashboard')}
                                title="Go Back to Dashboard"
                            >
                                <ChevronLeft size={20} />
                            </button>
                        )}
                        <div className="search-wrapper">
                            <Search size={18} className="search-icon" />
                            <input
                                type="text"
                                placeholder="Search everything..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="header-actions">
                        <div className="theme-toggle">
                            <button onClick={() => setIsDarkMode(false)} className={!isDarkMode ? 'active' : ''}><Sun size={18} /></button>
                            <button onClick={() => setIsDarkMode(true)} className={isDarkMode ? 'active' : ''}><Moon size={18} /></button>
                        </div>

                        <div className="notification-bell">
                            <button onClick={() => setShowNotifications(!showNotifications)}>
                                <Bell size={20} />
                                {notifications.length > 0 && <span className="notification-dot" />}
                            </button>
                            {showNotifications && (
                                <div className="notification-dropdown glass-card animate-fade">
                                    <div className="dropdown-header">
                                        <h3>Recent Activity</h3>
                                        {notifications.length > 0 && (
                                            <button className="clear-link" onClick={clearNotifications}>Clear all</button>
                                        )}
                                    </div>
                                    <div className="notification-list">
                                        {notifications.length > 0 ? (
                                            notifications.map(n => (
                                                <div key={n.id} className="notification-item">
                                                    <div className="item-icon" style={{ background: n.color }}>
                                                        <Mail size={16} color="white" />
                                                    </div>
                                                    <div className="item-content">
                                                        <div className="item-title">{n.title}</div>
                                                        <div className="item-time">{n.time}</div>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="notification-empty">
                                                <Bell size={32} />
                                                <p>All activities caught up!</p>
                                            </div>
                                        )}
                                    </div>
                                    <button className="view-all-btn" onClick={() => {
                                        setShowNotifications(false);
                                        setActiveView('notifications');
                                        setNotifications([]); // Clear when viewing all as requested
                                    }}>
                                        View all
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </header>

                <div className="content-body animate-fade">
                    {activeView === 'dashboard' && (
                        <>
                            <div className="welcome-banner">
                                <div className="welcome-text">
                                    <h1>Welcome back, <span className="text-gradient">{data?.me?.firstName || data?.me?.username}!</span></h1>
                                    <p>Your workspace is synced and operational. Here's your summary.</p>
                                </div>
                                <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
                                    <Plus size={20} /> New Trigger
                                </button>
                            </div>

                            <div className="stats-grid">
                                <StatCard icon={<Mail size={20} color="var(--primary)" />} label="Pending" value={stats.pending} color="var(--primary-glow)" trend="12" />
                                <StatCard icon={<CheckCircle size={20} color="var(--success)" />} label="Completed" value={stats.completed} color="rgba(52, 211, 153, 0.1)" trend="5" />
                                <StatCard icon={<Clock size={20} color="var(--warning)" />} label="Next 7 Days" value={stats.inSeven} color="rgba(251, 191, 36, 0.1)" />
                                <StatCard icon={<Activity size={20} color="var(--info)" />} label="Total Active" value={stats.active} color="rgba(96, 165, 250, 0.1)" trend="18" />
                            </div>

                            <div className="glass-card table-section card-glow">
                                <div className="section-header">
                                    <h2>Active Triggers</h2>
                                    <button className="btn-secondary" onClick={() => setActiveView('notifications')}>Detailed View</button>
                                </div>

                                <div className="table-wrapper">
                                    <table className="premium-table">
                                        <thead>
                                            <tr>
                                                <th>Label</th>
                                                <th>Recipient</th>
                                                <th>Slack</th>
                                                <th>Status</th>
                                                <th>Cadence</th>
                                                <th style={{ textAlign: 'right' }}>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {reminders.slice(0, 8).map(reminder => (
                                                <tr key={reminder.id}>
                                                    <td>
                                                        <div className="reminder-title-cell">
                                                            <div className={`status-dot ${reminder.completed ? 'completed' : 'active'}`} />
                                                            <div className="title-text">
                                                                <span className="main-title">{reminder.title}</span>
                                                                <span className="sub-title">{reminder.reminderStartDate ? format(new Date(reminder.reminderStartDate), 'MMM dd') : 'No date'}</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td><span className="email-cell">{reminder.receiverEmail}</span></td>
                                                    <td>
                                                        {(reminder.slackChannels || reminder.slackUserId) ? (
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                                <MessageSquare size={14} color="#E01E5A" />
                                                                <span className="text-dim" style={{ fontSize: '0.85rem' }}>
                                                                    {reminder.slackChannels || reminder.slackUserId}
                                                                </span>
                                                            </div>
                                                        ) : (
                                                            <span className="text-dim">-</span>
                                                        )}
                                                    </td>
                                                    <td>
                                                        <span className={`badge ${reminder.completed ? 'badge-completed' : 'badge-active'}`}>
                                                            {reminder.completed ? 'Done' : 'Active'}
                                                        </span>
                                                    </td>
                                                    <td className="cadence-cell">
                                                        <Clock size={14} /> {reminder.intervalType}
                                                    </td>
                                                    <td style={{ textAlign: 'right' }}>
                                                        <div className="action-btns">
                                                            <button onClick={() => toggleComplete(reminder.id, reminder.completed)} title="Toggle status">
                                                                <CheckCircle size={18} className={reminder.completed ? 'text-success' : ''} />
                                                            </button>
                                                            <button onClick={() => handleDelete(reminder.id)} title="Delete">
                                                                <Trash2 size={18} />
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                            {reminders.length === 0 && (
                                                <tr key="empty">
                                                     <td colSpan="6" className="empty-state">
                                                         <Bell size={48} />
                                                         <p>No triggers found. Start by creating one!</p>
                                                     </td>
                                                 </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </>
                    )}

                    {(activeView === 'notifications' || activeView === 'pending') && (
                        <div className="glass-card full-view">
                            <div className="section-header">
                                <h2>{activeView === 'notifications' ? 'All Triggers' : 'Pending Operations'}</h2>
                                <div className="filter-group">
                                    <div className="filter-dropdown-container">
                                        <button 
                                            className={`btn-secondary small ${filterStatus !== 'all' ? 'active-filter' : ''}`}
                                            onClick={() => setShowFilterDropdown(!showFilterDropdown)}
                                        >
                                            <Filter size={14} /> 
                                            {filterStatus === 'all' ? 'Filters' : `Filter: ${filterStatus.charAt(0).toUpperCase() + filterStatus.slice(1)}`}
                                        </button>
                                        
                                        {showFilterDropdown && (
                                            <div className="filter-dropdown glass-card animate-fade">
                                                <button 
                                                    className={filterStatus === 'all' ? 'active' : ''} 
                                                    onClick={() => { setFilterStatus('all'); setShowFilterDropdown(false); }}
                                                >
                                                    All Triggers
                                                </button>
                                                <button 
                                                    className={filterStatus === 'active' ? 'active' : ''} 
                                                    onClick={() => { setFilterStatus('active'); setShowFilterDropdown(false); }}
                                                >
                                                    Active Only
                                                </button>
                                                <button 
                                                    className={filterStatus === 'completed' ? 'active' : ''} 
                                                    onClick={() => { setFilterStatus('completed'); setShowFilterDropdown(false); }}
                                                >
                                                    Finalized Only
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="table-wrapper">
                                <table className="premium-table">
                                    <thead>
                                        <tr>
                                            <th>Label</th>
                                            <th>From</th>
                                            <th>To</th>
                                            <th>Slack</th>
                                            <th>Timeline</th>
                                            <th>State</th>
                                            <th style={{ textAlign: 'right' }}>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(activeView === 'pending' ? filteredReminders.filter(r => !r.completed) : filteredReminders).map(reminder => (
                                            <tr key={reminder.id}>
                                                <td className="bold">{reminder.title}</td>
                                                <td>{reminder.senderEmail}</td>
                                                <td>{reminder.receiverEmail}</td>
                                                <td>
                                                    {(reminder.slackChannels || reminder.slackUserId) ? (
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                            <MessageSquare size={14} color="#E01E5A" />
                                                            <span className="text-dim" style={{ fontSize: '0.85rem' }}>
                                                                {reminder.slackChannels || reminder.slackUserId}
                                                            </span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-dim">-</span>
                                                    )}
                                                </td>
                                                <td className="text-dim">{reminder.reminderStartDate ? format(new Date(reminder.reminderStartDate), 'MMM dd, yyyy') : '-'}</td>
                                                <td>
                                                    <span className={`badge ${reminder.completed ? 'badge-completed' : 'badge-active'}`}>
                                                        {reminder.completed ? 'Finalized' : 'In Queue'}
                                                    </span>
                                                </td>
                                                <td style={{ textAlign: 'right' }}>
                                                    <div className="action-btns">
                                                        <button onClick={() => toggleComplete(reminder.id, reminder.completed)}><CheckCircle size={18} /></button>
                                                        <button onClick={() => handleDelete(reminder.id)}><Trash2 size={18} /></button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {activeView === 'settings' && (
                        <div className="settings-view">
                            <div className="settings-header">
                                <h1>Settings</h1>
                                <button className="btn-primary" onClick={() => setIsProfileModalOpen(true)}>
                                    <Settings size={18} /> Edit Profile
                                </button>
                            </div>

                            <div className="settings-nav">
                                {['Profile', 'Team', 'Security', 'Integration'].map(tab => (
                                    <button key={tab} className={settingsTab === tab ? 'active' : ''} onClick={() => setSettingsTab(tab)}>{tab}</button>
                                ))}
                            </div>

                            <div className="settings-content animate-fade">
                                {settingsTab === 'Profile' && (
                                    <div className="profile-settings-grid">
                                        <div className="glass-card profile-details">
                                            <div className="card-header">
                                                <User className="header-icon" />
                                                <h3>Account Details</h3>
                                            </div>
                                            <div className="detail-grid">
                                                <div className="detail-item-new">
                                                    <User className="item-icon" size={16} />
                                                    <div className="item-info">
                                                        <span className="item-label">Username</span>
                                                        <span className="item-value">{data?.me?.username}</span>
                                                    </div>
                                                </div>
                                                <div className="detail-item-new">
                                                    <Mail className="item-icon" size={16} />
                                                    <div className="item-info">
                                                        <span className="item-label">Email Address</span>
                                                        <span className="item-value">{data?.me?.email}</span>
                                                    </div>
                                                </div>
                                                <div className="detail-item-new">
                                                    <Building className="item-icon" size={16} />
                                                    <div className="item-info">
                                                        <span className="item-label">Company</span>
                                                        <span className="item-value">{data?.me?.company?.name || 'NotifyHub'}</span>
                                                    </div>
                                                </div>
                                                <div className="detail-item-new">
                                                    <Shield className="item-icon" size={16} />
                                                    <div className="item-info">
                                                        <span className="item-label">Access Level</span>
                                                        <span className="item-value">Administrator</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="glass-card profile-activity">
                                            <div className="card-header">
                                                <Activity className="header-icon" />
                                                <h3>System Activity</h3>
                                            </div>
                                            <div className="progress-list">
                                                <div className="progress-item">
                                                    <div className="progress-label">
                                                        <div className="label-with-icon"><Activity size={14} /> <span>Success Rate</span></div>
                                                        <span>99.9%</span>
                                                    </div>
                                                    <div className="progress-bar"><div className="bar" style={{ width: '99.9%', background: 'var(--success)' }} /></div>
                                                </div>
                                                <div className="progress-item">
                                                    <div className="progress-label">
                                                        <div className="label-with-icon"><Clock size={14} /> <span>Avg. Processing Time</span></div>
                                                        <span>42ms</span>
                                                    </div>
                                                    <div className="progress-bar"><div className="bar" style={{ width: '85%', background: 'var(--primary)' }} /></div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {settingsTab === 'Team' && (
                                    <div className="glass-card team-section">
                                        <h3>Team Cluster</h3>
                                        <div className="team-grid">
                                            {teamUsers.map(user => (
                                                <div key={user.id} className="team-member-card">
                                                    <div className="member-avatar"><User size={20} /></div>
                                                    <div className="member-info">
                                                        <div className="member-name">{user.firstName} {user.lastName}</div>
                                                        <div className="member-email">{user.email}</div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {settingsTab === 'Security' && (
                                    <div className="glass-card security-section">
                                        <h3>Security Control</h3>
                                        <div className="security-controls">
                                            {[
                                                { id: 'twoFactor', title: '2FA Auth', icon: Key },
                                                { id: 'encryption', title: 'Encryption', icon: Shield },
                                                { id: 'accessControl', title: 'Restricted Access', icon: Building }
                                            ].map(s => (
                                                <div key={s.id} className="control-row">
                                                    <div className="control-info"><s.icon size={18} /> <span>{s.title}</span></div>
                                                    <button className={`toggle ${securitySettings[s.id] ? 'active' : ''}`} onClick={() => toggleSecuritySetting(s.id)}>
                                                        <div className="thumb" />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <CreateReminderModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSuccess={() => { showToast('Trigger created'); refetch(); }} />
                <UpdateProfileModal isOpen={isProfileModalOpen} onClose={() => setIsProfileModalOpen(false)} user={data?.me} onSuccess={(msg) => { showToast(msg); refetch(); }} />
                <Toast {...toast} onHide={hideToast} />
            </main>
        </div>
    );
}
