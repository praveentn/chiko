// src/components/Layout.js
import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Home,
  Brain,
  Users,
  Bot,
  Workflow,
  Wrench,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  Shield,
  ChevronDown
} from 'lucide-react';
import './Layout.css';

const Layout = ({ user, onLogout }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const navigationItems = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: Home,
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      name: 'Models',
      path: '/models',
      icon: Brain,
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      name: 'Personas',
      path: '/personas',
      icon: Users,
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      name: 'Agents',
      path: '/agents',
      icon: Bot,
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      name: 'Workflows',
      path: '/workflows',
      icon: Workflow,
      roles: ['Admin', 'Developer', 'Business User']
    },
    {
      name: 'Tools',
      path: '/tools',
      icon: Wrench,
      roles: ['Admin', 'Developer']
    },
    {
      name: 'Admin',
      path: '/admin',
      icon: Shield,
      roles: ['Admin']
    }
  ];

  const filteredNavigation = navigationItems.filter(item =>
    !item.roles || item.roles.includes(user?.role)
  );

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  const isActiveRoute = (path) => {
    return location.pathname.startsWith(path);
  };

  return (
    <div className="layout">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo">
            <Bot className="logo-icon" />
            <span className={`logo-text ${!sidebarOpen ? 'hidden' : ''}`}>
              QueryForge
            </span>
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="sidebar-toggle"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="sidebar-nav">
          <ul>
            {filteredNavigation.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.name}>
                  <Link
                    to={item.path}
                    className={`nav-link ${isActiveRoute(item.path) ? 'active' : ''}`}
                    title={!sidebarOpen ? item.name : ''}
                  >
                    <Icon size={20} />
                    <span className={`nav-text ${!sidebarOpen ? 'hidden' : ''}`}>
                      {item.name}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-left">
            <h1 className="page-title">
              {/* This will be set by individual pages */}
            </h1>
          </div>

          <div className="header-right">
            {/* User Menu */}
            <div className="user-menu">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="user-menu-button"
              >
                <User size={20} />
                <span className="user-name">
                  {user?.first_name} {user?.last_name}
                </span>
                <ChevronDown size={16} />
              </button>

              {userMenuOpen && (
                <div className="user-menu-dropdown">
                  <div className="user-info">
                    <div className="user-name-full">
                      {user?.first_name} {user?.last_name}
                    </div>
                    <div className="user-email">{user?.email}</div>
                    <div className="user-role">{user?.role}</div>
                  </div>
                  
                  <div className="menu-divider"></div>
                  
                  <Link to="/profile" className="menu-item">
                    <User size={16} />
                    Profile Settings
                  </Link>
                  
                  <Link to="/settings" className="menu-item">
                    <Settings size={16} />
                    Preferences
                  </Link>
                  
                  <div className="menu-divider"></div>
                  
                  <button onClick={handleLogout} className="menu-item logout">
                    <LogOut size={16} />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="page-content">
          <Outlet />
        </main>
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};

export default Layout;