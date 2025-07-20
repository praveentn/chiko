// src/pages/AgentsPage.js
import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Bot,
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
  X
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import AgentModal from '../components/AgentModal';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './AgentsPage.css';

const AgentsPage = ({ user }) => {
  const [agents, setAgents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [modelFilter, setModelFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const loadAgents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '20',
        ...(searchTerm && { search: searchTerm }),
        ...(statusFilter && { status: statusFilter }),
        ...(modelFilter && { model_id: modelFilter })
      });

      const response = await authService.apiCall(`/agents?${params}`);
      
      if (response && response.ok) {
        const data = await response.json();
        setAgents(data.agents || []);
        setPagination(data.pagination || null);
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to load agents');
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
      setError(error.message || 'Failed to load agents');
      setAgents([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchTerm, statusFilter, modelFilter]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const handleCreateAgent = () => {
    setSelectedAgent(null);
    setShowCreateModal(true);
  };

  const handleEditAgent = (agent) => {
    setSelectedAgent(agent);
    setShowCreateModal(true);
  };

  const handleDeleteAgent = async (agentId) => {
    if (!window.confirm('Are you sure you want to delete this agent?')) {
      return;
    }

    try {
      const response = await authService.apiCall(`/agents/${agentId}`, {
        method: 'DELETE'
      });

      if (response?.ok) {
        await loadAgents(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to delete agent');
      }
    } catch (error) {
      console.error('Delete agent error:', error);
      setError(error.message || 'Failed to delete agent');
    }
  };

  const handleToggleStatus = async (agentId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/agents/${agentId}`, {
        method: 'PUT',
        body: JSON.stringify({
          is_active: !currentStatus
        })
      });

      if (response?.ok) {
        await loadAgents(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to update agent status');
      }
    } catch (error) {
      console.error('Toggle status error:', error);
      setError(error.message || 'Failed to update agent status');
    }
  };

  const handleDuplicateAgent = async (agent) => {
    try {
      const response = await authService.apiCall(`/agents/${agent.id}/duplicate`, {
        method: 'POST'
      });

      if (response?.ok) {
        await loadAgents(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to duplicate agent');
      }
    } catch (error) {
      console.error('Duplicate agent error:', error);
      setError(error.message || 'Failed to duplicate agent');
    }
  };

  const handleExecuteAgent = (agent) => {
    setSelectedAgent(agent);
    setShowExecuteModal(true);
  };

  const handleViewDetails = (agent) => {
    setSelectedAgent(agent);
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

  const handleModelFilterChange = (e) => {
    setModelFilter(e.target.value);
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

  const getAccessLevelIcon = (visibility, isApproved) => {
    if (visibility === 'public' && isApproved) {
      return <Globe className="w-4 h-4 text-blue-500" title="Public" />;
    } else if (visibility === 'team' && isApproved) {
      return <Team className="w-4 h-4 text-green-500" title="Team" />;
    } else {
      return <Lock className="w-4 h-4 text-gray-500" title="Private" />;
    }
  };

  const onModalSuccess = () => {
    loadAgents();
  };

  return (
    <div className="agents-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1>
              <Bot className="w-6 h-6" />
              AI Agents
            </h1>
            <p>Create and manage intelligent AI agents for automated tasks</p>
          </div>
          <PermissionGate resource="agent" action="create" userRole={user?.role}>
            <button
              onClick={handleCreateAgent}
              className="btn btn-primary"
              disabled={isLoading}
            >
              <Plus className="w-4 h-4" />
              Create Agent
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
            placeholder="Search agents..."
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
            value={modelFilter}
            onChange={handleModelFilterChange}
            className="filter-select"
            disabled={isLoading}
          >
            <option value="">All Models</option>
            {/* Model options would be populated from API */}
          </select>
        </div>
      </div>

      <div className="content-area">
        {isLoading ? (
          <div className="loading-container">
            <LoadingSpinner size="large" />
            <p>Loading agents...</p>
          </div>
        ) : agents.length === 0 ? (
          <div className="empty-state">
            <Bot className="w-12 h-12 text-gray-400" />
            <h3>No agents found</h3>
            <p>
              {searchTerm || statusFilter || modelFilter
                ? 'Try adjusting your search or filters'
                : 'Get started by creating your first AI agent'
              }
            </p>
            {!searchTerm && !statusFilter && !modelFilter && (
              <PermissionGate resource="agent" action="create" userRole={user?.role}>
                <button onClick={handleCreateAgent} className="btn btn-primary">
                  <Plus className="w-4 h-4" />
                  Create Your First Agent
                </button>
              </PermissionGate>
            )}
          </div>
        ) : (
          <>
            <div className="agents-grid">
              {agents.map((agent) => (
                <div key={agent.id} className="agent-card">
                  <div className="card-header">
                    <div className="card-title">
                      <h3>{agent.name}</h3>
                      <div className="card-badges">
                        {getAccessLevelIcon(agent.visibility, agent.is_approved)}
                        {getStatusIcon(agent.is_active, agent.is_approved)}
                      </div>
                    </div>
                    <p className="card-description">{agent.description}</p>
                  </div>

                  <div className="card-content">
                    <div className="card-stats">
                      <div className="stat-item">
                        <span className="stat-label">Model</span>
                        <span className="stat-value">{agent.model_name || 'N/A'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Persona</span>
                        <span className="stat-value">{agent.persona_name || 'N/A'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Status</span>
                        <span className={`stat-value ${agent.is_active ? 'text-green-600' : 'text-red-600'}`}>
                          {agent.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    {agent.tags && agent.tags.length > 0 && (
                      <div className="card-tags">
                        {agent.tags.slice(0, 3).map((tag, index) => (
                          <span key={index} className="tag">{tag}</span>
                        ))}
                        {agent.tags.length > 3 && (
                          <span className="tag-more">+{agent.tags.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card-footer">
                    <div className="card-meta">
                      <span>By {agent.created_by}</span>
                      <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                    </div>

                    <div className="card-actions">
                      <button
                        onClick={() => handleViewDetails(agent)}
                        className="btn btn-secondary btn-sm"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <PermissionGate resource="agent" action="execute" userRole={user?.role}>
                        <button
                          onClick={() => handleExecuteAgent(agent)}
                          className="btn btn-success btn-sm"
                          title="Execute Agent"
                          disabled={!agent.is_active}
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="agent" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleEditAgent(agent)}
                          className="btn btn-secondary btn-sm"
                          title="Edit Agent"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="agent" action="create" userRole={user?.role}>
                        <button
                          onClick={() => handleDuplicateAgent(agent)}
                          className="btn btn-secondary btn-sm"
                          title="Duplicate Agent"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="agent" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleToggleStatus(agent.id, agent.is_active)}
                          className={`btn btn-sm ${agent.is_active ? 'btn-warning' : 'btn-success'}`}
                          title={agent.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {agent.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="agent" action="delete" userRole={user?.role}>
                        <button
                          onClick={() => handleDeleteAgent(agent.id)}
                          className="btn btn-danger btn-sm"
                          title="Delete Agent"
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
      <AgentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        agent={selectedAgent}
        onSuccess={onModalSuccess}
        user={user}
      />

      {/* Details Modal */}
      {showDetailsModal && selectedAgent && (
        <div className="modal-backdrop" onClick={() => setShowDetailsModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Agent Details</h2>
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
                    <span>{selectedAgent.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Description</label>
                    <span>{selectedAgent.description || 'No description'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Status</label>
                    <span>{selectedAgent.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Visibility</label>
                    <span>{selectedAgent.visibility}</span>
                  </div>
                </div>
              </div>

              <div className="details-section">
                <h3>Configuration</h3>
                <div className="details-grid">
                  <div className="detail-item">
                    <label>Model</label>
                    <span>{selectedAgent.model_name || 'Not specified'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Persona</label>
                    <span>{selectedAgent.persona_name || 'Not specified'}</span>
                  </div>
                </div>
              </div>

              {selectedAgent.tags && selectedAgent.tags.length > 0 && (
                <div className="details-section">
                  <h3>Tags</h3>
                  <div className="tags-list">
                    {selectedAgent.tags.map((tag, index) => (
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
      {showExecuteModal && selectedAgent && (
        <div className="modal-backdrop" onClick={() => setShowExecuteModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Execute Agent: {selectedAgent.name}</h2>
              <button onClick={() => setShowExecuteModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="modal-body">
              <p>Agent execution interface would go here.</p>
              <p>This would include input fields, execution controls, and real-time output display.</p>
            </div>
            <div className="modal-footer">
              <button
                onClick={() => setShowExecuteModal(false)}
                className="btn btn-secondary"
              >
                Close
              </button>
              <button className="btn btn-primary">
                <Play className="w-4 h-4" />
                Execute
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentsPage;