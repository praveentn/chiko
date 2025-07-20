// src/pages/ModelsPage.js
import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Brain,
  Edit,
  Trash2,
  Eye,
  TestTube,
  Copy,
  Globe,
  Lock,
  Users as Team,
  AlertCircle,
  CheckCircle,
  XCircle,
  Zap,
  DollarSign,
  X
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import ModelModal from '../components/ModelModal';
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
  const [showTestModal, setShowTestModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const loadModels = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '20',
        ...(searchTerm && { search: searchTerm }),
        ...(providerFilter && { provider: providerFilter }),
        ...(statusFilter && { status: statusFilter })
      });

      const response = await authService.apiCall(`/models?${params}`);
      
      if (response && response.ok) {
        const data = await response.json();
        setModels(data.models || []);
        setPagination(data.pagination || null);
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to load models');
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      setError(error.message || 'Failed to load models');
      setModels([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchTerm, providerFilter, statusFilter]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleCreateModel = () => {
    setSelectedModel(null);
    setShowCreateModal(true);
  };

  const handleEditModel = (model) => {
    setSelectedModel(model);
    setShowCreateModal(true);
  };

  const handleDeleteModel = async (modelId) => {
    if (!window.confirm('Are you sure you want to delete this model?')) {
      return;
    }

    try {
      const response = await authService.apiCall(`/models/${modelId}`, {
        method: 'DELETE'
      });

      if (response?.ok) {
        await loadModels(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to delete model');
      }
    } catch (error) {
      console.error('Delete model error:', error);
      setError(error.message || 'Failed to delete model');
    }
  };

  const handleToggleStatus = async (modelId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/models/${modelId}`, {
        method: 'PUT',
        body: JSON.stringify({
          is_active: !currentStatus
        })
      });

      if (response?.ok) {
        await loadModels(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to update model status');
      }
    } catch (error) {
      console.error('Toggle status error:', error);
      setError(error.message || 'Failed to update model status');
    }
  };

  const handleDuplicateModel = async (model) => {
    try {
      const response = await authService.apiCall(`/models/${model.id}/duplicate`, {
        method: 'POST'
      });

      if (response?.ok) {
        await loadModels(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to duplicate model');
      }
    } catch (error) {
      console.error('Duplicate model error:', error);
      setError(error.message || 'Failed to duplicate model');
    }
  };

  const handleTestModel = (model) => {
    setSelectedModel(model);
    setShowTestModal(true);
  };

  const handleViewDetails = (model) => {
    setSelectedModel(model);
    setShowDetailsModal(true);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const handleProviderFilterChange = (e) => {
    setProviderFilter(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  const getProviderIcon = (provider) => {
    switch (provider) {
      case 'azure_openai':
      case 'openai':
        return <Brain className="w-4 h-4 text-green-500" />;
      case 'anthropic':
        return <Brain className="w-4 h-4 text-purple-500" />;
      case 'google':
        return <Brain className="w-4 h-4 text-blue-500" />;
      default:
        return <Brain className="w-4 h-4 text-gray-500" />;
    }
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

  const formatCost = (cost) => {
    if (cost === null || cost === undefined) return 'N/A';
    return `$${(cost * 1000000).toFixed(4)}/1M tokens`;
  };

  const onModalSuccess = () => {
    loadModels();
  };

  return (
    <div className="models-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1>
              <Brain className="w-6 h-6" />
              AI Models
            </h1>
            <p>Manage AI models and their configurations</p>
          </div>
          <PermissionGate resource="model" action="create" userRole={user?.role}>
            <button
              onClick={handleCreateModel}
              className="btn btn-primary"
              disabled={isLoading}
            >
              <Plus className="w-4 h-4" />
              Add Model
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
            placeholder="Search models..."
            value={searchTerm}
            onChange={handleSearchChange}
            disabled={isLoading}
          />
        </div>

        <div className="filter-controls">
          <select
            value={providerFilter}
            onChange={handleProviderFilterChange}
            className="filter-select"
            disabled={isLoading}
          >
            <option value="">All Providers</option>
            <option value="azure_openai">Azure OpenAI</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google</option>
            <option value="huggingface">Hugging Face</option>
            <option value="ollama">Ollama</option>
          </select>

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
        </div>
      </div>

      <div className="content-area">
        {isLoading ? (
          <div className="loading-container">
            <LoadingSpinner size="large" />
            <p>Loading models...</p>
          </div>
        ) : models.length === 0 ? (
          <div className="empty-state">
            <Brain className="w-12 h-12 text-gray-400" />
            <h3>No models found</h3>
            <p>
              {searchTerm || providerFilter || statusFilter
                ? 'Try adjusting your search or filters'
                : 'Get started by adding your first AI model'
              }
            </p>
            {!searchTerm && !providerFilter && !statusFilter && (
              <PermissionGate resource="model" action="create" userRole={user?.role}>
                <button onClick={handleCreateModel} className="btn btn-primary">
                  <Plus className="w-4 h-4" />
                  Add Your First Model
                </button>
              </PermissionGate>
            )}
          </div>
        ) : (
          <>
            <div className="models-grid">
              {models.map((model) => (
                <div key={model.id} className="model-card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="model-info">
                        {getProviderIcon(model.provider)}
                        <h3>{model.name}</h3>
                      </div>
                      <div className="card-badges">
                        {getStatusIcon(model.is_active, model.is_approved)}
                      </div>
                    </div>
                    <p className="card-description">{model.description}</p>
                  </div>

                  <div className="card-content">
                    <div className="card-stats">
                      <div className="stat-item">
                        <span className="stat-label">Provider</span>
                        <span className="stat-value">{model.provider}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Model</span>
                        <span className="stat-value">{model.model_name}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Context</span>
                        <span className="stat-value">{model.context_window?.toLocaleString() || 'N/A'}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Status</span>
                        <span className={`stat-value ${model.is_active ? 'text-green-600' : 'text-red-600'}`}>
                          {model.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    <div className="pricing-info">
                      <div className="price-item">
                        <DollarSign className="w-3 h-3" />
                        <span className="price-label">Input:</span>
                        <span className="price-value">{formatCost(model.input_cost_per_token)}</span>
                      </div>
                      <div className="price-item">
                        <DollarSign className="w-3 h-3" />
                        <span className="price-label">Output:</span>
                        <span className="price-value">{formatCost(model.output_cost_per_token)}</span>
                      </div>
                    </div>

                    {model.tags && model.tags.length > 0 && (
                      <div className="card-tags">
                        {model.tags.slice(0, 3).map((tag, index) => (
                          <span key={index} className="tag">{tag}</span>
                        ))}
                        {model.tags.length > 3 && (
                          <span className="tag-more">+{model.tags.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card-footer">
                    <div className="card-meta">
                      <span>By {model.created_by}</span>
                      <span>{new Date(model.created_at).toLocaleDateString()}</span>
                    </div>

                    <div className="card-actions">
                      <button
                        onClick={() => handleViewDetails(model)}
                        className="btn btn-secondary btn-sm"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <PermissionGate resource="model" action="test" userRole={user?.role}>
                        <button
                          onClick={() => handleTestModel(model)}
                          className="btn btn-secondary btn-sm"
                          title="Test Model"
                          disabled={!model.is_active}
                        >
                          <TestTube className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="model" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleEditModel(model)}
                          className="btn btn-secondary btn-sm"
                          title="Edit Model"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="model" action="create" userRole={user?.role}>
                        <button
                          onClick={() => handleDuplicateModel(model)}
                          className="btn btn-secondary btn-sm"
                          title="Duplicate Model"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="model" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleToggleStatus(model.id, model.is_active)}
                          className={`btn btn-sm ${model.is_active ? 'btn-warning' : 'btn-success'}`}
                          title={model.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {model.is_active ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="model" action="delete" userRole={user?.role}>
                        <button
                          onClick={() => handleDeleteModel(model.id)}
                          className="btn btn-danger btn-sm"
                          title="Delete Model"
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
      <ModelModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        model={selectedModel}
        onSuccess={onModalSuccess}
        user={user}
      />

      {/* Details Modal */}
      {showDetailsModal && selectedModel && (
        <div className="modal-backdrop" onClick={() => setShowDetailsModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Model Details</h2>
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
                    <span>{selectedModel.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Provider</label>
                    <span>{selectedModel.provider}</span>
                  </div>
                  <div className="detail-item">
                    <label>Model Name</label>
                    <span>{selectedModel.model_name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Status</label>
                    <span>{selectedModel.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                </div>
              </div>

              <div className="details-section">
                <h3>Configuration</h3>
                <div className="details-grid">
                  <div className="detail-item">
                    <label>API Endpoint</label>
                    <span className="code-text">{selectedModel.api_endpoint}</span>
                  </div>
                  {selectedModel.deployment_id && (
                    <div className="detail-item">
                      <label>Deployment ID</label>
                      <span>{selectedModel.deployment_id}</span>
                    </div>
                  )}
                  <div className="detail-item">
                    <label>Context Window</label>
                    <span>{selectedModel.context_window?.toLocaleString()}</span>
                  </div>
                  <div className="detail-item">
                    <label>Max Tokens</label>
                    <span>{selectedModel.max_tokens?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="details-section">
                <h3>Pricing</h3>
                <div className="details-grid">
                  <div className="detail-item">
                    <label>Input Cost</label>
                    <span>{formatCost(selectedModel.input_cost_per_token)}</span>
                  </div>
                  <div className="detail-item">
                    <label>Output Cost</label>
                    <span>{formatCost(selectedModel.output_cost_per_token)}</span>
                  </div>
                </div>
              </div>

              {selectedModel.description && (
                <div className="details-section">
                  <h3>Description</h3>
                  <p>{selectedModel.description}</p>
                </div>
              )}

              {selectedModel.tags && selectedModel.tags.length > 0 && (
                <div className="details-section">
                  <h3>Tags</h3>
                  <div className="tags-list">
                    {selectedModel.tags.map((tag, index) => (
                      <span key={index} className="tag">{tag}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Test Modal */}
      {showTestModal && selectedModel && (
        <div className="modal-backdrop" onClick={() => setShowTestModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Test Model: {selectedModel.name}</h2>
              <button onClick={() => setShowTestModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="modal-body">
              <p>Model testing interface would go here.</p>
              <p>This would include a prompt input, test parameters, and response display.</p>
            </div>
            <div className="modal-footer">
              <button
                onClick={() => setShowTestModal(false)}
                className="btn btn-secondary"
              >
                Close
              </button>
              <button className="btn btn-primary">
                <Zap className="w-4 h-4" />
                Run Test
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelsPage;