// src/pages/WorkflowsPage.js
import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Workflow,
  Edit,
  Trash2,
  Eye,
  Play,
  Pause,
  Copy,
  Check,
  Globe,
  Lock,
  Users as Team,
  AlertCircle,
  CheckCircle,
  XCircle,
  Settings,
  Activity,
  Zap,
  GitBranch,
  Clock
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './WorkflowsPage.css';

const WorkflowsPage = ({ user }) => {
  const [workflows, setWorkflows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  useEffect(() => {
    loadWorkflows();
  }, [currentPage, searchTerm, statusFilter, typeFilter]);

  const loadWorkflows = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage,
        per_page: 20,
        ...(searchTerm && { search: searchTerm }),
        ...(statusFilter && { status: statusFilter }),
        ...(typeFilter && { type: typeFilter })
      });

      const response = await authService.apiCall(`/workflows?${params}`);
      if (response?.ok) {
        const data = await response.json();
        setWorkflows(data.workflows || []);
        setPagination(data.pagination);
      } else {
        throw new Error('Failed to load workflows');
      }
    } catch (error) {
      console.error('Failed to load workflows:', error);
      setError('Failed to load workflows');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateWorkflow = () => {
    setShowCreateModal(true);
  };

  const handleEditWorkflow = (workflow) => {
    setSelectedWorkflow(workflow);
    setShowCreateModal(true);
  };

  const handleDeleteWorkflow = async (workflowId) => {
    if (window.confirm('Are you sure you want to delete this workflow?')) {
      try {
        const response = await authService.apiCall(`/workflows/${workflowId}`, {
          method: 'DELETE'
        });
        
        if (response?.ok) {
          setWorkflows(workflows.filter(workflow => workflow.id !== workflowId));
        } else {
          throw new Error('Failed to delete workflow');
        }
      } catch (error) {
        console.error('Delete workflow error:', error);
        setError('Failed to delete workflow');
      }
    }
  };

  const handleExecuteWorkflow = (workflow) => {
    setSelectedWorkflow(workflow);
    setShowExecuteModal(true);
  };

  const handleToggleWorkflowStatus = async (workflowId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/workflows/${workflowId}/toggle`, {
        method: 'PUT'
      });
      
      if (response?.ok) {
        setWorkflows(workflows.map(workflow => 
          workflow.id === workflowId 
            ? { ...workflow, is_active: !currentStatus }
            : workflow
        ));
      } else {
        throw new Error('Failed to toggle workflow status');
      }
    } catch (error) {
      console.error('Toggle workflow status error:', error);
      setError('Failed to toggle workflow status');
    }
  };

  const handleDuplicateWorkflow = async (workflow) => {
    try {
      const response = await authService.apiCall(`/workflows/${workflow.id}/duplicate`, {
        method: 'POST'
      });
      
      if (response?.ok) {
        const data = await response.json();
        setWorkflows([data.workflow, ...workflows]);
      } else {
        throw new Error('Failed to duplicate workflow');
      }
    } catch (error) {
      console.error('Duplicate workflow error:', error);
      setError('Failed to duplicate workflow');
    }
  };

  const handleViewDetails = (workflow) => {
    setSelectedWorkflow(workflow);
    setShowDetailsModal(true);
  };

  if (isLoading) {
    return (
      <div className="page-loading">
        <LoadingSpinner size="large" />
        <p>Loading workflows...</p>
      </div>
    );
  }

  return (
    <div className="workflows-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1 className="page-title">
              <Workflow className="page-icon" />
              Workflows
            </h1>
            <p className="page-subtitle">
              Design and manage your AI workflow automations
            </p>
          </div>
          <PermissionGate 
            userRole={user?.role} 
            requiredRoles={['Admin', 'Developer', 'Business User']}
          >
            <button 
              className="btn btn-primary"
              onClick={handleCreateWorkflow}
            >
              <Plus size={20} />
              Create Workflow
            </button>
          </PermissionGate>
        </div>
      </div>

      <div className="page-content">
        {/* Filters */}
        <div className="filters-section">
          <div className="search-box">
            <Search className="search-icon" />
            <input
              type="text"
              placeholder="Search workflows..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-controls">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="approved">Approved</option>
              <option value="pending">Pending</option>
            </select>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Types</option>
              <option value="sequential">Sequential</option>
              <option value="parallel">Parallel</option>
              <option value="conditional">Conditional</option>
              <option value="loop">Loop</option>
            </select>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            <AlertCircle size={20} />
            <span>{error}</span>
            <button 
              onClick={() => setError(null)}
              className="error-close"
            >
              <XCircle size={16} />
            </button>
          </div>
        )}

        {/* Workflows Grid */}
        <div className="workflows-grid">
          {workflows.length > 0 ? (
            workflows.map((workflow) => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                user={user}
                onEdit={handleEditWorkflow}
                onDelete={handleDeleteWorkflow}
                onExecute={handleExecuteWorkflow}
                onToggleStatus={handleToggleWorkflowStatus}
                onDuplicate={handleDuplicateWorkflow}
                onViewDetails={handleViewDetails}
              />
            ))
          ) : (
            <div className="empty-state">
              <Workflow size={64} />
              <h3>No workflows found</h3>
              <p>Create your first workflow to automate AI tasks</p>
              <button 
                className="btn btn-primary"
                onClick={handleCreateWorkflow}
              >
                <Plus size={20} />
                Create Workflow
              </button>
            </div>
          )}
        </div>

        {/* Pagination */}
        {pagination && pagination.total_pages > 1 && (
          <div className="pagination">
            <button
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={!pagination.has_prev}
              className="pagination-btn"
            >
              Previous
            </button>
            <span className="pagination-info">
              Page {currentPage} of {pagination.total_pages}
            </span>
            <button
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={!pagination.has_next}
              className="pagination-btn"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Workflow Card Component
const WorkflowCard = ({ workflow, user, onEdit, onDelete, onExecute, onToggleStatus, onDuplicate, onViewDetails }) => {
  const canEdit = user?.role === 'Admin' || workflow.created_by === user?.id;

  const getStatusIcon = (isActive, isApproved) => {
    if (!isApproved) return <XCircle size={16} className="status-icon pending" />;
    if (isActive) return <CheckCircle size={16} className="status-icon active" />;
    return <Pause size={16} className="status-icon inactive" />;
  };

  const getWorkflowTypeIcon = (type) => {
    switch (type) {
      case 'sequential':
        return <GitBranch size={16} className="type-icon sequential" />;
      case 'parallel':
        return <Zap size={16} className="type-icon parallel" />;
      case 'conditional':
        return <Settings size={16} className="type-icon conditional" />;
      case 'loop':
        return <Clock size={16} className="type-icon loop" />;
      default:
        return <Workflow size={16} className="type-icon default" />;
    }
  };

  return (
    <div className="workflow-card">
      <div className="workflow-card-header">
        <div className="workflow-info">
          <div className="workflow-meta">
            {getStatusIcon(workflow.is_active, workflow.is_approved)}
            <span className="status-text">
              {!workflow.is_approved ? 'Pending' : workflow.is_active ? 'Active' : 'Inactive'}
            </span>
            {getWorkflowTypeIcon(workflow.type)}
            <span className="type-text">{workflow.type || 'Basic'}</span>
          </div>
          <h3 className="workflow-name">{workflow.name}</h3>
          <p className="workflow-description">
            {workflow.description || 'No description provided'}
          </p>
        </div>
      </div>

      <div className="workflow-card-body">
        <div className="workflow-details">
          <div className="detail-item">
            <span className="detail-label">Steps:</span>
            <span className="detail-value">{workflow.step_count || 0}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Executions:</span>
            <span className="detail-value">{workflow.execution_count || 0}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Success Rate:</span>
            <span className="detail-value">
              {workflow.success_rate ? `${workflow.success_rate.toFixed(1)}%` : 'N/A'}
            </span>
          </div>
        </div>

        {workflow.tags && workflow.tags.length > 0 && (
          <div className="workflow-tags">
            {workflow.tags.slice(0, 3).map((tag, index) => (
              <span key={index} className="tag">
                {tag}
              </span>
            ))}
            {workflow.tags.length > 3 && (
              <span className="tag-more">+{workflow.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>

      <div className="workflow-card-footer">
        <div className="workflow-meta">
          <span className="created-by">
            Created by {workflow.created_by_name || 'Unknown'}
          </span>
          <span className="created-date">
            {new Date(workflow.created_at).toLocaleDateString()}
          </span>
        </div>

        <div className="workflow-actions">
          <button
            onClick={() => onViewDetails(workflow)}
            className="action-btn secondary"
            title="View Details"
          >
            <Eye size={16} />
          </button>
          
          <button
            onClick={() => onExecute(workflow)}
            className="action-btn primary"
            title="Execute Workflow"
            disabled={!workflow.is_active || !workflow.is_approved}
          >
            <Play size={16} />
          </button>

          {canEdit && (
            <>
              <button
                onClick={() => onEdit(workflow)}
                className="action-btn secondary"
                title="Edit Workflow"
              >
                <Edit size={16} />
              </button>
              
              <button
                onClick={() => onDuplicate(workflow)}
                className="action-btn secondary"
                title="Duplicate Workflow"
              >
                <Copy size={16} />
              </button>
              
              <button
                onClick={() => onToggleStatus(workflow.id, workflow.is_active)}
                className="action-btn secondary"
                title={workflow.is_active ? "Deactivate" : "Activate"}
              >
                {workflow.is_active ? <Pause size={16} /> : <Play size={16} />}
              </button>
              
              <button
                onClick={() => onDelete(workflow.id)}
                className="action-btn danger"
                title="Delete Workflow"
              >
                <Trash2 size={16} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowsPage;