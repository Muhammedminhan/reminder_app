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
    X,
    UserPlus,
    Edit3,
    Lock,
    Unlock,
    Crown,
    Tag,
    Save,
    AlertTriangle
} from 'lucide-react';
import { logout, isAuthenticated } from '../lib/api';
import { format } from 'date-fns';
import CreateReminderModal from '../components/CreateReminderModal';
import UpdateProfileModal from '../components/UpdateProfileModal';
import Toast, { useToast } from '../components/Toast';

// ── Admin mutations ──────────────────────────────────────────────────────────

const CREATE_USER = gql`
  mutation CreateUser($username: String!, $email: String!, $password: String!, $firstName: String, $lastName: String, $isStaff: Boolean, $isSuperuser: Boolean, $companyId: ID, $departmentIds: [ID]) {
    createUser(username: $username, email: $email, password: $password, firstName: $firstName, lastName: $lastName, isStaff: $isStaff, isSuperuser: $isSuperuser, companyId: $companyId, departmentIds: $departmentIds) {
      ok user { id username email firstName lastName isSuperuser isStaff }
    }
  }
`;

const UPDATE_USER_ADMIN = gql`
  mutation UpdateUser($id: ID!, $firstName: String, $lastName: String, $email: String, $isStaff: Boolean, $isSuperuser: Boolean, $isActive: Boolean) {
    updateUser(id: $id, firstName: $firstName, lastName: $lastName, email: $email, isStaff: $isStaff, isSuperuser: $isSuperuser, isActive: $isActive) {
      ok user { id username email firstName lastName isSuperuser isStaff isActive }
    }
  }
`;

const DELETE_USER_MUTATION = gql`
  mutation DeleteUser($id: ID!) {
    deleteUser(id: $id) { ok }
  }
`;

const CREATE_DEPT = gql`
  mutation CreateDepartment($name: String!, $companyId: ID) {
    createDepartment(name: $name, companyId: $companyId) {
      ok department { id name }
    }
  }
`;

const DELETE_DEPT = gql`
  mutation DeleteDepartment($id: ID!) {
    deleteDepartment(id: $id) { ok }
  }
`;

const CREATE_ROLE = gql`
  mutation CreateRole($name: String!, $description: String, $permissionIds: [ID]) {
    createRole(name: $name, description: $description, permissionIds: $permissionIds) {
      ok role { id name description }
    }
  }
`;

const DELETE_ROLE = gql`
  mutation DeleteRole($id: ID!) {
    deleteRole(id: $id) { ok }
  }
`;

const ASSIGN_ROLE = gql`
  mutation AssignRoleToUser($userId: ID!, $roleId: ID!) {
    assignRoleToUser(userId: $userId, roleId: $roleId) { ok }
  }
`;

const ADMIN_QUERY = gql`
  query GetAdminData {
    users { id username email firstName lastName isSuperuser isStaff isActive departments { id name } }
    companies { id name email address website }
    departments { id name company { name } }
    roles { id name description permissions { id name } }
    permissions { id name code category description isActive }
    reminders { id title receiverEmail active send completed company { name } createdBy { username } reminderStartDate intervalType }
    oauthApplications { id name clientId clientType authorizationGrantType }
    userRoles { id user { id username email } role { id name } company { name } isActive assignedAt }
    sendgridDomainAuths { id domain customerId isVerified user { username } createdAt }
    auditLogs { id actorUsername action objectRepr contentTypeName timestamp }
    accessTokensAdmin { id userUsername tokenMasked expires scope }
  }
`;

const REMOVE_ROLE_FROM_USER = gql`
  mutation RemoveRoleFromUser($userId: ID!, $roleId: ID!) {
    removeRoleFromUser(userId: $userId, roleId: $roleId) { ok }
  }
`;

const CREATE_PERMISSION = gql`
  mutation CreatePermission($code: String!, $name: String!, $category: String, $description: String) {
    createPermission(code: $code, name: $name, category: $category, description: $description) {
      ok permission { id code name category }
    }
  }
`;

const DELETE_PERMISSION = gql`
  mutation DeletePermission($id: ID!) {
    deletePermission(id: $id) { ok }
  }
`;

const CREATE_COMPANY = gql`
  mutation CreateCompany($name: String!, $email: String, $address: String, $website: String) {
    createCompany(name: $name, email: $email, address: $address, website: $website) {
      ok company { id name email }
    }
  }
`;

const DELETE_COMPANY_MUTATION = gql`
  mutation DeleteCompany($id: ID!) {
    deleteCompany(id: $id) { ok }
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
      reminderEndDate
      active
      completed
      slackChannels
      slackUserId
      isFormal
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
      isSuperuser
      isStaff
      company {
        id
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
    slackConfigured
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
    const [adminTab, setAdminTab] = useState('users');
    const [showCreateUser, setShowCreateUser] = useState(false);
    const [showCreateDept, setShowCreateDept] = useState(false);
    const [showCreateRole, setShowCreateRole] = useState(false);
    const [newUserForm, setNewUserForm] = useState({ username:'', email:'', password:'', firstName:'', lastName:'', isStaff:false, isSuperuser:false });
    const [newDeptName, setNewDeptName] = useState('');
    const [newRoleForm, setNewRoleForm] = useState({ name:'', description:'' });
    // adminData query and admin mutations — declared here but skip logic uses isAdmin state set after INITIAL_QUERY
    const [isAdminUser, setIsAdminUser] = useState(false);
    const [showCreateCompany, setShowCreateCompany] = useState(false);
    const [newCompanyForm, setNewCompanyForm] = useState({ name:'', email:'', address:'', website:'' });
    const [showAssignRole, setShowAssignRole] = useState(false);
    const [assignRoleForm, setAssignRoleForm] = useState({ userId:'', roleId:'' });
    const [showCreatePermission, setShowCreatePermission] = useState(false);
    const [newPermissionForm, setNewPermissionForm] = useState({ code:'', name:'', category:'', description:'' });
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
    const [isDarkMode, setIsDarkMode] = useState(false);
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

    // Set admin flag once me data loads
    useEffect(() => {
        if (data?.me) {
            setIsAdminUser(!!data.me.isSuperuser || !!data.me.isStaff);
        }
    }, [data?.me]);

    // ── Admin query + mutations (safe to declare here — after INITIAL_QUERY) ──
    const { data: adminData, refetch: refetchAdmin } = useQuery(ADMIN_QUERY, { skip: !isAdminUser });
    const [createUser] = useMutation(CREATE_USER, { onCompleted: () => { refetchAdmin(); setShowCreateUser(false); setNewUserForm({ username:'', email:'', password:'', firstName:'', lastName:'', isStaff:false, isSuperuser:false }); showToast('User created'); }});
    const [deleteUserMutation] = useMutation(DELETE_USER_MUTATION, { onCompleted: () => { refetchAdmin(); showToast('User deleted'); }});
    const [updateUserAdmin] = useMutation(UPDATE_USER_ADMIN, { onCompleted: () => { refetchAdmin(); showToast('User updated'); }});
    const [createDept] = useMutation(CREATE_DEPT, { onCompleted: () => { refetchAdmin(); setShowCreateDept(false); setNewDeptName(''); showToast('Department created'); }});
    const [deleteDept] = useMutation(DELETE_DEPT, { onCompleted: () => { refetchAdmin(); showToast('Department deleted'); }});
    const [createRole] = useMutation(CREATE_ROLE, { onCompleted: () => { refetchAdmin(); setShowCreateRole(false); setNewRoleForm({ name:'', description:'' }); showToast('Role created'); }});
    const [deleteRole] = useMutation(DELETE_ROLE, { onCompleted: () => { refetchAdmin(); showToast('Role deleted'); }});
    const [assignRole] = useMutation(ASSIGN_ROLE, { onCompleted: () => { refetchAdmin(); setShowAssignRole(false); setAssignRoleForm({ userId:'', roleId:'' }); showToast('Role assigned'); }});
    const [removeRoleFromUser] = useMutation(REMOVE_ROLE_FROM_USER, { onCompleted: () => { refetchAdmin(); showToast('Role removed'); }});
    const [createPermission] = useMutation(CREATE_PERMISSION, { onCompleted: () => { refetchAdmin(); setShowCreatePermission(false); setNewPermissionForm({ code:'', name:'', category:'', description:'' }); showToast('Permission created'); }});
    const [deletePermission] = useMutation(DELETE_PERMISSION, { onCompleted: () => { refetchAdmin(); showToast('Permission deleted'); }});
    const [createCompany] = useMutation(CREATE_COMPANY, { onCompleted: () => { refetchAdmin(); setShowCreateCompany(false); setNewCompanyForm({ name:'', email:'', address:'', website:'' }); showToast('Company created'); }});
    const [deleteCompanyMutation] = useMutation(DELETE_COMPANY_MUTATION, { onCompleted: () => { refetchAdmin(); showToast('Company deleted'); }});

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
        // Exclude expired reminders
        const now = new Date();
        if (r.reminderEndDate && new Date(r.reminderEndDate) < now) {
            return false;
        }

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
                                                                                    href={`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}${att.url}?token=${localStorage.getItem('access_token') || ''}`}
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
                                        {(activeView === 'pending' ? filteredReminders.filter(r => r.isFormal && !r.completed) : filteredReminders).map(reminder => (
                                            <tr key={reminder.id}>
                                                <td className="bold">
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                        {reminder.title}
                                                        {reminder.isFormal && (
                                                            <span className="mini-tag" style={{ background: 'var(--primary-glow)', fontSize: '10px' }}>Formal</span>
                                                        )}
                                                    </div>
                                                </td>
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
                                                        {reminder.isFormal && !reminder.completed && (
                                                            <button 
                                                                className="btn-primary small" 
                                                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                                                onClick={() => toggleComplete(reminder.id, reminder.completed)}
                                                            >
                                                                Done
                                                            </button>
                                                        )}
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
                                                        
                                                        {!reminder.isFormal && (
                                                            <button 
                                                                title={reminder.completed ? "Mark Incomplete" : "Finalize"}
                                                                onClick={() => toggleComplete(reminder.id, reminder.completed)}
                                                            >
                                                                <CheckCircle size={18} color={reminder.completed ? "var(--success)" : "currentColor"} />
                                                            </button>
                                                        )}
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
                                {['Profile', 'Team', 'Security', 'Integration', ...(isAdminUser ? ['Admin'] : [])].map(tab => (
                                    <button key={tab} className={settingsTab === tab ? 'active' : ''} onClick={() => setSettingsTab(tab)}>
                                        {tab === 'Admin' ? <span style={{ display:'flex', alignItems:'center', gap:'5px' }}><Crown size={12} />{tab}</span> : tab}
                                    </button>
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
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

                                    {/* ── Slack Integration Card ── */}
                                    <div className="glass-card integration-section animate-fade">
                                        <div className="section-header">
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                <div className="header-icon" style={{ display:'flex', alignItems:'center', justifyContent:'center' }}>
                                                    {/* Slack logo mark */}
                                                    <svg width="20" height="20" viewBox="0 0 54 54" fill="none">
                                                        <path d="M19.712 33.316a3.93 3.93 0 0 1-3.925 3.925 3.93 3.93 0 0 1-3.924-3.925 3.93 3.93 0 0 1 3.924-3.924h3.925v3.924z" fill="#E01E5A"/>
                                                        <path d="M21.67 33.316a3.93 3.93 0 0 1 3.924-3.924 3.93 3.93 0 0 1 3.925 3.924v9.812a3.93 3.93 0 0 1-3.925 3.924 3.93 3.93 0 0 1-3.924-3.924v-9.812z" fill="#E01E5A"/>
                                                        <path d="M25.594 19.712a3.93 3.93 0 0 1-3.924-3.925 3.93 3.93 0 0 1 3.924-3.924 3.93 3.93 0 0 1 3.925 3.924v3.925h-3.925z" fill="#36C5F0"/>
                                                        <path d="M25.594 21.67a3.93 3.93 0 0 1 3.925 3.924 3.93 3.93 0 0 1-3.925 3.924H15.782a3.93 3.93 0 0 1-3.924-3.924 3.93 3.93 0 0 1 3.924-3.924h9.812z" fill="#36C5F0"/>
                                                        <path d="M39.288 25.594a3.93 3.93 0 0 1 3.924 3.924 3.93 3.93 0 0 1-3.924 3.924 3.93 3.93 0 0 1-3.924-3.924v-3.924h3.924z" fill="#2EB67D"/>
                                                        <path d="M37.33 25.594a3.93 3.93 0 0 1-3.924-3.924 3.93 3.93 0 0 1 3.924-3.924h9.812a3.93 3.93 0 0 1 3.924 3.924 3.93 3.93 0 0 1-3.924 3.924H37.33z" fill="#2EB67D"/>
                                                        <path d="M33.406 39.288a3.93 3.93 0 0 1 3.924 3.924 3.93 3.93 0 0 1-3.924 3.924 3.93 3.93 0 0 1-3.924-3.924V35.364h3.924z" fill="#ECB22E"/>
                                                        <path d="M33.406 37.33a3.93 3.93 0 0 1-3.924-3.924 3.93 3.93 0 0 1 3.924-3.925v.001h.001v-.001a3.93 3.93 0 0 1 3.924 3.924 3.93 3.93 0 0 1-3.924 3.924h-.001z" fill="#ECB22E"/>
                                                        <path d="M33.406 21.67V11.858a3.93 3.93 0 0 0-3.924-3.924 3.93 3.93 0 0 0-3.924 3.924 3.93 3.93 0 0 0 3.924 3.924h3.924v5.888z" fill="#ECB22E" opacity="0"/>
                                                    </svg>
                                                </div>
                                                <div>
                                                    <h3>Slack Notifications</h3>
                                                    <p className="text-dim">Send reminder alerts to Slack channels and teammates.</p>
                                                </div>
                                            </div>
                                            <div className={`status-badge ${data?.slackConfigured ? 'active' : 'inactive'}`}>
                                                {data?.slackConfigured ? 'Connected' : 'Not Connected'}
                                            </div>
                                        </div>

                                        {data?.slackConfigured ? (
                                            <div style={{ padding: '24px 32px' }}>
                                                <div style={{ display:'flex', alignItems:'center', gap:'10px', padding:'14px 18px', background:'rgba(0,171,228,0.06)', border:'1px solid rgba(0,171,228,0.18)', borderRadius:'12px', marginBottom:'16px' }}>
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00ABE4" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                                                    <span style={{ fontSize:'13.5px', color:'#0d1f2d', fontWeight:'500' }}>Slack Bot Token is configured. Channel and user notifications are active.</span>
                                                </div>
                                                <p style={{ fontSize:'13px', color:'#6b8099', lineHeight:'1.6' }}>
                                                    To change the token, update the <code style={{ background:'#f4f8fc', padding:'2px 6px', borderRadius:'4px', color:'#00ABE4' }}>SLACK_BOT_TOKEN</code> environment variable on your server and redeploy.
                                                </p>
                                            </div>
                                        ) : (
                                            <div style={{ padding: '24px 32px' }}>
                                                <div style={{ display:'flex', alignItems:'flex-start', gap:'10px', padding:'14px 18px', background:'rgba(251,191,36,0.08)', border:'1px solid rgba(251,191,36,0.25)', borderRadius:'12px', marginBottom:'20px' }}>
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2" style={{marginTop:'2px', flexShrink:0}}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                                                    <span style={{ fontSize:'13px', color:'#92400e' }}>Slack is not connected. Follow the steps below to enable notifications.</span>
                                                </div>

                                                <div style={{ display:'flex', flexDirection:'column', gap:'16px' }}>
                                                    {[
                                                        { step:'1', title:'Create a Slack App', desc: <>Go to <a href="https://api.slack.com/apps" target="_blank" rel="noopener noreferrer" style={{color:'#00ABE4'}}>api.slack.com/apps</a> → <strong>Create New App</strong> → <strong>From scratch</strong>. Name it "NotifyHub" and pick your workspace.</> },
                                                        { step:'2', title:'Add Bot Scopes', desc: <>Under <strong>OAuth & Permissions → Scopes → Bot Token Scopes</strong>, add: <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>chat:write</code> <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>channels:read</code> <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>users:read</code> <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>users:read.email</code> <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>im:write</code></> },
                                                        { step:'3', title:'Install to Workspace', desc: <>Click <strong>Install to Workspace</strong> and authorise. Copy the <strong>Bot User OAuth Token</strong> (starts with <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>xoxb-</code>).</> },
                                                        { step:'4', title:'Invite Bot to Channels', desc: <>In Slack, go to each channel you want NotifyHub to post in and type <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>/invite @NotifyHub</code>.</> },
                                                        { step:'5', title:'Set Environment Variable', desc: <>Add <code style={{background:'#f4f8fc',padding:'2px 6px',borderRadius:'4px',color:'#00ABE4',fontSize:'12px'}}>SLACK_BOT_TOKEN=xoxb-your-token</code> to your Cloud Run service environment variables (or <code>.env</code> for local dev), then redeploy.</> },
                                                    ].map(({ step, title, desc }) => (
                                                        <div key={step} style={{ display:'flex', gap:'14px', alignItems:'flex-start' }}>
                                                            <div style={{ width:'28px', height:'28px', borderRadius:'50%', background:'rgba(0,171,228,0.12)', border:'1.5px solid rgba(0,171,228,0.3)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, fontSize:'12px', fontWeight:'700', color:'#00ABE4' }}>{step}</div>
                                                            <div>
                                                                <p style={{ fontSize:'13.5px', fontWeight:'600', color:'#0d1f2d', marginBottom:'3px' }}>{title}</p>
                                                                <p style={{ fontSize:'13px', color:'#6b8099', lineHeight:'1.6', margin:0 }}>{desc}</p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* ── Jira Integration Card ── */}
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
                                    </div> /* end Integration flex wrapper */
                                )}

                                {/* ══ ADMIN TAB ══════════════════════════════════════════════ */}
                                {settingsTab === 'Admin' && isAdminUser && (() => {
                                    const aUsers = adminData?.users || [];
                                    const aDepts = adminData?.departments || [];
                                    const aRoles = adminData?.roles || [];
                                    const aPerms = adminData?.permissions || [];
                                    const aCompanies = adminData?.companies || [];
                                    const aReminders = adminData?.reminders || [];
                                    const aOAuthApps = adminData?.oauthApplications || [];
                                    const aUserRoles = adminData?.userRoles || [];
                                    const aSendGridAuths = adminData?.sendgridDomainAuths || [];
                                    const aAuditLogs = adminData?.auditLogs || [];
                                    const aAccessTokens = adminData?.accessTokensAdmin || [];

                                    const adminCardStyle = { background:'#FFFFFF', border:'1px solid rgba(0,171,228,0.18)', borderRadius:'20px', marginBottom:'24px', overflow:'hidden', boxShadow:'0 2px 12px rgba(0,171,228,0.07)' };
                                    const adminHeaderStyle = { padding:'18px 28px', background:'linear-gradient(135deg,rgba(0,171,228,0.07) 0%,rgba(233,241,250,0.5) 100%)', borderBottom:'1px solid rgba(0,171,228,0.12)', display:'flex', justifyContent:'space-between', alignItems:'center' };
                                    const adminBodyStyle = { padding:'20px 24px' };
                                    const inputStyle = { width:'100%', padding:'10px 14px', borderRadius:'10px', border:'1.5px solid rgba(0,171,228,0.2)', background:'#f4f8fc', fontSize:'13.5px', color:'#0d1f2d', outline:'none', boxSizing:'border-box' };
                                    const smallBtnStyle = (danger) => ({ padding:'6px 14px', borderRadius:'8px', fontSize:'12px', fontWeight:'600', cursor:'pointer', border: danger ? '1px solid rgba(239,68,68,0.3)' : '1.5px solid rgba(0,171,228,0.3)', background: danger ? 'rgba(239,68,68,0.06)' : 'rgba(0,171,228,0.08)', color: danger ? '#dc2626' : '#00ABE4' });
                                    const primaryBtnStyle = { padding:'9px 18px', borderRadius:'10px', fontSize:'13px', fontWeight:'600', cursor:'pointer', background:'#00ABE4', color:'#fff', border:'none', boxShadow:'0 3px 10px rgba(0,171,228,0.3)' };

                                    return (
                                    <div>
                                        {/* Sub-nav */}
                                        <div style={{ display:'flex', gap:'8px', marginBottom:'24px', flexWrap:'wrap' }}>
                                            {[['users','Users',Users],['departments','Departments',Building],['roles','Roles',Shield],['companies','Company',Briefcase],['reminders','Reminders',Bell],['oauth','OAuth Apps',Key],['userroles','User Roles',Users],['sendgrid','SendGrid',Mail],['auditlog','Audit Log',Activity],['accesstokens','Access Tokens',Key],['permissions','Permissions',Lock]].map(([k,label,Icon]) => (
                                                <button key={k} onClick={() => setAdminTab(k)} style={{ display:'flex', alignItems:'center', gap:'6px', padding:'8px 16px', borderRadius:'10px', fontSize:'13px', fontWeight:'600', cursor:'pointer', border:'1.5px solid', borderColor: adminTab===k ? '#00ABE4' : 'rgba(0,171,228,0.2)', background: adminTab===k ? '#00ABE4' : '#fff', color: adminTab===k ? '#fff' : '#3d5a73', transition:'all 0.18s' }}>
                                                    <Icon size={14} />{label}
                                                </button>
                                            ))}
                                        </div>

                                        {/* ── USERS ── */}
                                        {adminTab === 'users' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>User Management</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aUsers.length} users in workspace</div>
                                                </div>
                                                <button style={primaryBtnStyle} onClick={() => setShowCreateUser(v=>!v)}>
                                                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><UserPlus size={14} /> Create User</span>
                                                </button>
                                            </div>

                                            {showCreateUser && (
                                                <div style={{ padding:'20px 24px', borderBottom:'1px solid rgba(0,171,228,0.1)', background:'rgba(0,171,228,0.02)' }}>
                                                    <div style={{ fontWeight:'600', color:'#0d1f2d', marginBottom:'14px', fontSize:'13.5px' }}>New User Details</div>
                                                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'12px' }}>
                                                        {[['username','Username','e.g. john_doe'],['email','Email','john@company.com'],['password','Password','Min 8 characters'],['firstName','First Name','John'],['lastName','Last Name','Doe']].map(([k,label,ph]) => (
                                                            <div key={k}>
                                                                <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>{label}</div>
                                                                <input type={k==='password'?'password':'text'} placeholder={ph} value={newUserForm[k]||''} onChange={e=>setNewUserForm(f=>({...f,[k]:e.target.value}))} style={inputStyle} />
                                                            </div>
                                                        ))}
                                                        <div>
                                                            <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'8px', textTransform:'uppercase', letterSpacing:'0.06em' }}>Roles</div>
                                                            <div style={{ display:'flex', gap:'10px' }}>
                                                                {[['isStaff','Staff'],['isSuperuser','Superuser']].map(([k,label]) => (
                                                                    <label key={k} style={{ display:'flex', alignItems:'center', gap:'6px', fontSize:'13px', cursor:'pointer', color:'#0d1f2d' }}>
                                                                        <input type="checkbox" checked={!!newUserForm[k]} onChange={e=>setNewUserForm(f=>({...f,[k]:e.target.checked}))} style={{ accentColor:'#00ABE4' }} />{label}
                                                                    </label>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div style={{ display:'flex', gap:'10px' }}>
                                                        <button style={primaryBtnStyle} onClick={() => createUser({ variables: { ...newUserForm, companyId: data?.me?.company?.id } })}>
                                                            <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Save size={13} /> Save User</span>
                                                        </button>
                                                        <button style={{ ...smallBtnStyle(false), background:'#fff' }} onClick={() => setShowCreateUser(false)}>Cancel</button>
                                                    </div>
                                                </div>
                                            )}

                                            <div style={adminBodyStyle}>
                                                {aUsers.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No users found</div>
                                                ) : (
                                                    <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                                                        {aUsers.map(u => (
                                                            <div key={u.id} style={{ display:'flex', alignItems:'center', gap:'14px', padding:'12px 16px', background:'#f4f8fc', borderRadius:'12px', border:'1px solid rgba(0,171,228,0.1)' }}>
                                                                <div style={{ width:'38px', height:'38px', borderRadius:'10px', background:'linear-gradient(135deg,#00ABE4,#0090c4)', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontWeight:'700', fontSize:'15px', flexShrink:0 }}>
                                                                    {(u.firstName||u.username||'?')[0].toUpperCase()}
                                                                </div>
                                                                <div style={{ flex:1, minWidth:0 }}>
                                                                    <div style={{ fontWeight:'600', color:'#0d1f2d', fontSize:'13.5px' }}>{u.firstName} {u.lastName} <span style={{ color:'#94afc5', fontWeight:'400' }}>@{u.username}</span></div>
                                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{u.email}</div>
                                                                </div>
                                                                <div style={{ display:'flex', gap:'6px', alignItems:'center', flexShrink:0 }}>
                                                                    {u.isSuperuser && <span style={{ padding:'2px 8px', borderRadius:'6px', background:'rgba(239,68,68,0.08)', color:'#dc2626', fontSize:'11px', fontWeight:'700' }}>Superuser</span>}
                                                                    {u.isStaff && !u.isSuperuser && <span style={{ padding:'2px 8px', borderRadius:'6px', background:'rgba(0,171,228,0.1)', color:'#00ABE4', fontSize:'11px', fontWeight:'700' }}>Staff</span>}
                                                                    {!u.isActive && <span style={{ padding:'2px 8px', borderRadius:'6px', background:'rgba(148,163,184,0.15)', color:'#94a3b8', fontSize:'11px', fontWeight:'700' }}>Inactive</span>}
                                                                    <button style={smallBtnStyle(false)} title="Toggle active" onClick={() => updateUserAdmin({ variables:{ id:u.id, isActive:!u.isActive } })}>
                                                                        {u.isActive ? <Unlock size={12} /> : <Lock size={12} />}
                                                                    </button>
                                                                    {u.id !== data?.me?.id && (
                                                                        <button style={smallBtnStyle(true)} title="Delete user" onClick={() => { if(window.confirm(`Delete user ${u.username}?`)) deleteUserMutation({ variables:{ id:u.id } }); }}>
                                                                            <Trash2 size={12} />
                                                                        </button>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── DEPARTMENTS ── */}
                                        {adminTab === 'departments' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>Departments</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aDepts.length} departments</div>
                                                </div>
                                                <button style={primaryBtnStyle} onClick={() => setShowCreateDept(v=>!v)}>
                                                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Plus size={14} /> New Department</span>
                                                </button>
                                            </div>
                                            {showCreateDept && (
                                                <div style={{ padding:'16px 24px', borderBottom:'1px solid rgba(0,171,228,0.1)', background:'rgba(0,171,228,0.02)', display:'flex', gap:'10px', alignItems:'flex-end' }}>
                                                    <div style={{ flex:1 }}>
                                                        <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>Department Name</div>
                                                        <input placeholder="e.g. Engineering" value={newDeptName} onChange={e=>setNewDeptName(e.target.value)} style={inputStyle} />
                                                    </div>
                                                    <button style={primaryBtnStyle} onClick={() => createDept({ variables:{ name:newDeptName, companyId:data?.me?.company?.id } })}>
                                                        <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Save size={13} /> Save</span>
                                                    </button>
                                                    <button style={{ ...smallBtnStyle(false), background:'#fff' }} onClick={() => setShowCreateDept(false)}>Cancel</button>
                                                </div>
                                            )}
                                            <div style={adminBodyStyle}>
                                                {aDepts.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No departments yet</div>
                                                ) : (
                                                    <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(200px,1fr))', gap:'10px' }}>
                                                        {aDepts.map(d => (
                                                            <div key={d.id} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 16px', background:'#f4f8fc', borderRadius:'12px', border:'1px solid rgba(0,171,228,0.1)' }}>
                                                                <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
                                                                    <Building size={14} color="#00ABE4" />
                                                                    <span style={{ fontWeight:'600', color:'#0d1f2d', fontSize:'13.5px' }}>{d.name}</span>
                                                                </div>
                                                                <button style={smallBtnStyle(true)} onClick={() => { if(window.confirm(`Delete department ${d.name}?`)) deleteDept({ variables:{ id:d.id } }); }}>
                                                                    <Trash2 size={12} />
                                                                </button>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── ROLES & PERMISSIONS ── */}
                                        {adminTab === 'roles' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>Roles & Permissions</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aRoles.length} roles · {aPerms.length} permissions</div>
                                                </div>
                                                <button style={primaryBtnStyle} onClick={() => setShowCreateRole(v=>!v)}>
                                                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Plus size={14} /> New Role</span>
                                                </button>
                                            </div>
                                            {showCreateRole && (
                                                <div style={{ padding:'16px 24px', borderBottom:'1px solid rgba(0,171,228,0.1)', background:'rgba(0,171,228,0.02)' }}>
                                                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'12px' }}>
                                                        <div>
                                                            <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>Role Name</div>
                                                            <input placeholder="e.g. HR Manager" value={newRoleForm.name} onChange={e=>setNewRoleForm(f=>({...f,name:e.target.value}))} style={inputStyle} />
                                                        </div>
                                                        <div>
                                                            <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>Description</div>
                                                            <input placeholder="What can this role do?" value={newRoleForm.description} onChange={e=>setNewRoleForm(f=>({...f,description:e.target.value}))} style={inputStyle} />
                                                        </div>
                                                    </div>
                                                    <div style={{ display:'flex', gap:'10px' }}>
                                                        <button style={primaryBtnStyle} onClick={() => createRole({ variables: newRoleForm })}>
                                                            <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Save size={13} /> Save Role</span>
                                                        </button>
                                                        <button style={{ ...smallBtnStyle(false), background:'#fff' }} onClick={() => setShowCreateRole(false)}>Cancel</button>
                                                    </div>
                                                </div>
                                            )}
                                            <div style={adminBodyStyle}>
                                                {aRoles.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No roles yet. Run <code style={{ background:'#f4f8fc', padding:'2px 6px', borderRadius:'4px', color:'#00ABE4' }}>setup_permissions --create-roles</code> to seed defaults.</div>
                                                ) : (
                                                    <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                                                        {aRoles.map(r => (
                                                            <div key={r.id} style={{ padding:'14px 16px', background:'#f4f8fc', borderRadius:'12px', border:'1px solid rgba(0,171,228,0.1)' }}>
                                                                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'8px' }}>
                                                                    <div>
                                                                        <span style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'13.5px' }}>{r.name}</span>
                                                                        {r.description && <span style={{ marginLeft:'8px', fontSize:'12px', color:'#6b8099' }}>{r.description}</span>}
                                                                    </div>
                                                                    <button style={smallBtnStyle(true)} onClick={() => { if(window.confirm(`Delete role ${r.name}?`)) deleteRole({ variables:{ id:r.id } }); }}>
                                                                        <Trash2 size={12} />
                                                                    </button>
                                                                </div>
                                                                <div style={{ display:'flex', flexWrap:'wrap', gap:'6px' }}>
                                                                    {(r.permissions||[]).map(p => (
                                                                        <span key={p.id} style={{ padding:'2px 8px', borderRadius:'6px', background:'rgba(0,171,228,0.1)', color:'#00ABE4', fontSize:'11px', fontWeight:'600' }}>{p.name}</span>
                                                                    ))}
                                                                    {(r.permissions||[]).length === 0 && <span style={{ fontSize:'12px', color:'#94afc5' }}>No permissions assigned</span>}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── COMPANY ── */}
                                        {adminTab === 'companies' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>Companies</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aCompanies.length} {aCompanies.length===1?'company':'companies'}</div>
                                                </div>
                                                <button style={primaryBtnStyle} onClick={() => setShowCreateCompany(v=>!v)}>
                                                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Plus size={14} /> Add Company</span>
                                                </button>
                                            </div>
                                            {showCreateCompany && (
                                                <div style={{ padding:'20px 24px', borderBottom:'1px solid rgba(0,171,228,0.1)', background:'rgba(0,171,228,0.02)' }}>
                                                    <div style={{ fontWeight:'600', color:'#0d1f2d', marginBottom:'14px', fontSize:'13.5px' }}>New Company</div>
                                                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'12px' }}>
                                                        {[['name','Company Name','e.g. Acme Corp'],['email','Email','contact@company.com'],['address','Address','123 Main St'],['website','Website','https://company.com']].map(([k,label,ph]) => (
                                                            <div key={k}>
                                                                <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>{label}</div>
                                                                <input placeholder={ph} value={newCompanyForm[k]} onChange={e=>setNewCompanyForm(f=>({...f,[k]:e.target.value}))} style={inputStyle} />
                                                            </div>
                                                        ))}
                                                    </div>
                                                    <div style={{ display:'flex', gap:'10px' }}>
                                                        <button style={primaryBtnStyle} onClick={() => createCompany({ variables: newCompanyForm })}>
                                                            <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Save size={13} /> Save Company</span>
                                                        </button>
                                                        <button style={{ ...smallBtnStyle(false), background:'#fff' }} onClick={() => setShowCreateCompany(false)}>Cancel</button>
                                                    </div>
                                                </div>
                                            )}
                                            <div style={adminBodyStyle}>
                                                {aCompanies.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No companies found</div>
                                                ) : (
                                                    <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                                                        {aCompanies.map(c => {
                                                            const deptCount = aDepts.filter(d => d.company?.name === c.name).length;
                                                            const userCount = aUsers.filter(u => u.departments?.length > 0).length;
                                                            return (
                                                            <div key={c.id} style={{ display:'flex', alignItems:'center', gap:'14px', padding:'14px 18px', background:'#f4f8fc', borderRadius:'12px', border:'1px solid rgba(0,171,228,0.1)' }}>
                                                                <div style={{ width:'44px', height:'44px', borderRadius:'12px', background:'linear-gradient(135deg,#00ABE4,#0090c4)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, fontSize:'18px', fontWeight:'800', color:'#fff' }}>
                                                                    {c.name[0].toUpperCase()}
                                                                </div>
                                                                <div style={{ flex:1 }}>
                                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'14px' }}>{c.name}</div>
                                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{c.email} {c.website && <span>· <a href={c.website} target="_blank" rel="noopener noreferrer" style={{ color:'#00ABE4' }}>{c.website}</a></span>}</div>
                                                                </div>
                                                                <div style={{ display:'flex', gap:'8px', alignItems:'center' }}>
                                                                    <span style={{ padding:'3px 10px', borderRadius:'8px', background:'rgba(0,171,228,0.08)', color:'#00ABE4', fontSize:'11.5px', fontWeight:'600' }}>{deptCount} depts</span>
                                                                    <span style={{ padding:'3px 10px', borderRadius:'8px', background:'rgba(0,171,228,0.08)', color:'#00ABE4', fontSize:'11.5px', fontWeight:'600' }}>{aUsers.filter(u=>true).length} users</span>
                                                                    <button style={smallBtnStyle(true)} title="Delete company" onClick={() => { if(window.confirm(`Delete company "${c.name}"? This will affect all users in this company.`)) deleteCompanyMutation({ variables:{ id:c.id } }); }}>
                                                                        <Trash2 size={12} />
                                                                    </button>
                                                                </div>
                                                            </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── REMINDERS (admin) ── */}
                                        {adminTab === 'reminders' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>All Reminders</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aReminders.length} total reminders across all companies</div>
                                                </div>
                                            </div>
                                            <div style={adminBodyStyle}>
                                                {aReminders.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No reminders found</div>
                                                ) : (
                                                    <div style={{ overflowX:'auto' }}>
                                                        <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'13px' }}>
                                                            <thead>
                                                                <tr style={{ background:'rgba(0,171,228,0.05)', borderBottom:'1.5px solid rgba(0,171,228,0.12)' }}>
                                                                    {['Title','Recipient','Company','Status','Cadence','Created By'].map(h => (
                                                                        <th key={h} style={{ padding:'10px 14px', textAlign:'left', fontWeight:'700', color:'#3d5a73', fontSize:'12px', whiteSpace:'nowrap' }}>{h}</th>
                                                                    ))}
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {aReminders.map(r => (
                                                                    <tr key={r.id} style={{ borderBottom:'1px solid rgba(0,171,228,0.07)' }}>
                                                                        <td style={{ padding:'10px 14px', fontWeight:'600', color:'#0d1f2d', maxWidth:'200px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.title}</td>
                                                                        <td style={{ padding:'10px 14px', color:'#3d5a73' }}>{r.receiverEmail}</td>
                                                                        <td style={{ padding:'10px 14px', color:'#3d5a73' }}>{r.company?.name || '—'}</td>
                                                                        <td style={{ padding:'10px 14px' }}>
                                                                            <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background: r.completed ? 'rgba(16,185,129,0.1)' : r.active ? 'rgba(0,171,228,0.1)' : 'rgba(239,68,68,0.08)', color: r.completed ? '#059669' : r.active ? '#00ABE4' : '#dc2626' }}>
                                                                                {r.completed ? 'Completed' : r.active ? 'Active' : 'Inactive'}
                                                                            </span>
                                                                        </td>
                                                                        <td style={{ padding:'10px 14px', color:'#3d5a73', textTransform:'capitalize' }}>{r.intervalType || '—'}</td>
                                                                        <td style={{ padding:'10px 14px', color:'#3d5a73' }}>{r.createdBy?.username || '—'}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── OAUTH APPS (admin) ── */}
                                        {adminTab === 'oauth' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>OAuth Applications</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aOAuthApps.length} registered OAuth apps</div>
                                                </div>
                                            </div>
                                            <div style={adminBodyStyle}>
                                                {aOAuthApps.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No OAuth applications found</div>
                                                ) : (
                                                    <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
                                                        {aOAuthApps.map(app => (
                                                            <div key={app.id} style={{ display:'flex', alignItems:'center', gap:'14px', padding:'14px 18px', background:'#f4f8fc', borderRadius:'12px', border:'1px solid rgba(0,171,228,0.1)' }}>
                                                                <div style={{ width:'40px', height:'40px', borderRadius:'12px', background:'linear-gradient(135deg,#6366f1,#4f46e5)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                                                                    <Key size={18} color="#fff" />
                                                                </div>
                                                                <div style={{ flex:1 }}>
                                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'14px' }}>{app.name || '(unnamed)'}</div>
                                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px', fontFamily:'monospace' }}>
                                                                        {app.clientId ? app.clientId.slice(0,8) + '••••••••' + app.clientId.slice(-4) : '—'}
                                                                    </div>
                                                                </div>
                                                                <div style={{ display:'flex', gap:'8px', alignItems:'center' }}>
                                                                    <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background:'rgba(99,102,241,0.1)', color:'#6366f1', textTransform:'capitalize' }}>{app.clientType}</span>
                                                                    <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background:'rgba(0,171,228,0.1)', color:'#00ABE4', textTransform:'capitalize' }}>{(app.authorizationGrantType||'').replace(/-/g,' ')}</span>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── USER ROLES ── */}
                                        {adminTab === 'userroles' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>User Role Assignments</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aUserRoles.length} active assignments</div>
                                                </div>
                                                <button style={primaryBtnStyle} onClick={() => setShowAssignRole(v=>!v)}>
                                                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Shield size={14} /> Assign Role</span>
                                                </button>
                                            </div>
                                            {showAssignRole && (
                                                <div style={{ padding:'20px 24px', borderBottom:'1px solid rgba(0,171,228,0.1)', background:'rgba(0,171,228,0.02)' }}>
                                                    <div style={{ fontWeight:'600', color:'#0d1f2d', marginBottom:'14px', fontSize:'13.5px' }}>Assign Role to User</div>
                                                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'12px' }}>
                                                        <div>
                                                            <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>User</div>
                                                            <select value={assignRoleForm.userId} onChange={e=>setAssignRoleForm(f=>({...f,userId:e.target.value}))} style={inputStyle}>
                                                                <option value="">Select user…</option>
                                                                {aUsers.map(u => <option key={u.id} value={u.id}>{u.username} ({u.email})</option>)}
                                                            </select>
                                                        </div>
                                                        <div>
                                                            <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>Role</div>
                                                            <select value={assignRoleForm.roleId} onChange={e=>setAssignRoleForm(f=>({...f,roleId:e.target.value}))} style={inputStyle}>
                                                                <option value="">Select role…</option>
                                                                {aRoles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                                                            </select>
                                                        </div>
                                                    </div>
                                                    <div style={{ display:'flex', gap:'10px' }}>
                                                        <button style={primaryBtnStyle} onClick={() => { if(assignRoleForm.userId && assignRoleForm.roleId) assignRole({ variables: { userId: assignRoleForm.userId, roleId: assignRoleForm.roleId } }); }}>Assign</button>
                                                        <button style={smallBtnStyle(false)} onClick={() => setShowAssignRole(false)}>Cancel</button>
                                                    </div>
                                                </div>
                                            )}
                                            <div style={adminBodyStyle}>
                                                {aUserRoles.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No role assignments found</div>
                                                ) : (
                                                    <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'13px' }}>
                                                        <thead>
                                                            <tr style={{ borderBottom:'2px solid rgba(0,171,228,0.15)' }}>
                                                                {['User','Role','Company','Status','Assigned At',''].map(h => (
                                                                    <th key={h} style={{ padding:'8px 12px', textAlign:'left', fontWeight:'700', color:'#6b8099', fontSize:'11.5px', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {aUserRoles.map(ur => (
                                                                <tr key={ur.id} style={{ borderBottom:'1px solid rgba(0,171,228,0.07)' }}>
                                                                    <td style={{ padding:'10px 12px', color:'#0d1f2d' }}>{ur.user?.username}<div style={{ fontSize:'11px', color:'#94afc5' }}>{ur.user?.email}</div></td>
                                                                    <td style={{ padding:'10px 12px', color:'#0d1f2d', fontWeight:'600' }}>{ur.role?.name}</td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099' }}>{ur.company?.name || '—'}</td>
                                                                    <td style={{ padding:'10px 12px' }}>
                                                                        <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background: ur.isActive ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', color: ur.isActive ? '#16a34a' : '#dc2626' }}>{ur.isActive ? 'Active' : 'Inactive'}</span>
                                                                    </td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099', fontSize:'12px' }}>{ur.assignedAt ? new Date(ur.assignedAt).toLocaleDateString() : '—'}</td>
                                                                    <td style={{ padding:'10px 12px' }}>
                                                                        {ur.isActive && <button style={smallBtnStyle(true)} onClick={() => removeRoleFromUser({ variables: { userId: ur.user?.id, roleId: ur.role?.id } })}>Remove</button>}
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── SENDGRID ── */}
                                        {adminTab === 'sendgrid' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>SendGrid Domain Auths</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aSendGridAuths.length} domain authentication records</div>
                                                </div>
                                            </div>
                                            <div style={adminBodyStyle}>
                                                {aSendGridAuths.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No SendGrid domain auths found</div>
                                                ) : (
                                                    <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'13px' }}>
                                                        <thead>
                                                            <tr style={{ borderBottom:'2px solid rgba(0,171,228,0.15)' }}>
                                                                {['Domain','Customer ID','Verified','User','Created At'].map(h => (
                                                                    <th key={h} style={{ padding:'8px 12px', textAlign:'left', fontWeight:'700', color:'#6b8099', fontSize:'11.5px', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {aSendGridAuths.map(sg => (
                                                                <tr key={sg.id} style={{ borderBottom:'1px solid rgba(0,171,228,0.07)' }}>
                                                                    <td style={{ padding:'10px 12px', color:'#0d1f2d', fontWeight:'600', fontFamily:'monospace' }}>{sg.domain}</td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099', fontFamily:'monospace', fontSize:'12px' }}>{sg.customerId || '—'}</td>
                                                                    <td style={{ padding:'10px 12px' }}>
                                                                        <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background: sg.isVerified ? 'rgba(34,197,94,0.1)' : 'rgba(251,191,36,0.1)', color: sg.isVerified ? '#16a34a' : '#d97706' }}>{sg.isVerified ? 'Verified' : 'Pending'}</span>
                                                                    </td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099' }}>{sg.user?.username || '—'}</td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099', fontSize:'12px' }}>{sg.createdAt ? new Date(sg.createdAt).toLocaleDateString() : '—'}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── AUDIT LOG ── */}
                                        {adminTab === 'auditlog' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>Audit Log</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>Last {aAuditLogs.length} entries — read only</div>
                                                </div>
                                            </div>
                                            <div style={adminBodyStyle}>
                                                {aAuditLogs.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No audit log entries found</div>
                                                ) : (
                                                    <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'13px' }}>
                                                        <thead>
                                                            <tr style={{ borderBottom:'2px solid rgba(0,171,228,0.15)' }}>
                                                                {['Actor','Action','Object','Type','Timestamp'].map(h => (
                                                                    <th key={h} style={{ padding:'8px 12px', textAlign:'left', fontWeight:'700', color:'#6b8099', fontSize:'11.5px', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {aAuditLogs.map(log => {
                                                                const actionColors = { 0: { bg:'rgba(34,197,94,0.1)', color:'#16a34a', label:'Create' }, 1: { bg:'rgba(59,130,246,0.1)', color:'#2563eb', label:'Update' }, 2: { bg:'rgba(239,68,68,0.1)', color:'#dc2626', label:'Delete' } };
                                                                const ac = actionColors[log.action] || { bg:'rgba(0,171,228,0.1)', color:'#00ABE4', label:'Other' };
                                                                return (
                                                                    <tr key={log.id} style={{ borderBottom:'1px solid rgba(0,171,228,0.07)' }}>
                                                                        <td style={{ padding:'10px 12px', color:'#0d1f2d', fontWeight:'600' }}>{log.actorUsername}</td>
                                                                        <td style={{ padding:'10px 12px' }}><span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background:ac.bg, color:ac.color }}>{ac.label}</span></td>
                                                                        <td style={{ padding:'10px 12px', color:'#0d1f2d', maxWidth:'200px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{log.objectRepr}</td>
                                                                        <td style={{ padding:'10px 12px', color:'#6b8099' }}>{log.contentTypeName}</td>
                                                                        <td style={{ padding:'10px 12px', color:'#6b8099', fontSize:'12px' }}>{log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}</td>
                                                                    </tr>
                                                                );
                                                            })}
                                                        </tbody>
                                                    </table>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── ACCESS TOKENS ── */}
                                        {adminTab === 'accesstokens' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>OAuth Access Tokens</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aAccessTokens.length} tokens — read only</div>
                                                </div>
                                            </div>
                                            <div style={adminBodyStyle}>
                                                {aAccessTokens.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No access tokens found</div>
                                                ) : (
                                                    <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'13px' }}>
                                                        <thead>
                                                            <tr style={{ borderBottom:'2px solid rgba(0,171,228,0.15)' }}>
                                                                {['User','Token','Expires','Scope'].map(h => (
                                                                    <th key={h} style={{ padding:'8px 12px', textAlign:'left', fontWeight:'700', color:'#6b8099', fontSize:'11.5px', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {aAccessTokens.map(tok => (
                                                                <tr key={tok.id} style={{ borderBottom:'1px solid rgba(0,171,228,0.07)' }}>
                                                                    <td style={{ padding:'10px 12px', color:'#0d1f2d', fontWeight:'600' }}>{tok.userUsername}</td>
                                                                    <td style={{ padding:'10px 12px', fontFamily:'monospace', color:'#6b8099', fontSize:'12px' }}>{tok.tokenMasked}</td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099', fontSize:'12px' }}>{tok.expires ? new Date(tok.expires).toLocaleString() : '—'}</td>
                                                                    <td style={{ padding:'10px 12px', color:'#6b8099', fontSize:'12px' }}>{tok.scope || '—'}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                        {/* ── PERMISSIONS ── */}
                                        {adminTab === 'permissions' && (
                                        <div style={adminCardStyle}>
                                            <div style={adminHeaderStyle}>
                                                <div>
                                                    <div style={{ fontWeight:'700', color:'#0d1f2d', fontSize:'15px' }}>Permissions</div>
                                                    <div style={{ fontSize:'12px', color:'#6b8099', marginTop:'2px' }}>{aPerms.length} permissions defined</div>
                                                </div>
                                                <button style={primaryBtnStyle} onClick={() => setShowCreatePermission(v=>!v)}>
                                                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}><Lock size={14} /> Create Permission</span>
                                                </button>
                                            </div>
                                            {showCreatePermission && (
                                                <div style={{ padding:'20px 24px', borderBottom:'1px solid rgba(0,171,228,0.1)', background:'rgba(0,171,228,0.02)' }}>
                                                    <div style={{ fontWeight:'600', color:'#0d1f2d', marginBottom:'14px', fontSize:'13.5px' }}>New Permission</div>
                                                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginBottom:'12px' }}>
                                                        {[['code','Code','e.g. users.manage_roles'],['name','Name','Human-readable name'],['category','Category','e.g. Users'],['description','Description','Optional description']].map(([k,label,ph]) => (
                                                            <div key={k}>
                                                                <div style={{ fontSize:'11.5px', fontWeight:'700', color:'#6b8099', marginBottom:'5px', textTransform:'uppercase', letterSpacing:'0.06em' }}>{label}</div>
                                                                <input placeholder={ph} value={newPermissionForm[k]||''} onChange={e=>setNewPermissionForm(f=>({...f,[k]:e.target.value}))} style={inputStyle} />
                                                            </div>
                                                        ))}
                                                    </div>
                                                    <div style={{ display:'flex', gap:'10px' }}>
                                                        <button style={primaryBtnStyle} onClick={() => { if(newPermissionForm.code && newPermissionForm.name) createPermission({ variables: { code: newPermissionForm.code, name: newPermissionForm.name, category: newPermissionForm.category, description: newPermissionForm.description } }); }}>Create</button>
                                                        <button style={smallBtnStyle(false)} onClick={() => setShowCreatePermission(false)}>Cancel</button>
                                                    </div>
                                                </div>
                                            )}
                                            <div style={adminBodyStyle}>
                                                {aPerms.length === 0 ? (
                                                    <div style={{ textAlign:'center', padding:'30px', color:'#94afc5' }}>No permissions found</div>
                                                ) : (
                                                    <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'13px' }}>
                                                        <thead>
                                                            <tr style={{ borderBottom:'2px solid rgba(0,171,228,0.15)' }}>
                                                                {['Code','Name','Category','Status',''].map(h => (
                                                                    <th key={h} style={{ padding:'8px 12px', textAlign:'left', fontWeight:'700', color:'#6b8099', fontSize:'11.5px', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {aPerms.map(p => (
                                                                <tr key={p.id} style={{ borderBottom:'1px solid rgba(0,171,228,0.07)' }}>
                                                                    <td style={{ padding:'10px 12px', fontFamily:'monospace', color:'#0d1f2d', fontSize:'12px' }}>{p.code}</td>
                                                                    <td style={{ padding:'10px 12px', color:'#0d1f2d', fontWeight:'600' }}>{p.name}</td>
                                                                    <td style={{ padding:'10px 12px' }}>
                                                                        <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background:'rgba(0,171,228,0.1)', color:'#00ABE4' }}>{p.category || '—'}</span>
                                                                    </td>
                                                                    <td style={{ padding:'10px 12px' }}>
                                                                        <span style={{ padding:'3px 8px', borderRadius:'6px', fontSize:'11.5px', fontWeight:'700', background: p.isActive !== false ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', color: p.isActive !== false ? '#16a34a' : '#dc2626' }}>{p.isActive !== false ? 'Active' : 'Inactive'}</span>
                                                                    </td>
                                                                    <td style={{ padding:'10px 12px' }}>
                                                                        <button style={smallBtnStyle(true)} onClick={() => { if(window.confirm('Delete this permission?')) deletePermission({ variables: { id: p.id } }); }}>Delete</button>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                )}
                                            </div>
                                        </div>
                                        )}

                                    </div>
                                    );
                                })()}

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
                                                    href={`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}${att.url}?token=${localStorage.getItem('access_token') || ''}`}
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
