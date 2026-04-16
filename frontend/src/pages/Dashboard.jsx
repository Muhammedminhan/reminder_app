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
    Eye,
    Check,
    CornerDownRight,
    MessageCircle,
    Database,
    Building,
    Key,
    ChevronLeft,
    Paperclip,
    X
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
      visibleToDepartment
      visibleToGroups {
        id
        name
      }
      attachments {
        id
        filename
        url
      }
      isApproved
      approvedAt
      approvedBy {
        id
        username
      }
      createdBy {
        id
        username
        manager {
          id
        }
      }
      comments {
        id
        text
        createdAt
        user {
          id
          username
          profilePicture
        }
        replies {
          id
          text
          createdAt
          user {
            id
            username
            profilePicture
          }
        }
      }
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
    groups {
      id
      name
      members {
        id
        username
      }
    }
    jiraIntegration {
      baseUrl
      email
      projectKey
      isActive
    }
    reminderDeliveries {
      id
      sentAt
      status
      reminder {
        title
      }
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
        isApproved
      }
    }
  }
`;

const APPROVE_REMINDER = gql`
  mutation ApproveReminder($id: ID!) {
    approveReminder(id: $id) {
      ok
      reminder {
        id
        completed
        isApproved
        approvedAt
        approvedBy {
          id
          username
        }
      }
    }
  }
`;

const CREATE_COMMENT = gql`
  mutation CreateComment($reminderId: ID!, $text: String!, $parentId: ID) {
    createComment(reminderId: $reminderId, text: $text, parentId: $parentId) {
      ok
      comment {
        id
        text
        createdAt
        user {
          id
          username
          profilePicture
        }
        parent {
          id
        }
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

const CREATE_GROUP = gql`
  mutation CreateGroup($name: String!, $memberIds: [ID]) {
    createGroup(name: $name, memberIds: $memberIds) {
      ok
      group {
        id
        name
        members {
          id
          username
        }
      }
    }
  }
`;

const UPDATE_GROUP = gql`
  mutation UpdateGroup($id: ID!, $name: String, $memberIds: [ID]) {
    updateGroup(id: $id, name: $name, memberIds: $memberIds) {
      ok
      group {
        id
        name
        members {
          id
          username
        }
      }
    }
  }
`;

const DELETE_GROUP = gql`
  mutation DeleteGroup($id: ID!) {
    deleteGroup(id: $id) {
      ok
    }
  }
`;

const UPDATE_JIRA = gql`
  mutation UpdateJiraIntegration($baseUrl: String!, $email: String!, $apiToken: String!, $projectKey: String!, $isActive: Boolean) {
    updateJiraIntegration(baseUrl: $baseUrl, email: $email, apiToken: $apiToken, projectKey: $projectKey, isActive: $isActive) {
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
    const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
    const [selectedReminder, setSelectedReminder] = useState(null);
    const [commentText, setCommentText] = useState('');
    const [replyToId, setReplyToId] = useState(null);
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

    const [groupName, setGroupName] = useState('');
    const [selectedMembers, setSelectedMembers] = useState([]);
    const [isGroupModalOpen, setIsGroupModalOpen] = useState(false);
    const [editingGroup, setEditingGroup] = useState(null);

    const [jiraConfig, setJiraConfig] = useState({
        baseUrl: '',
        email: '',
        apiToken: '',
        projectKey: '',
        isActive: true
    });

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

    useEffect(() => {
        if (error) {
            showToast('Sync Error: ' + error.message);
        }
    }, [error]);

    const [updateReminder] = useMutation(UPDATE_REMINDER, {
        refetchQueries: [{ query: INITIAL_QUERY }]
    });

    const [approveReminder] = useMutation(APPROVE_REMINDER, {
        onCompleted: () => {
            showToast('Reminder approved and completed');
            if (selectedReminder) {
                const updated = reminders.find(r => r.id === selectedReminder.id);
                setSelectedReminder(updated);
            }
        },
        refetchQueries: [{ query: INITIAL_QUERY }]
    });

    const [addComment] = useMutation(CREATE_COMMENT, {
        onCompleted: () => {
            setCommentText('');
            setReplyToId(null);
            showToast('Comment added');
        },
        refetchQueries: [{ query: INITIAL_QUERY }]
    });

    const [deleteReminder] = useMutation(DELETE_REMINDER, {
        onCompleted: () => {
            showToast('Notification deleted');
            refetch();
        }
    });

    const [createGroup, { loading: creatingGroup }] = useMutation(CREATE_GROUP, {
        refetchQueries: [{ query: INITIAL_QUERY }],
        onCompleted: (data) => {
            if (data?.createGroup?.ok) {
                showToast('Group created successfully');
                setIsGroupModalOpen(false);
                setGroupName('');
                setSelectedMembers([]);
            } else {
                showToast('Failed to create group');
            }
        },
        onError: (err) => showToast('Error: ' + err.message)
    });

    const [updateGroup, { loading: updatingGroup }] = useMutation(UPDATE_GROUP, {
        refetchQueries: [{ query: INITIAL_QUERY }],
        onCompleted: (data) => {
            if (data?.updateGroup?.ok) {
                showToast('Group updated successfully');
                setIsGroupModalOpen(false);
                setEditingGroup(null);
                setGroupName('');
                setSelectedMembers([]);
            } else {
                showToast('Failed to update group');
            }
        },
        onError: (err) => showToast('Error: ' + err.message)
    });

    const [deleteGroup] = useMutation(DELETE_GROUP, {
        onCompleted: () => {
            showToast('Group deleted');
            refetch();
        }
    });

    const [updateJira] = useMutation(UPDATE_JIRA, {
        onCompleted: () => {
            showToast('Jira configuration updated');
            refetch();
        }
    });

    useEffect(() => {
        if (data?.jiraIntegration) {
            setJiraConfig({
                ...data.jiraIntegration,
                apiToken: '' // Don't prefill token for security
            });
        }
    }, [data?.jiraIntegration]);

    // REST Fallback for Identity (Ensures "Guest" never shows if authenticated)
    const [restUser, setRestUser] = useState(null);
    const fetchProfile = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        try {
            const response = await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/user/profile/`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            if (data.ok) setRestUser(data.user);
        } catch (err) {
            console.error("Failed to fetch REST profile:", err);
        }
    };

    useEffect(() => {
        fetchProfile();
    }, []);

    useEffect(() => {
        if (!loading && !error && data) {
            // Enhanced session validation
            if (data.me === null && !restUser && isAuthenticated()) {
                console.warn('User session invalidated on server. Logging out.');
                logout();
            }
        }
    }, [loading, error, data, restUser]);

    useEffect(() => {
        if (error) {
            console.error('Data fetch error:', error);
            // Optional: Handle specific auth errors here
            if (error.networkError?.statusCode === 401) {
                logout();
            }
        }
    }, [loading, data, error]);

    const reminders = data?.reminders || [];
    const teamUsers = data?.users || [];
    const groups = data?.groups || [];
    const me = data?.me;

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
                        {(data?.me?.profilePicture || restUser?.avatar) ? (
                            <img src={`${(data?.me?.profilePicture || restUser?.avatar).startsWith('http') ? '' : (import.meta.env.VITE_API_BASE || 'http://localhost:8000')}${data?.me?.profilePicture || restUser?.avatar}${(data?.me?.profilePicture || restUser?.avatar).includes('?') ? '&' : '?'}t=${Date.now()}`} alt="User" />
                        ) : (
                            <User size={20} color="white" />
                        )}
                    </div>
                    <div className="user-info">
                        <div className="user-name">{(data?.me?.firstName || data?.me?.first_name || restUser?.first_name) ? `${data?.me?.firstName || data?.me?.first_name || restUser?.first_name} ${data?.me?.lastName || data?.me?.last_name || restUser?.last_name || ''}` : (data?.me?.username || restUser?.username || 'Admin')}</div>
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
                                    <h1>Welcome back, <span className="text-gradient">{(data?.me?.firstName || data?.me?.first_name || restUser?.first_name || data?.me?.username || restUser?.username) || 'Admin'}</span>! <small style={{fontSize: '11px', opacity: 0.5}}>({data?.me?.email || restUser?.email || 'Logged In'})</small> ✨</h1>
                                    <p>Workspace synchronized. Review your active triggers below.</p>
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
                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                                    <span className="sub-title">{reminder.reminderStartDate ? format(new Date(reminder.reminderStartDate), 'MMM dd') : 'No date'}</span>
                                                                    {reminder.attachments?.length > 0 && (
                                                                        <div title={`${reminder.attachments.length} attachments`} style={{ display: 'flex', gap: '4px' }}>
                                                                            {reminder.attachments.map(att => (
                                                                                <a 
                                                                                    key={att.id} 
                                                                                    href={`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}${att.url}`}
                                                                                    target="_blank"
                                                                                    rel="noopener noreferrer"
                                                                                    style={{ color: 'var(--primary-glow)', display: 'flex' }}
                                                                                >
                                                                                    <Paperclip size={12} />
                                                                                </a>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
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
                                                        <button 
                                                            className="btn-icon" 
                                                            title="View Details"
                                                            onClick={() => { setSelectedReminder(reminder); setIsDetailsModalOpen(true); }}
                                                        >
                                                            <Eye size={18} />
                                                        </button>
                                                        
                                                        {reminder.createdBy?.manager?.id === data?.me?.id && !reminder.isApproved && (
                                                            <button 
                                                                className="btn-icon approve-btn" 
                                                                title="Approve"
                                                                onClick={() => approveReminder({ variables: { id: reminder.id }})}
                                                            >
                                                                <Check size={18} color="var(--success)" />
                                                            </button>
                                                        )}
                                                        
                                                        <button 
                                                            title={reminder.completed ? "Mark Incomplete" : "Finalize"}
                                                            onClick={() => toggleComplete(reminder.id, reminder.completed)}
                                                        >
                                                            <CheckCircle size={18} color={reminder.completed ? "var(--success)" : "currentColor"} />
                                                        </button>
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
                                                        <span className="item-value">{data?.me?.username || restUser?.username}</span>
                                                    </div>
                                                </div>
                                                <div className="detail-item-new">
                                                    <Mail className="item-icon" size={16} />
                                                    <div className="item-info">
                                                        <span className="item-label">Email Address</span>
                                                        <span className="item-value">{data?.me?.email || restUser?.email}</span>
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
                                )}                                {settingsTab === 'Team' && (
                                    <div className="team-settings-container">
                                        <div className="settings-section-clean section-glow">
                                            <div className="section-header-clean">
                                                <div className="header-text-group">
                                                    <h3>User Directory</h3>
                                                    <p className="text-dim xsmall">Manage and view all workspace members.</p>
                                                </div>
                                                <button className="btn-tertiary small" onClick={() => setActiveView('notifications')}>
                                                    <Settings size={14} /> <span>Manage</span>
                                                </button>
                                            </div>
                                            
                                            <div className="team-grid-clean">
                                                {teamUsers.map(user => (
                                                    <div key={user.id} className="member-card-clean glass-card">
                                                        <div className="member-avatar-clean">
                                                            {user.profilePicture ? (
                                                                <img src={`${user.profilePicture.startsWith('http') ? user.profilePicture : `${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}${user.profilePicture}`}${user.profilePicture.includes('?') ? '&' : '?'}token=${localStorage.getItem('access_token')}`} alt="" />
                                                            ) : (
                                                                <div className="avatar-initials">{user.firstName?.charAt(0) || user.username?.charAt(0)}</div>
                                                            )}
                                                            <div className="status-dot-mini online" />
                                                        </div>
                                                        <div className="member-details-clean">
                                                            <h4>{user.firstName} {user.lastName || user.username}</h4>
                                                            <span className="member-email-clean">{user.email}</span>
                                                            <div className="tag-row">
                                                                {user.departments?.map(d => (
                                                                    <span key={d.id} className="mini-tag">{d.name}</span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                        <button className="action-dots"><MoreVertical size={14} /></button>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="settings-section-clean section-glow mt-8">
                                            <div className="section-header-clean">
                                                <div className="header-text-group">
                                                    <h3>Collaboration Groups</h3>
                                                    <p className="text-dim xsmall">Organize users into functional teams.</p>
                                                </div>
                                                <button className="btn-primary small" onClick={() => {
                                                    setEditingGroup(null);
                                                    setGroupName('');
                                                    setSelectedMembers([]);
                                                    setIsGroupModalOpen(true);
                                                }}>
                                                    <Plus size={16} /> <span>New Group</span>
                                                </button>
                                            </div>

                                            <div className="groups-container-clean">
                                                {groups.length > 0 ? (
                                                    <div className="groups-grid-clean">
                                                        {groups.map(group => (
                                                            <div key={group.id} className="group-card-clean glass-card">
                                                                <div className="group-header-clean">
                                                                    <div className="group-icon-clean">
                                                                        {group.name?.substring(0, 1).toUpperCase() || 'G'}
                                                                    </div>
                                                                    <div className="group-info-clean">
                                                                        <h4>{group.name}</h4>
                                                                        <span className="text-dim xxsmall">{group.members?.length || 0} Members</span>
                                                                    </div>
                                                                </div>
                                                                <div className="group-actions-clean">
                                                                    <button onClick={() => {
                                                                        setEditingGroup(group);
                                                                        setGroupName(group.name);
                                                                        setSelectedMembers(group.members.map(m => m.id));
                                                                        setIsGroupModalOpen(true);
                                                                    }}><Settings size={14} /></button>
                                                                    <button className="danger" onClick={() => {
                                                                        if(window.confirm('Delete group?')) deleteGroup({ variables: { id: group.id } });
                                                                    }}><Trash2 size={14} /></button>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="empty-state-clean">
                                                        <div className="empty-visual">
                                                            <Users size={24} />
                                                        </div>
                                                        <p>No collaboration groups yet.</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {settingsTab === 'Integration' && (
                                    <div className="glass-card integration-section animate-fade">
                                        <div className="section-header">
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                <Database className="header-icon" />
                                                <div>
                                                    <h3>Jira Enterprise Sync</h3>
                                                    <p className="text-dim">Connect your reminders with Atlassian Jira projects.</p>
                                                </div>
                                            </div>
                                            <div className={`status-badge ${jiraConfig.isActive ? 'active' : 'inactive'}`}>
                                                {jiraConfig.isActive ? 'Connected' : 'Disconnected'}
                                            </div>
                                        </div>

                                        <form className="jira-config-form" onSubmit={(e) => {
                                            e.preventDefault();
                                            updateJira({ variables: jiraConfig });
                                        }}>
                                            <div className="form-group">
                                                <label>Atlassian Base URL</label>
                                                <input 
                                                    type="url" 
                                                    placeholder="https://company.atlassian.net"
                                                    value={jiraConfig.baseUrl}
                                                    onChange={e => setJiraConfig({...jiraConfig, baseUrl: e.target.value})}
                                                    required
                                                />
                                            </div>
                                            <div className="form-row">
                                                <div className="form-group">
                                                    <label>Account Email</label>
                                                    <input 
                                                        type="email" 
                                                        placeholder="admin@company.com"
                                                        value={jiraConfig.email}
                                                        onChange={e => setJiraConfig({...jiraConfig, email: e.target.value})}
                                                        required
                                                    />
                                                </div>
                                                <div className="form-group">
                                                    <label>Default Project Key</label>
                                                    <input 
                                                        type="text" 
                                                        placeholder="PROJ"
                                                        value={jiraConfig.projectKey}
                                                        onChange={e => setJiraConfig({...jiraConfig, projectKey: e.target.value})}
                                                        required
                                                    />
                                                </div>
                                            </div>
                                            <div className="form-group">
                                                <label>API Token / Secret Key</label>
                                                <input 
                                                    type="password" 
                                                    placeholder="••••••••••••••••"
                                                    value={jiraConfig.apiToken}
                                                    onChange={e => setJiraConfig({...jiraConfig, apiToken: e.target.value})}
                                                    required={!data?.jiraIntegration}
                                                />
                                                <small className="help-text">Your API token is encrypted at rest and never displayed after saving.</small>
                                            </div>
                                            <div className="form-group checkbox-group">
                                                <label className="toggle-label">
                                                    <input 
                                                        type="checkbox" 
                                                        checked={jiraConfig.isActive}
                                                        onChange={e => setJiraConfig({...jiraConfig, isActive: e.target.checked})}
                                                    />
                                                    <span>Enable dynamic syncing</span>
                                                </label>
                                            </div>
                                            <div className="form-actions">
                                                <button type="submit" className="btn-primary">Save Integration</button>
                                            </div>
                                        </form>
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
            </main>

            <CreateReminderModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSuccess={() => { showToast('Trigger created'); refetch(); }} />
            <UpdateProfileModal isOpen={isProfileModalOpen} onClose={() => setIsProfileModalOpen(false)} user={data?.me || restUser} onSuccess={(msg) => { showToast(msg); refetch(); fetchProfile(); }} />
            
            {isGroupModalOpen && (
                <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsGroupModalOpen(false)}>
                    <div className="modal-container animate-fade">
                        <button onClick={() => setIsGroupModalOpen(false)} className="modal-close"><X size={20} /></button>
                        <div className="modal-header">
                            <h2>{editingGroup ? 'Edit Group' : 'Create New Group'}</h2>
                            <p>Manage collaboration units within your company.</p>
                        </div>
                        <div className="form-group">
                            <label>Group Name</label>
                            <input 
                                type="text" 
                                value={groupName} 
                                onChange={e => setGroupName(e.target.value)}
                                placeholder="Sales Team / Engineers / etc."
                            />
                        </div>
                        <div className="form-group">
                            <label>Select Members</label>
                            <div className="members-select-grid">
                                {teamUsers.map(u => (
                                    <label key={u.id} className="member-select-item">
                                        <input 
                                            type="checkbox" 
                                            checked={selectedMembers.includes(u.id)}
                                            onChange={e => {
                                                if(e.target.checked) setSelectedMembers([...selectedMembers, u.id]);
                                                else setSelectedMembers(selectedMembers.filter(id => id !== u.id));
                                            }}
                                        />
                                        <span>{u.firstName || u.username}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setIsGroupModalOpen(false)}>Cancel</button>
                            <button 
                                className="btn-primary" 
                                disabled={creatingGroup || updatingGroup}
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    if(editingGroup) updateGroup({ variables: { id: editingGroup.id, name: groupName, memberIds: selectedMembers }});
                                    else createGroup({ variables: { name: groupName, memberIds: selectedMembers }});
                                }}
                            >
                                {creatingGroup ? 'Creating...' : updatingGroup ? 'Updating...' : (editingGroup ? 'Update Group' : 'Create Group')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
            
            <Toast {...toast} onHide={hideToast} />

            {isDetailsModalOpen && selectedReminder && (
                <div className="modal-overlay" onClick={() => setIsDetailsModalOpen(false)}>
                    <div className="modal-content glass-card wide-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <div className={`status-dot ${selectedReminder.completed ? 'completed' : 'active'}`} />
                                <div>
                                    <h2>{selectedReminder.title}</h2>
                                    <p className="text-dim">ID: {selectedReminder.uniqueId}</p>
                                </div>
                            </div>
                            <button className="close-btn" onClick={() => setIsDetailsModalOpen(false)}>&times;</button>
                        </div>

                        <div className="details-grid">
                            <div className="details-main">
                                <div className="detail-section">
                                    <label>Description</label>
                                    <div className="description-text">
                                        {selectedReminder.description || "No description provided."}
                                    </div>
                                </div>

                                <div className="detail-section">
                                    <label>Comments & Discussion</label>
                                    <div className="comments-container">
                                        {selectedReminder.comments?.map(comment => (
                                            <div key={comment.id} className="comment-thread">
                                                <div className="comment-item">
                                                    <div className="comment-avatar">
                                                        {comment.user.username.charAt(0).toUpperCase()}
                                                    </div>
                                                    <div className="comment-content">
                                                        <div className="comment-meta">
                                                            <span className="comment-user">{comment.user.username}</span>
                                                            <span className="comment-date">{new Date(comment.createdAt).toLocaleString()}</span>
                                                        </div>
                                                        <div className="comment-text">{comment.text}</div>
                                                        <button 
                                                            className="reply-btn"
                                                            onClick={() => {
                                                                setReplyToId(comment.id);
                                                                setCommentText(`@${comment.user.username} `);
                                                            }}
                                                        >
                                                            Reply
                                                        </button>
                                                    </div>
                                                </div>
                                                
                                                {comment.replies?.map(reply => (
                                                    <div key={reply.id} className="comment-item reply">
                                                        <CornerDownRight size={14} className="reply-arrow" />
                                                        <div className="comment-avatar small">
                                                            {reply.user.username.charAt(0).toUpperCase()}
                                                        </div>
                                                        <div className="comment-content">
                                                            <div className="comment-meta">
                                                                <span className="comment-user">{reply.user.username}</span>
                                                                <span className="comment-date">{new Date(reply.createdAt).toLocaleString()}</span>
                                                            </div>
                                                            <div className="comment-text">{reply.text}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ))}
                                        
                                        {selectedReminder.comments?.length === 0 && (
                                            <div className="empty-comments">No comments yet. Start the discussion!</div>
                                        )}
                                    </div>

                                    <div className="comment-input-area">
                                        {replyToId && (
                                            <div className="replying-notice">
                                                Replying to comment... <button onClick={() => setReplyToId(null)}>Cancel</button>
                                            </div>
                                        )}
                                        <textarea 
                                            placeholder={replyToId ? "Write a reply..." : "Add a comment..."}
                                            value={commentText}
                                            onChange={e => setCommentText(e.target.value)}
                                        />
                                        <button 
                                            className="btn-primary" 
                                            disabled={!commentText.trim()}
                                            onClick={() => addComment({ variables: { reminderId: selectedReminder.id, text: commentText, parentId: replyToId }})}
                                        >
                                            {replyToId ? "Reply" : "Comment"}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <aside className="details-sidebar">
                                <div className="sidebar-group">
                                    <label>Timeline</label>
                                    <div className="sidebar-info">
                                        <Clock size={16} />
                                        <span>Start: {selectedReminder.reminderStartDate ? format(new Date(selectedReminder.reminderStartDate), 'PPP') : 'Not set'}</span>
                                    </div>
                                </div>

                                <div className="sidebar-group">
                                    <label>Approval Status</label>
                                    <div className={`approval-badge ${selectedReminder.isApproved ? 'approved' : 'pending'}`}>
                                        {selectedReminder.isApproved ? (
                                            <>
                                                <CheckCircle size={14} /> Approved by {selectedReminder.approvedBy?.username}
                                            </>
                                        ) : (
                                            <>
                                                <Clock size={14} /> Awaiting Approval
                                            </>
                                        )}
                                    </div>
                                    
                                    {selectedReminder.createdBy?.manager?.id === data?.me?.id && !selectedReminder.isApproved && (
                                        <button 
                                            className="btn-primary w-full mt-4"
                                            onClick={() => approveReminder({ variables: { id: selectedReminder.id }})}
                                        >
                                            Approve Now
                                        </button>
                                    )}
                                </div>

                                {selectedReminder.attachments?.length > 0 && (
                                    <div className="sidebar-group">
                                        <label>Attachments</label>
                                        <div className="attachments-list">
                                            {selectedReminder.attachments.map(att => (
                                                <a 
                                                    key={att.id} 
                                                    href={`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}${att.url}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="att-link"
                                                >
                                                    <Paperclip size={14} /> {att.filename}
                                                </a>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </aside>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
