// src/pages/ModelsPage.js
import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Filter,
  Brain,
  Settings,
  TestTube,
  Check,
  X,
  AlertCircle,
  DollarSign,
  Zap,
  Clock,
  Edit,
  Trash2,
  Eye,
  CheckCircle,
  XCircle
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './ModelsPage.css';

const ModelsPage = ({ user }) => {
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [providerFilter, setProviderFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [modelToDelete, setModelToDelete] = useState(null);

  useEffect(() => {
    loadModels();
  }, [currentPage, searchTerm, providerFilter, statusFilter]);

  const loadModels = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage,
        per_page: 20,
        ...(searchTerm && { search: searchTerm }),
        ...(providerFilter && { provider: providerFilter }),
        ...(statusFilter && { status: statusFilter })
      });

      const response = await authService.apiCall(`/models?${params}`);
      if (response?.ok) {
        const data = await response.json();
        setModels(data.models || []);
        setPagination(data.pagination);
      } else {
        throw new Error('Failed to load models');
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      setError('Failed to load models');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateModel = () => {
    setShowCreateModal(true);
  };

  const handleEditModel = (model) => {
    setSelectedModel(model);
    setShowCreateModal(true);
  };

  const handleDeleteModel = (model) => {
    setModelToDelete(model);
    setShowConfirmDialog(true);
  };

  const confirmDeleteModel = async () => {
    if (modelToDelete) {
      try {
        const response = await authService.apiCall(`/models/${modelToDelete.id}`, {
          method: 'DELETE'
        });
        
        if (response?.ok) {
          setModels(models.filter(model => model.id !== modelToDelete.id));
        } else {
          throw new Error('Failed to delete model');
        }
      } catch (error) {
        console.error('Delete model error:', error);
        setError('Failed to delete model');
      } finally {
        setShowConfirmDialog(false);
        setModelToDelete(null);
      }
    }
  };

  const cancelDelete = () => {
    setShowConfirmDialog(false);
    setModelToDelete(null);
  };

  const handleTestModel = async (model) => {
    try {
      const response = await authService.apiCall(`/models/${model.id}/test`, {
        method: 'POST'
      });
      
      if (response?.ok) {
        const data = await response.json();
        alert(`Model test ${data.success ? 'passed' : 'failed'}: ${data.message}`);
      } else {
        throw new Error('Failed to test model');
      }
    } catch (error) {
      console.error('Test model error:', error);
      setError('Failed to test model');
    }
  };

  const handleToggleModelStatus = async (modelId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/models/${modelId}/toggle`, {
        method: 'PUT'
      });
      
      if (response?.ok) {
        setModels(models.map(model => 
          model.id === modelId 
            ? { ...model, is_active: !currentStatus }
            : model
        ));
      } else {
        throw new Error('Failed to toggle model status');
      }
    } catch (error) {
      console.error('Toggle model status error:', error);
      setError('Failed to toggle model status');
    }
  };

  const handleViewDetails = (model) => {
    setSelectedModel(model);
    setShowDetailsModal(true);
  };

  if (isLoading) {
    return (
      <div className="page-loading">
        <LoadingSpinner size="large" />
        <p>Loading models...</p>
      </div>
    );
  }

  return (
    <div className="models-page">
      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="modal-overlay">
          <div className="confirm-dialog">
            <h3>Confirm Delete</h3>
            <p>Are you sure you want to delete the model "{modelToDelete?.name}"?</p>
            <div className="dialog-actions">
              <button onClick={cancelDelete} className="btn btn-secondary">
                Cancel
              </button>
              <button onClick={confirmDeleteModel} className="btn btn-danger">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1 className="page-title">
              <Brain className="page-icon" />
              Models
            </h1>
            <p className="page-subtitle">
              Manage AI models and their configurations
            </p>
          </div>
          <PermissionGate 
            userRole={user?.role} 
            requiredRoles={['Admin']}
          >
            <button 
              className="btn btn-primary"
              onClick={handleCreateModel}
            >
              <Plus size={20} />
              Add Model
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
              placeholder="Search models..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-controls">
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="azure">Azure OpenAI</option>
              <option value="huggingface">Hugging Face</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
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
              <X size={16} />
            </button>
          </div>
        )}

        {/* Models Grid */}
        <div className="models-grid">
          {models.length > 0 ? (
            models.map((model) => (
              <ModelCard
                key={model.id}
                model={model}
                user={user}
                onEdit={handleEditModel}
                onDelete={handleDeleteModel}
                onTest={handleTestModel}
                onToggleStatus={handleToggleModelStatus}
                onViewDetails={handleViewDetails}
              />
            ))
          ) : (
            <div className="empty-state">
              <Brain size={64} />
              <h3>No models found</h3>
              <p>Add your first AI model to get started</p>
              <PermissionGate 
                userRole={user?.role} 
                requiredRoles={['Admin']}
              >
                <button 
                  className="btn btn-primary"
                  onClick={handleCreateModel}
                >
                  <Plus size={20} />
                  Add Model
                </button>
              </PermissionGate>
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

// Model Card Component
const ModelCard = ({ model, user, onEdit, onDelete, onTest, onToggleStatus, onViewDetails }) => {
  const canEdit = user?.role === 'Admin';

  const getStatusIcon = (isActive) => {
    return isActive 
      ? <CheckCircle size={16} className="status-icon active" />
      : <XCircle size={16} className="status-icon inactive" />;
  };

  const getProviderIcon = (provider) => {
    switch (provider) {
      case 'openai':
      case 'azure':
        return <Zap size={16} className="provider-icon openai" />;
      case 'anthropic':
        return <Brain size={16} className="provider-icon anthropic" />;
      default:
        return <Settings size={16} className="provider-icon default" />;
    }
  };

  return (
    <div className="model-card">
      <div className="model-card-header">
        <div className="model-info">
          <div className="model-meta">
            {getStatusIcon(model.is_active)}
            <span className="status-text">
              {model.is_active ? 'Active' : 'Inactive'}
            </span>
            {getProviderIcon(model.provider)}
            <span className="provider-text">{model.provider || 'Unknown'}</span>
          </div>
          <h3 className="model-name">{model.name}</h3>
          <p className="model-description">
            {model.description || 'No description provided'}
          </p>
        </div>
      </div>

      <div className="model-card-body">
        <div className="model-details">
          <div className="detail-item">
            <span className="detail-label">Model:</span>
            <span className="detail-value">{model.model_name || 'Unknown'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Max Tokens:</span>
            <span className="detail-value">{model.max_tokens || 'N/A'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Temperature:</span>
            <span className="detail-value">{model.temperature ?? 'N/A'}</span>
          </div>
        </div>

        {model.cost_per_token && (
          <div className="model-cost">
            <DollarSign size={16} />
            <span>${(model.cost_per_token * 1000).toFixed(4)}/1K tokens</span>
          </div>
        )}
      </div>

      <div className="model-card-footer">
        <div className="model-meta">
          <span className="created-date">
            Added {new Date(model.created_at).toLocaleDateString()}
          </span>
        </div>

        <div className="model-actions">
          <button
            onClick={() => onViewDetails(model)}
            className="action-btn secondary"
            title="View Details"
          >
            <Eye size={16} />
          </button>
          
          <button
            onClick={() => onTest(model)}
            className="action-btn primary"
            title="Test Model"
            disabled={!model.is_active}
          >
            <TestTube size={16} />
          </button>

          {canEdit && (
            <>
              <button
                onClick={() => onEdit(model)}
                className="action-btn secondary"
                title="Edit Model"
              >
                <Edit size={16} />
              </button>
              
              <button
                onClick={() => onToggleStatus(model.id, model.is_active)}
                className="action-btn secondary"
                title={model.is_active ? "Deactivate" : "Activate"}
              >
                {model.is_active ? <XCircle size={16} /> : <CheckCircle size={16} />}
              </button>
              
              <button
                onClick={() => onDelete(model)}
                className="action-btn danger"
                title="Delete Model"
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

export default ModelsPage;