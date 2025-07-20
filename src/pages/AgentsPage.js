// src/pages/AgentsPage.js
import React, { useState, useEffect } from 'react';
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
  Check,
  Globe,
  Lock,
  Users as Team,
  AlertCircle,
  CheckCircle,
  XCircle,
  Settings,
  Activity,
  Zap
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
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

  useEffect(() => {
    loadAgents();
  }, [currentPage, searchTerm, statusFilter, modelFilter]);

  const loadAgents = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage,
        per_page: 20,
        ...(searchTerm && { search: searchTerm }),
        ...(statusFilter && { status: statusFilter }),
        ...(modelFilter && { model_id: modelFilter })
      });

      const response = await authService.apiCall(`/agents?${params}`);
      if (response?.ok) {
        const data = await response.json();
        setAgents(data.agents || []);
        setPagination(data.pagination);
      } else {
        throw new Error('Failed to load agents');
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
      setError('Failed to load agents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAgent = () => {
    setShowCreateModal(true);
  };

  const handleEditAgent = (agent) => {
    setSelectedAgent(agent);
    setShowCreateModal(true);
  };

  const handleDeleteAgent = async (agentId) => {
    if (window.confirm('Are you sure you want to delete this agent?')) {
      try {
        const response = await authService.apiCall(`/agents/${agentId}`, {
          method: 'DELETE'
        });
        
        if (response?.ok) {
          setAgents(agents.filter(agent => agent.id !== agentId));
        } else {
          throw new Error('Failed to delete agent');
        }
      } catch (error) {
        console.error('Delete agent error:', error);
        setError('Failed to delete agent');
      }
    }
  };

  const handleExecuteAgent = (agent) => {
    setSelectedAgent(agent);
    setShowExecuteModal(true);
  };

  const handleToggleAgentStatus = async (agentId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/agents/${agentId}/toggle`, {
        method: 'PUT'
      });
      
      if (response?.ok) {
        setAgents(agents.map(agent => 
          agent.id === agentId 
            ? { ...agent, is_active: !currentStatus }
            : agent
        ));
      } else {
        throw new Error('Failed to toggle agent status');
      }
    } catch (error) {
      console.error('Toggle agent status error:', error);
      setError('Failed to toggle agent status');
    }
  };

  const handleDuplicateAgent = async (agent) => {
    try {
      const response = await authService.apiCall(`/agents/${agent.id}/duplicate`, {
        method: 'POST'
      });
      
      if (response?.ok) {
        const data = await response.json();
        setAgents([data.agent, ...agents]);
      } else {
        throw new Error('Failed to duplicate agent');
      }
    } catch (error) {
      console.error('Duplicate agent error:', error);
      setError('Failed to duplicate agent');
    }
  };

  const handleViewDetails = (agent) => {
    setSelectedAgent(agent);
    setShowDetailsModal(true);
  };

  if (isLoading) {
    return (
      <div className="page-loading">
        <LoadingSpinner size="large" />
        <p>Loading agents...</p>
      </div>
    );
  }

  return (
    <div className="agents-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1 className="page-title">
              <Bot className="page-icon" />
              Agents
            </h1>
            <p className="page-subtitle">
              Manage your AI agents and their configurations
            </p>
          </div>
          <PermissionGate 
            userRole={user?.role} 
            requiredRoles={['Admin', 'Developer', 'Business User']}
          >
            <button 
              className="btn btn-primary"
              onClick={handleCreateAgent}
            >
              <Plus size={20} />
              Create Agent
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
              placeholder="Search agents..."
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
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Models</option>
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="claude-3">Claude 3</option>
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

        {/* Agents Grid */}
        <div className="agents-grid">
          {agents.length > 0 ? (
            agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                user={user}
                onEdit={handleEditAgent}
                onDelete={handleDeleteAgent}
                onExecute={handleExecuteAgent}
                onToggleStatus={handleToggleAgentStatus}
                onDuplicate={handleDuplicateAgent}
                onViewDetails={handleViewDetails}
              />
            ))
          ) : (
            <div className="empty-state">
              <Bot size={64} />
              <h3>No agents found</h3>
              <p>Create your first AI agent to get started</p>
              <button 
                className="btn btn-primary"
                onClick={handleCreateAgent}
              >
                <Plus size={20} />
                Create Agent
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

// Agent Card Component
const AgentCard = ({ agent, user, onEdit, onDelete, onExecute, onToggleStatus, onDuplicate, onViewDetails }) => {
  const canEdit = user?.role === 'Admin' || agent.created_by === user?.id;

  const getStatusIcon = (isActive, isApproved) => {
    if (!isApproved) return <XCircle size={16} className="status-icon pending" />;
    if (isActive) return <CheckCircle size={16} className="status-icon active" />;
    return <Pause size={16} className="status-icon inactive" />;
  };

  return (
    <div className="agent-card">
      <div className="agent-card-header">
        <div className="agent-info">
          <div className="agent-meta">
            {getStatusIcon(agent.is_active, agent.is_approved)}
            <span className="status-text">
              {!agent.is_approved ? 'Pending' : agent.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <h3 className="agent-name">{agent.name}</h3>
          <p className="agent-description">
            {agent.description || 'No description provided'}
          </p>
        </div>
      </div>

      <div className="agent-card-body">
        <div className="agent-details">
          <div className="detail-item">
            <span className="detail-label">Model:</span>
            <span className="detail-value">{agent.model_name || 'Unknown'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Persona:</span>
            <span className="detail-value">{agent.persona_name || 'Default'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Executions:</span>
            <span className="detail-value">{agent.execution_count || 0}</span>
          </div>
        </div>

        {agent.tags && agent.tags.length > 0 && (
          <div className="agent-tags">
            {agent.tags.slice(0, 3).map((tag, index) => (
              <span key={index} className="tag">
                {tag}
              </span>
            ))}
            {agent.tags.length > 3 && (
              <span className="tag-more">+{agent.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>

      <div className="agent-card-footer">
        <div className="agent-meta">
          <span className="created-by">
            Created by {agent.created_by_name || 'Unknown'}
          </span>
          <span className="created-date">
            {new Date(agent.created_at).toLocaleDateString()}
          </span>
        </div>

        <div className="agent-actions">
          <button
            onClick={() => onViewDetails(agent)}
            className="action-btn secondary"
            title="View Details"
          >
            <Eye size={16} />
          </button>
          
          <button
            onClick={() => onExecute(agent)}
            className="action-btn primary"
            title="Execute Agent"
            disabled={!agent.is_active || !agent.is_approved}
          >
            <Play size={16} />
          </button>

          {canEdit && (
            <>
              <button
                onClick={() => onEdit(agent)}
                className="action-btn secondary"
                title="Edit Agent"
              >
                <Edit size={16} />
              </button>
              
              <button
                onClick={() => onDuplicate(agent)}
                className="action-btn secondary"
                title="Duplicate Agent"
              >
                <Copy size={16} />
              </button>
              
              <button
                onClick={() => onToggleStatus(agent.id, agent.is_active)}
                className="action-btn secondary"
                title={agent.is_active ? "Deactivate" : "Activate"}
              >
                {agent.is_active ? <Pause size={16} /> : <Play size={16} />}
              </button>
              
              <button
                onClick={() => onDelete(agent.id)}
                className="action-btn danger"
                title="Delete Agent"
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

export default AgentsPage;