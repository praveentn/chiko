// src/pages/DashboardPage.js
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  Bot,
  Brain,
  Clock,
  DollarSign,
  Plus,
  TrendingUp,
  Users,
  Workflow,
  Zap,
  AlertCircle,
  CheckCircle,
  PlayCircle
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import authService from '../services/authService';
import './DashboardPage.css';

const DashboardPage = ({ user }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const response = await authService.apiCall('/dashboard/stats');
      if (response?.ok) {
        const data = await response.json();
        setDashboardData(data);
        setRecentActivity(data.recent_activity || []);
      } else {
        throw new Error('Failed to load dashboard data');
      }
    } catch (error) {
      console.error('Dashboard error:', error);
      setError('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const quickActions = [
    {
      title: 'Create Agent',
      description: 'Build a new AI agent',
      icon: Bot,
      path: '/agents/create',
      color: 'blue',
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      title: 'New Workflow',
      description: 'Design a workflow',
      icon: Workflow,
      path: '/workflows/create',
      color: 'green',
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      title: 'Add Model',
      description: 'Register a new model',
      icon: Brain,
      path: '/models/create',
      color: 'purple',
      roles: ['Admin', 'Developer']
    },
    {
      title: 'Create Persona',
      description: 'Define AI personality',
      icon: Users,
      path: '/personas/create',
      color: 'orange',
      roles: ['Admin', 'Developer', 'Business User']
    }
  ];

  const filteredQuickActions = quickActions.filter(action => 
    action.roles.includes(user?.role)
  );

  if (isLoading) {
    return (
      <div className="dashboard-loading">
        <LoadingSpinner size="large" text="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <AlertCircle size={48} />
        <h3>Failed to load dashboard</h3>
        <p>{error}</p>
        <button onClick={loadDashboardData} className="retry-button">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Welcome Section */}
      <div className="dashboard-header">
        <div className="welcome-section">
          <h1 className="welcome-title">
            {getGreeting()}, {user?.first_name}! 👋
          </h1>
          <p className="welcome-subtitle">
            Welcome to your AI workbench. What would you like to build today?
          </p>
        </div>
        
        <div className="user-badge">
          <span className="user-role">{user?.role}</span>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2 className="section-title">Quick Actions</h2>
        <div className="quick-actions-grid">
          {filteredQuickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <Link
                key={index}
                to={action.path}
                className={`quick-action-card ${action.color}`}
              >
                <div className="action-icon">
                  <Icon size={24} />
                </div>
                <div className="action-content">
                  <h3>{action.title}</h3>
                  <p>{action.description}</p>
                </div>
                <div className="action-arrow">
                  <Plus size={16} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="dashboard-content">
        {/* Stats Overview */}
        <div className="stats-section">
          <h2 className="section-title">Overview</h2>
          <div className="stats-grid">
            <StatCard
              title="Total Agents"
              value={dashboardData?.stats?.agents?.total || 0}
              change="+12%"
              trend="up"
              icon={Bot}
              color="blue"
            />
            <StatCard
              title="Active Workflows"
              value={dashboardData?.stats?.workflows?.active || 0}
              change="+8%"
              trend="up"
              icon={Workflow}
              color="green"
            />
            <StatCard
              title="Executions Today"
              value={dashboardData?.stats?.executions?.today || 0}
              change="+25%"
              trend="up"
              icon={PlayCircle}
              color="purple"
            />
            <StatCard
              title="Cost This Month"
              value={`$${(dashboardData?.stats?.cost?.this_month || 0).toFixed(2)}`}
              change="-5%"
              trend="down"
              icon={DollarSign}
              color="orange"
            />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="main-content-grid">
          {/* Recent Activity */}
          <div className="activity-panel">
            <div className="panel-header">
              <h3>Recent Activity</h3>
              <Link to="/admin/activity" className="view-all-link">
                View All
              </Link>
            </div>
            <div className="activity-list">
              {recentActivity.length > 0 ? (
                recentActivity.slice(0, 10).map((activity, index) => (
                  <ActivityItem key={index} activity={activity} />
                ))
              ) : (
                <div className="empty-state">
                  <Activity size={32} />
                  <p>No recent activity</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="quick-stats-panel">
            <div className="panel-header">
              <h3>Quick Stats</h3>
            </div>
            <div className="quick-stats-list">
              <QuickStat
                label="Models Available"
                value={dashboardData?.stats?.models?.approved || 0}
                icon={Brain}
              />
              <QuickStat
                label="Personas Created"
                value={dashboardData?.stats?.personas?.total || 0}
                icon={Users}
              />
              <QuickStat
                label="Tools Registered"
                value={dashboardData?.stats?.tools?.active || 0}
                icon={Zap}
              />
              <QuickStat
                label="Success Rate"
                value={`${dashboardData?.stats?.success_rate || 0}%`}
                icon={CheckCircle}
              />
            </div>
          </div>
        </div>

        {/* Recent Items */}
        <div className="recent-items-section">
          <div className="recent-grid">
            <RecentItemsPanel
              title="Recent Agents"
              items={dashboardData?.recent?.agents || []}
              type="agents"
              icon={Bot}
            />
            <RecentItemsPanel
              title="Recent Workflows"
              items={dashboardData?.recent?.workflows || []}
              type="workflows"
              icon={Workflow}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

// Stat Card Component
const StatCard = ({ title, value, change, trend, icon: Icon, color }) => (
  <div className={`stat-card ${color}`}>
    <div className="stat-icon">
      <Icon size={24} />
    </div>
    <div className="stat-content">
      <div className="stat-value">{value}</div>
      <div className="stat-title">{title}</div>
      <div className={`stat-change ${trend}`}>
        <TrendingUp size={14} />
        {change}
      </div>
    </div>
  </div>
);

// Activity Item Component
const ActivityItem = ({ activity }) => {
  const getActivityIcon = (action) => {
    switch (action) {
      case 'agent_created':
      case 'agent_executed':
        return Bot;
      case 'workflow_created':
      case 'workflow_executed':
        return Workflow;
      case 'model_created':
        return Brain;
      case 'user_login':
        return Users;
      default:
        return Activity;
    }
  };

  const getActivityColor = (action) => {
    if (action.includes('created')) return 'green';
    if (action.includes('executed')) return 'blue';
    if (action.includes('failed')) return 'red';
    return 'gray';
  };

  const Icon = getActivityIcon(activity.action);
  const color = getActivityColor(activity.action);

  return (
    <div className="activity-item">
      <div className={`activity-icon ${color}`}>
        <Icon size={16} />
      </div>
      <div className="activity-content">
        <div className="activity-description">
          {activity.description || activity.action}
        </div>
        <div className="activity-time">
          <Clock size={12} />
          {new Date(activity.created_at).toLocaleString()}
        </div>
      </div>
    </div>
  );
};

// Quick Stat Component
const QuickStat = ({ label, value, icon: Icon }) => (
  <div className="quick-stat">
    <div className="quick-stat-icon">
      <Icon size={20} />
    </div>
    <div className="quick-stat-content">
      <div className="quick-stat-value">{value}</div>
      <div className="quick-stat-label">{label}</div>
    </div>
  </div>
);

// Recent Items Panel Component
const RecentItemsPanel = ({ title, items, type, icon: Icon }) => (
  <div className="recent-items-panel">
    <div className="panel-header">
      <h3>
        <Icon size={20} />
        {title}
      </h3>
      <Link to={`/${type}`} className="view-all-link">
        View All
      </Link>
    </div>
    <div className="recent-items-list">
      {items.length > 0 ? (
        items.slice(0, 5).map((item, index) => (
          <div key={index} className="recent-item">
            <div className="recent-item-info">
              <div className="recent-item-name">{item.name}</div>
              <div className="recent-item-meta">
                Created {new Date(item.created_at).toLocaleDateString()}
              </div>
            </div>
            <div className={`recent-item-status ${item.status || 'active'}`}>
              {item.status || 'Active'}
            </div>
          </div>
        ))
      ) : (
        <div className="empty-state small">
          <Icon size={24} />
          <p>No {type} yet</p>
        </div>
      )}
    </div>
  </div>
);

export default DashboardPage;