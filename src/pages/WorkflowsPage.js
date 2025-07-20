// src/pages/WorkflowsPage.js
import React, { useState, useEffect, useCallback } from 'react';
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
  Globe,
  Lock,
  Users as Team,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  X
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import WorkflowModal from '../components/WorkflowModal';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './WorkflowsPage.css';

const WorkflowsPage = ({ user }) => {
  const [workflows, setWorkflows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const loadWorkflows = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '20',
        ...(searchTerm && { search: searchTerm }),
        ...(statusFilter && { status: statusFilter }),
        ...(visibilityFilter && { visibility: visibilityFilter })
      });

      const response = await authService.apiCall(`/workflows?${params}`);
      
      if (response && response.ok) {
        const data = await response.json();
        setWorkflows(data.workflows || []);
        setPagination(data.pagination || null);
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to load workflows');
      }
    } catch (error) {
      console.error('Failed to load workflows:', error);
      setError(error.message || 'Failed to load workflows');
      setWorkflows([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchTerm, statusFilter, visibilityFilter]);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  const handleCreateWorkflow = () => {
    setSelectedWorkflow(null);
    setShowCreateModal(true);
  };

  const handleEditWorkflow = (workflow) => {
    setSelectedWorkflow(workflow);
    setShowCreateModal(true);
  };

  const handleDeleteWorkflow = async (workflowId) => {
    if (!window.confirm('Are you sure you want to delete this workflow?')) {
      return;
    }

    try {
      const response = await authService.apiCall(`/workflows/${workflowId}`, {
        method: 'DELETE'
      });

      if (response?.ok) {
        await loadWorkflows(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to delete workflow');
      }
    } catch (error) {
      console.error('Delete workflow error:', error);
      setError(error.message || 'Failed to delete workflow');
    }
  };

  const handleToggleStatus = async (workflowId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/workflows/${workflowId}`, {
        method: 'PUT',
        body: JSON.stringify({
          is_active: !currentStatus
        })
      });

      if (response?.ok) {
        await loadWorkflows(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to update workflow status');
      }
    } catch (error) {
      console.error('Toggle status error:', error);
      setError(error.message || 'Failed to update workflow status');
    }
  };

  const handleDuplicateWorkflow = async (workflow) => {
    try {
      const response = await authService.apiCall(`/workflows/${workflow.id}/duplicate`, {
        method: 'POST'
      });

      if (response?.ok) {
        await loadWorkflows(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to duplicate workflow');
      }
    } catch (error) {
      console.error('Duplicate workflow error:', error);
      setError(error.message || 'Failed to duplicate workflow');
    }
  };

  const handleExecuteWorkflow = (workflow) => {
    setSelectedWorkflow(workflow);
    setShowExecuteModal(true);
  };

  const handleViewDetails = (workflow) => {
    setSelectedWorkflow(workflow);
    setShowDetailsModal(true);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  const handleVisibilityFilterChange = (e) => {
    setVisibilityFilter(e.target.value);
    setCurrentPage(1);
  };

  const getStatusIcon = (isActive, isApproved) => {
    if (isActive && isApproved) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    } else if (!isActive) {
      return <XCircle className="w-4 h-4 text-red-500" />;
    } else {
      return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getVisibilityIcon = (visibility, isApproved) => {
    if (visibility === 'public' && isApproved) {
      return <Globe className="w-4 h-4 text-blue-500" title="Public" />;
    } else if (visibility === 'team' && isApproved) {
      return <Team className="w-4 h-4 text-green-500" title="Team" />;
    } else {
      return <Lock className="w-4 h-4 text-gray-500" title="Private" />;
    }
  };

  const formatSchedule = (scheduleConfig) => {
    if (!scheduleConfig || !scheduleConfig.enabled) {
      return 'Manual execution';
    }
    
    if (scheduleConfig.cron_expression) {
      // Simple cron interpretation
      const cron = scheduleConfig.cron_expression;
      if (cron === '* * * * *') return 'Every minute';
      if (cron === '0 * * * *') return 'Hourly';
      if (cron === '0 9 * * *') return 'Daily at 9 AM';
      if (cron === '0 9 * * 1') return 'Weekly on Monday';
      if (cron === '0 9 1 * *') return 'Monthly on 1st';
      return `Custom: ${cron}`;
    }
    
    return 'Scheduled';
  };

  const getNodeCount = (workflowDefinition) => {
    return workflowDefinition?.nodes?.length || 0;
  };

  const onModalSuccess = () => {
    loadWorkflows();
  };

  return (
    <div className="workflows-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1>
              <Workflow className="w-6 h-6" />
              Workflows
            </h1>
            <p>Design and manage automated workflow processes</p>
          </div>
          <PermissionGate resource="workflow" action="create" userRole={user?.role}>
            <button
              onClick={handleCreateWorkflow}
              className="btn btn-primary"
              disabled={isLoading}
            >
              <Plus className="w-4 h-4" />
              Create Workflow
            </button>
          </PermissionGate>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="filters-section">
        <div className="search-box">
          <Search className="w-4 h-4" />
          <input
            type="text"
            placeholder="Search workflows..."
            value={searchTerm}
            onChange={handleSearchChange}
            disabled={isLoading}
          />
        </div>

        <div className="filter-controls">
          <select
            value={statusFilter}
            onChange={handleStatusFilterChange}
            className="filter-select"
            disabled={isLoading}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="approved">Approved</option>
            <option value="pending">Pending</option>
          </select>

          <select
            value={visibilityFilter}
            onChange={handleVisibilityFilterChange}
            className="filter-select"
            disabled={isLoading}
          >
            <option value="">All Visibility</option>
            <option value="private">Private</option>
            <option value="team">Team</option>
            <option value="public">Public</option>
          </select>
        </div>
      </div>

      <div className="content-area">
        {isLoading ? (
          <div className="loading-container">
            <LoadingSpinner size="large" />
            <p>Loading workflows...</p>
          </div>
        ) : workflows.length === 0 ? (
          <div className="empty-state">
            <Workflow className="w-12 h-12 text-gray-400" />
            <h3>No workflows found</h3>
            <p>
              {searchTerm || statusFilter || visibilityFilter
                ? 'Try adjusting your search or filters'
                : 'Get started by creating your first workflow'
              }
            </p>
            {!searchTerm && !statusFilter && !visibilityFilter && (
              <PermissionGate resource="workflow" action="create" userRole={user?.role}>
                <button onClick={handleCreateWorkflow} className="btn btn-primary">
                  <Plus className="w-4 h-4" />
                  Create Your First Workflow
                </button>
              </PermissionGate>
            )}
          </div>
        ) : (
          <>
            <div className="workflows-grid">
              {workflows.map((workflow) => (
                <div key={workflow.id} className="workflow-card">
                  <div className="card-header">
                    <div className="card-title">
                      <h3>{workflow.name}</h3>
                      <div className="card-badges">
                        {getVisibilityIcon(workflow.visibility, workflow.is_approved)}
                        {getStatusIcon(workflow.is_active, workflow.is_approved)}
                      </div>
                    </div>
                    <p className="card-description">{workflow.description}</p>
                  </div>

                  <div className="card-content">
                    <div className="card-stats">
                      <div className="stat-item">
                        <span className="stat-label">Nodes</span>
                        <span className="stat-value">{getNodeCount(workflow.workflow_definition)}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Schedule</span>
                        <span className="stat-value schedule-text">
                          {formatSchedule(workflow.schedule_config)}
                        </span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Status</span>
                        <span className={`stat-value ${workflow.is_active ? 'text-green-600' : 'text-red-600'}`}>
                          {workflow.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    {workflow.schedule_config?.enabled && (
                      <div className="schedule-indicator">
                        <Clock className="w-3 h-3" />
                        <span>Scheduled execution enabled</span>
                      </div>
                    )}

                    {workflow.tags && workflow.tags.length > 0 && (
                      <div className="card-tags">
                        {workflow.tags.slice(0, 3).map((tag, index) => (
                          <span key={index} className="tag">{tag}</span>
                        ))}
                        {workflow.tags.length > 3 && (
                          <span className="tag-more">+{workflow.tags.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card-footer">
                    <div className="card-meta">
                      <span>By {workflow.created_by}</span>
                      <span>{new Date(workflow.created_at).toLocaleDateString()}</span>
                    </div>

                    <div className="card-actions">
                      <button
                        onClick={() => handleViewDetails(workflow)}
                        className="btn btn-secondary btn-sm"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <PermissionGate resource="workflow" action="execute" userRole={user?.role}>
                        <button
                          onClick={() => handleExecuteWorkflow(workflow)}
                          className="btn btn-success btn-sm"
                          title="Execute Workflow"
                          disabled={!workflow.is_active}
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="workflow" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleEditWorkflow(workflow)}
                          className="btn btn-secondary btn-sm"
                          title="Edit Workflow"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="workflow" action="create" userRole={user?.role}>
                        <button
                          onClick={() => handleDuplicateWorkflow(workflow)}
                          className="btn btn-secondary btn-sm"
                          title="Duplicate Workflow"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="workflow" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleToggleStatus(workflow.id, workflow.is_active)}
                          className={`btn btn-sm ${workflow.is_active ? 'btn-warning' : 'btn-success'}`}
                          title={workflow.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {workflow.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="workflow" action="delete" userRole={user?.role}>
                        <button
                          onClick={() => handleDeleteWorkflow(workflow.id)}
                          className="btn btn-danger btn-sm"
                          title="Delete Workflow"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </PermissionGate>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {pagination && pagination.pages > 1 && (
              <div className="pagination">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="pagination-btn"
                >
                  Previous
                </button>
                
                <div className="pagination-info">
                  Page {currentPage} of {pagination.pages}
                </div>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === pagination.pages}
                  className="pagination-btn"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Create/Edit Modal */}
      <WorkflowModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        workflow={selectedWorkflow}
        onSuccess={onModalSuccess}
        user={user}
      />

      {/* Details Modal */}
      {showDetailsModal && selectedWorkflow && (
        <div className="modal-backdrop" onClick={() => setShowDetailsModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Workflow Details</h2>
              <button onClick={() => setShowDetailsModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="modal-body">
              <div className="details-section">
                <h3>Basic Information</h3>
                <div className="details-grid">
                  <div className="detail-item">
                    <label>Name</label>
                    <span>{selectedWorkflow.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Description</label>
                    <span>{selectedWorkflow.description || 'No description'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Status</label>
                    <span>{selectedWorkflow.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Visibility</label>
                    <span>{selectedWorkflow.visibility}</span>
                  </div>
                </div>
              </div>

              <div className="details-section">
                <h3>Workflow Configuration</h3>
                <div className="details-grid">
                  <div className="detail-item">
                    <label>Number of Nodes</label>
                    <span>{getNodeCount(selectedWorkflow.workflow_definition)}</span>
                  </div>
                  <div className="detail-item">
                    <label>Schedule</label>
                    <span>{formatSchedule(selectedWorkflow.schedule_config)}</span>
                  </div>
                </div>
              </div>

              {selectedWorkflow.workflow_definition?.nodes && (
                <div className="details-section">
                  <h3>Workflow Nodes</h3>
                  <div className="nodes-list">
                    {selectedWorkflow.workflow_definition.nodes.map((node, index) => (
                      <div key={node.id || index} className="node-item">
                        <span className="node-type">{node.type}</span>
                        <span className="node-name">{node.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedWorkflow.tags && selectedWorkflow.tags.length > 0 && (
                <div className="details-section">
                  <h3>Tags</h3>
                  <div className="tags-list">
                    {selectedWorkflow.tags.map((tag, index) => (
                      <span key={index} className="tag">{tag}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Execute Modal */}
      {showExecuteModal && selectedWorkflow && (
        <div className="modal-backdrop" onClick={() => setShowExecuteModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Execute Workflow: {selectedWorkflow.name}</h2>
              <button onClick={() => setShowExecuteModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="modal-body">
              <p>Workflow execution interface would go here.</p>
              <p>This would include input parameters, execution monitoring, and results display.</p>
            </div>
            <div className="modal-footer">
              <button
                onClick={() => setShowExecuteModal(false)}
                className="btn btn-secondary"
              >
                Close
              </button>
              <button className="btn btn-primary">
                <Zap className="w-4 h-4" />
                Execute
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowsPage;