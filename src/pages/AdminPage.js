// src/pages/AdminPage.js
import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  Database,
  Users,
  Settings,
  Activity,
  BarChart3,
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap
} from 'lucide-react';

import SqlExecutor from '../components/SqlExecutor';
import LoadingSpinner from '../components/LoadingSpinner';
import authService from '../services/authService';
import './AdminPage.css';

const AdminPage = ({ user }) => {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const location = useLocation();

  const adminTabs = [
    {
      id: 'sql',
      name: 'SQL Console',
      icon: Database,
      path: '/admin',
      component: SqlExecutor
    },
    {
      id: 'users',
      name: 'User Management',
      icon: Users,
      path: '/admin/users',
      component: UserManagement
    },
    {
      id: 'stats',
      name: 'System Stats',
      icon: BarChart3,
      path: '/admin/stats',
      component: SystemStats
    },
    {
      id: 'activity',
      name: 'Activity Logs',
      icon: Activity,
      path: '/admin/activity',
      component: ActivityLogs
    },
    {
      id: 'settings',
      name: 'Settings',
      icon: Settings,
      path: '/admin/settings',
      component: SystemSettings
    }
  ];

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    setIsLoading(true);
    try {
      const [statsResponse, usersResponse] = await Promise.all([
        authService.apiCall('/admin/system/stats'),
        authService.apiCall('/admin/users')
      ]);

      if (statsResponse?.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData.stats);
      }

      if (usersResponse?.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.users || []);
      }
    } catch (error) {
      console.error('Failed to load admin data:', error);
      setError('Failed to load admin data');
    } finally {
      setIsLoading(false);
    }
  };

  const isActiveTab = (path) => {
    if (path === '/admin') {
      return location.pathname === '/admin';
    }
    return location.pathname.startsWith(path);
  };

  if (isLoading) {
    return (
      <div className="admin-loading">
        <LoadingSpinner size="large" />
        <p>Loading admin dashboard...</p>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <div className="admin-title">
          <Shield size={24} />
          <h1>System Administration</h1>
        </div>
        {stats && (
          <div className="admin-quick-stats">
            <div className="quick-stat">
              <div className="stat-value">{stats.users?.total || 0}</div>
              <div className="stat-label">Total Users</div>
            </div>
            <div className="quick-stat">
              <div className="stat-value">{stats.users?.active || 0}</div>
              <div className="stat-label">Active Users</div>
            </div>
            <div className="quick-stat warning">
              <div className="stat-value">{stats.users?.pending_approval || 0}</div>
              <div className="stat-label">Pending Approval</div>
            </div>
          </div>
        )}
      </div>

      <div className="admin-content">
        <div className="admin-sidebar">
          <nav className="admin-nav">
            {adminTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <Link
                  key={tab.id}
                  to={tab.path}
                  className={`admin-nav-link ${isActiveTab(tab.path) ? 'active' : ''}`}
                >
                  <Icon size={20} />
                  <span>{tab.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="admin-main">
          <Routes>
            <Route path="/" element={<SqlExecutor />} />
            <Route path="/users" element={<UserManagement users={users} onUsersChange={loadAdminData} />} />
            <Route path="/stats" element={<SystemStats stats={stats} />} />
            <Route path="/activity" element={<ActivityLogs />} />
            <Route path="/settings" element={<SystemSettings />} />
          </Routes>
        </div>
      </div>
    </div>
  );
};

// User Management Component
function UserManagement({ users, onUsersChange }) {
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = !roleFilter || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleApproveUser = async (userId) => {
    setIsLoading(true);
    try {
      const response = await authService.apiCall(`/admin/users/${userId}/approve`, {
        method: 'POST'
      });

      if (response?.ok) {
        onUsersChange();
      } else {
        throw new Error('Failed to approve user');
      }
    } catch (error) {
      console.error('Error approving user:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    setIsLoading(true);
    try {
      const response = await authService.apiCall(`/admin/users/${userId}/role`, {
        method: 'PUT',
        body: JSON.stringify({ role_name: newRole })
      });

      if (response?.ok) {
        onUsersChange();
      } else {
        throw new Error('Failed to update role');
      }
    } catch (error) {
      console.error('Error updating role:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getUserStatusBadge = (user) => {
    if (!user.is_active) {
      return <span className="status-badge inactive">Inactive</span>;
    }
    if (!user.is_approved) {
      return <span className="status-badge pending">Pending</span>;
    }
    return <span className="status-badge active">Active</span>;
  };

  return (
    <div className="user-management">
      <div className="user-management-header">
        <h2>User Management</h2>
        <div className="user-filters">
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="role-filter"
          >
            <option value="">All Roles</option>
            <option value="Admin">Admin</option>
            <option value="Developer">Developer</option>
            <option value="Business User">Business User</option>
          </select>
        </div>
      </div>

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.id}>
                <td>
                  <div className="user-info">
                    <div className="user-avatar">
                      {user.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="user-name">{user.full_name}</div>
                      <div className="user-id">ID: {user.id}</div>
                    </div>
                  </div>
                </td>
                <td>{user.email}</td>
                <td>
                  <select
                    value={user.role || ''}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                    className="role-select"
                    disabled={isLoading}
                  >
                    <option value="Business User">Business User</option>
                    <option value="Developer">Developer</option>
                    <option value="Admin">Admin</option>
                  </select>
                </td>
                <td>{getUserStatusBadge(user)}</td>
                <td>
                  {user.last_login ? 
                    new Date(user.last_login).toLocaleDateString() : 
                    'Never'
                  }
                </td>
                <td>
                  <div className="user-actions">
                    {!user.is_approved && (
                      <button
                        onClick={() => handleApproveUser(user.id)}
                        className="approve-btn"
                        disabled={isLoading}
                      >
                        <CheckCircle size={16} />
                        Approve
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// System Stats Component
function SystemStats({ stats }) {
  if (!stats) {
    return (
      <div className="stats-loading">
        <LoadingSpinner />
        <p>Loading system statistics...</p>
      </div>
    );
  }

  return (
    <div className="system-stats">
      <h2>System Statistics</h2>
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <Users size={24} />
          </div>
          <div className="stat-content">
            <h3>Users</h3>
            <div className="stat-number">{stats.users?.total || 0}</div>
            <div className="stat-details">
              <span className="stat-detail">
                <CheckCircle size={14} />
                {stats.users?.active || 0} active
              </span>
              <span className="stat-detail warning">
                <Clock size={14} />
                {stats.users?.pending_approval || 0} pending
              </span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Activity size={24} />
          </div>
          <div className="stat-content">
            <h3>Recent Activity</h3>
            <div className="stat-number">{stats.recent_activity?.last_24h || 0}</div>
            <div className="stat-details">
              <span className="stat-detail">
                <Zap size={14} />
                Last 24 hours
              </span>
              <span className="stat-detail">
                {stats.recent_activity?.last_7d || 0} this week
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Activity Logs Component
function ActivityLogs() {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    loadActivityLogs();
  }, [currentPage]);

  const loadActivityLogs = async () => {
    setIsLoading(true);
    try {
      const response = await authService.apiCall(`/admin/activity?page=${currentPage}`);
      if (response?.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      }
    } catch (error) {
      console.error('Failed to load activity logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="activity-logs">
      <h2>Activity Logs</h2>
      
      {isLoading ? (
        <div className="logs-loading">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="logs-table-container">
          <table className="logs-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                  <td>{log.user_email || 'System'}</td>
                  <td>{log.action}</td>
                  <td>{log.resource_type || '-'}</td>
                  <td>
                    {log.success ? (
                      <span className="status-badge success">Success</span>
                    ) : (
                      <span className="status-badge error">Error</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// System Settings Component
function SystemSettings() {
  const [settings, setSettings] = useState({
    maintenance_mode: false,
    registration_enabled: true,
    max_file_size: 100,
    session_timeout: 24
  });

  return (
    <div className="system-settings">
      <h2>System Settings</h2>
      
      <div className="settings-form">
        <div className="setting-group">
          <h3>General Settings</h3>
          
          <div className="setting-item">
            <label className="setting-label">
              <input
                type="checkbox"
                checked={settings.maintenance_mode}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  maintenance_mode: e.target.checked
                }))}
              />
              Maintenance Mode
            </label>
            <p className="setting-description">
              Prevents non-admin users from accessing the system
            </p>
          </div>

          <div className="setting-item">
            <label className="setting-label">
              <input
                type="checkbox"
                checked={settings.registration_enabled}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  registration_enabled: e.target.checked
                }))}
              />
              Enable User Registration
            </label>
            <p className="setting-description">
              Allow new users to create accounts
            </p>
          </div>
        </div>

        <div className="setting-group">
          <h3>Limits & Timeouts</h3>
          
          <div className="setting-item">
            <label className="setting-label">
              Maximum File Size (MB)
              <input
                type="number"
                value={settings.max_file_size}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  max_file_size: parseInt(e.target.value)
                }))}
                className="setting-input"
              />
            </label>
          </div>

          <div className="setting-item">
            <label className="setting-label">
              Session Timeout (hours)
              <input
                type="number"
                value={settings.session_timeout}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  session_timeout: parseInt(e.target.value)
                }))}
                className="setting-input"
              />
            </label>
          </div>
        </div>

        <div className="settings-actions">
          <button className="save-settings-btn">
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminPage;