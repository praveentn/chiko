// src/components/ProtectedRoute.js - Updated with PermissionGate
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Shield, Lock, AlertTriangle } from 'lucide-react';
import './ProtectedRoute.css';

const ProtectedRoute = ({ 
  children, 
  isAuthenticated, 
  requiredRole = null,
  requiredPermission = null,
  userRole = null,
  userPermissions = [],
  fallbackPath = '/login'
}) => {
  const location = useLocation();

  // Check authentication
  if (!isAuthenticated) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }

  // Check role-based access
  if (requiredRole) {
    if (Array.isArray(requiredRole)) {
      if (!requiredRole.includes(userRole)) {
        return <AccessDenied reason="role" required={requiredRole} current={userRole} />;
      }
    } else if (userRole !== requiredRole) {
      return <AccessDenied reason="role" required={requiredRole} current={userRole} />;
    }
  }

  // Check permission-based access
  if (requiredPermission) {
    if (Array.isArray(requiredPermission)) {
      const hasAnyPermission = requiredPermission.some(permission => 
        userPermissions.includes(permission)
      );
      if (!hasAnyPermission) {
        return <AccessDenied reason="permission" required={requiredPermission} />;
      }
    } else if (!userPermissions.includes(requiredPermission)) {
      return <AccessDenied reason="permission" required={requiredPermission} />;
    }
  }

  return children;
};

// Permission Gate Component - for conditional rendering based on roles/permissions
export const PermissionGate = ({ 
  children, 
  userRole = null,
  userPermissions = [],
  requiredRoles = null,
  requiredPermissions = null,
  fallback = null,
  requireAll = false // whether to require ALL roles/permissions or just one
}) => {
  const hasRequiredRole = () => {
    if (!requiredRoles) return true;
    
    if (Array.isArray(requiredRoles)) {
      return requireAll 
        ? requiredRoles.every(role => userRole === role)
        : requiredRoles.includes(userRole);
    }
    
    return userRole === requiredRoles;
  };

  const hasRequiredPermission = () => {
    if (!requiredPermissions) return true;
    
    if (Array.isArray(requiredPermissions)) {
      return requireAll
        ? requiredPermissions.every(permission => userPermissions.includes(permission))
        : requiredPermissions.some(permission => userPermissions.includes(permission));
    }
    
    return userPermissions.includes(requiredPermissions);
  };

  const hasAccess = hasRequiredRole() && hasRequiredPermission();

  if (!hasAccess) {
    return fallback || null;
  }

  return children;
};

// Access Denied Component
const AccessDenied = ({ reason, required, current }) => {
  const getErrorMessage = () => {
    switch (reason) {
      case 'role':
        return {
          title: 'Access Denied',
          message: `This page requires ${Array.isArray(required) ? required.join(' or ') : required} role.`,
          detail: current ? `Your current role: ${current}` : 'Please contact your administrator for access.',
          icon: Shield
        };
      case 'permission':
        return {
          title: 'Insufficient Permissions',
          message: `You don't have the required permissions to access this page.`,
          detail: `Required: ${Array.isArray(required) ? required.join(', ') : required}`,
          icon: Lock
        };
      default:
        return {
          title: 'Access Restricted',
          message: 'You are not authorized to view this page.',
          detail: 'Please contact your administrator if you believe this is an error.',
          icon: AlertTriangle
        };
    }
  };

  const error = getErrorMessage();
  const Icon = error.icon;

  return (
    <div className="access-denied">
      <div className="access-denied-content">
        <div className="access-denied-icon">
          <Icon size={64} />
        </div>
        <h1 className="access-denied-title">{error.title}</h1>
        <p className="access-denied-message">{error.message}</p>
        <p className="access-denied-detail">{error.detail}</p>
        <div className="access-denied-actions">
          <button 
            onClick={() => window.history.back()} 
            className="btn btn-secondary"
          >
            Go Back
          </button>
          <button 
            onClick={() => window.location.href = '/dashboard'} 
            className="btn btn-primary"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProtectedRoute;