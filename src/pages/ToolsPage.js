// src/pages/ToolsPage.js
import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Wrench,
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
  Shield,
  Clock,
  Activity,
  X
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import ToolModal from '../components/ToolModal';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './ToolsPage.css';

const ToolsPage = ({ user }) => {
  const [tools, setTools] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const toolTypes = [
    { value: 'function', label: 'Function' },
    { value: 'api', label: 'API' },
    { value: 'webhook', label: 'Webhook' },
    { value: 'mcp_server', label: 'MCP Server' }
  ];

  const loadTools = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '20',
        ...(searchTerm && { search: searchTerm }),
        ...(typeFilter && { tool_type: typeFilter }),
        ...(statusFilter && { status: statusFilter })
      });

      const response = await authService.apiCall(`/tools?${params}`);
      
      if (response && response.ok) {
        const data = await response.json();
        setTools(data.tools || []);
        setPagination(data.pagination || null);
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to load tools');
      }
    } catch (error) {
      console.error('Failed to load tools:', error);
      setError(error.message || 'Failed to load tools');
      setTools([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchTerm, typeFilter, statusFilter]);

  useEffect(() => {
    loadTools();
  }, [loadTools]);

  const handleCreateTool = () => {
    setSelectedTool(null);
    setShowCreateModal(true);
  };

  const handleEditTool = (tool) => {
    setSelectedTool(tool);
    setShowCreateModal(true);
  };

  const handleDeleteTool = async (toolId) => {
    if (!window.confirm('Are you sure you want to delete this tool?')) {
      return;
    }

    try {
      const response = await authService.apiCall(`/tools/${toolId}`, {
        method: 'DELETE'
      });

      if (response?.ok) {
        await loadTools(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to delete tool');
      }
    } catch (error) {
      console.error('Delete tool error:', error);
      setError(error.message || 'Failed to delete tool');
    }
  };

  const handleToggleStatus = async (toolId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/tools/${toolId}`, {
        method: 'PUT',
        body: JSON.stringify({
          is_active: !currentStatus
        })
      });

      if (response?.ok) {
        await loadTools(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to update tool status');
      }
    } catch (error) {
      console.error('Toggle status error:', error);
      setError(error.message || 'Failed to update tool status');
    }
  };

  const handleDuplicateTool = async (tool) => {
    try {
      const response = await authService.apiCall(`/tools/${tool.id}/duplicate`, {
        method: 'POST'
      });

      if (response?.ok) {
        await loadTools(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to duplicate tool');
      }
    } catch (error) {
      console.error('Duplicate tool error:', error);
      setError(error.message || 'Failed to duplicate tool');
    }
  };

  const handleTestTool = (tool) => {
    setSelectedTool(tool);
    setShowTestModal(true);
  };

  const handleViewDetails = (tool) => {
    setSelectedTool(tool);
    setShowDetailsModal(true);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const handleTypeFilterChange = (e) => {
    setTypeFilter(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  const getToolTypeIcon = (toolType) => {
    switch (toolType) {
      case 'function':
        return <Zap className="w-4 h-4 text-blue-500" />;
      case 'api':
        return <Globe className="w-4 h-4 text-green-500" />;
      case 'webhook':
        return <Activity className="w-4 h-4 text-orange-500" />;
      case 'mcp_server':
        return <Wrench className="w-4 h-4 text-purple-500" />;
      default:
        return <Wrench className="w-4 h-4 text-gray-500" />;
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

  const getHealthStatusIcon = (healthStatus) => {
    switch (healthStatus) {
      case 'healthy':
        return <CheckCircle className="w-3 h-3 text-green-500" />;
      case 'unhealthy':
        return <XCircle className="w-3 h-3 text-red-500" />;
      case 'warning':
        return <AlertCircle className="w-3 h-3 text-yellow-500" />;
      default:
        return <Clock className="w-3 h-3 text-gray-500" />;
    }
  };

  const formatLastHealthCheck = (lastCheck) => {
    if (!lastCheck) return 'Never checked';
    const date = new Date(lastCheck);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const onModalSuccess = () => {
    loadTools();
  };

  return (
    <div className="tools-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1>
              <Wrench className="w-6 h-6" />
              Tools
            </h1>
            <p>Manage external tools and integrations</p>
          </div>
          <PermissionGate resource="tool" action="create" userRole={user?.role}>
            <button
              onClick={handleCreateTool}
              className="btn btn-primary"
              disabled={isLoading}
            >
              <Plus className="w-4 h-4" />
              Add Tool
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
            placeholder="Search tools..."
            value={searchTerm}
            onChange={handleSearchChange}
            disabled={isLoading}
          />
        </div>

        <div className="filter-controls">
          <select
            value={typeFilter}
            onChange={handleTypeFilterChange}
            className="filter-select"
            disabled={isLoading}
          >
            <option value="">All Types</option>
            {toolTypes.map(type => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
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
            <p>Loading tools...</p>
          </div>
        ) : tools.length === 0 ? (
          <div className="empty-state">
            <Wrench className="w-12 h-12 text-gray-400" />
            <h3>No tools found</h3>
            <p>
              {searchTerm || typeFilter || statusFilter
                ? 'Try adjusting your search or filters'
                : 'Get started by adding your first tool'
              }
            </p>
            {!searchTerm && !typeFilter && !statusFilter && (
              <PermissionGate resource="tool" action="create" userRole={user?.role}>
                <button onClick={handleCreateTool} className="btn btn-primary">
                  <Plus className="w-4 h-4" />
                  Add Your First Tool
                </button>
              </PermissionGate>
            )}
          </div>
        ) : (
          <>
            <div className="tools-grid">
              {tools.map((tool) => (
                <div key={tool.id} className="tool-card">
                  <div className="card-header">
                    <div className="card-title">
                      <div className="tool-info">
                        {getToolTypeIcon(tool.tool_type)}
                        <h3>{tool.name}</h3>
                      </div>
                      <div className="card-badges">
                        {getStatusIcon(tool.is_active, tool.is_approved)}
                      </div>
                    </div>
                    <p className="card-description">{tool.description}</p>
                  </div>

                  <div className="card-content">
                    <div className="card-stats">
                      <div className="stat-item">
                        <span className="stat-label">Type</span>
                        <span className="stat-value">{tool.tool_type}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Rate Limit</span>
                        <span className="stat-value">{tool.rate_limit || 'N/A'}/hour</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Timeout</span>
                        <span className="stat-value">{tool.timeout || 30}s</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Status</span>
                        <span className={`stat-value ${tool.is_active ? 'text-green-600' : 'text-red-600'}`}>
                          {tool.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    <div className="health-status">
                      <div className="health-item">
                        {getHealthStatusIcon(tool.health_status)}
                        <span className="health-label">Health: {tool.health_status || 'Unknown'}</span>
                      </div>
                      <div className="health-item">
                        <Clock className="w-3 h-3" />
                        <span className="health-label">
                          Last check: {formatLastHealthCheck(tool.last_health_check)}
                        </span>
                      </div>
                    </div>

                    {tool.safety_tags && tool.safety_tags.length > 0 && (
                      <div className="safety-tags">
                        <Shield className="w-3 h-3" />
                        <span className="safety-label">Safety tags:</span>
                        <div className="safety-tag-list">
                          {tool.safety_tags.slice(0, 2).map((tag, index) => (
                            <span key={index} className="safety-tag">{tag}</span>
                          ))}
                          {tool.safety_tags.length > 2 && (
                            <span className="safety-tag-more">+{tool.safety_tags.length - 2}</span>
                          )}
                        </div>
                      </div>
                    )}

                    {tool.tags && tool.tags.length > 0 && (
                      <div className="card-tags">
                        {tool.tags.slice(0, 3).map((tag, index) => (
                          <span key={index} className="tag">{tag}</span>
                        ))}
                        {tool.tags.length > 3 && (
                          <span className="tag-more">+{tool.tags.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card-footer">
                    <div className="card-meta">
                      <span>By {tool.created_by}</span>
                      <span>{new Date(tool.created_at).toLocaleDateString()}</span>
                    </div>

                    <div className="card-actions">
                      <button
                        onClick={() => handleViewDetails(tool)}
                        className="btn btn-secondary btn-sm"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <PermissionGate resource="tool" action="test" userRole={user?.role}>
                        <button
                          onClick={() => handleTestTool(tool)}
                          className="btn btn-secondary btn-sm"
                          title="Test Tool"
                          disabled={!tool.is_active}
                        >
                          <TestTube className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="tool" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleEditTool(tool)}
                          className="btn btn-secondary btn-sm"
                          title="Edit Tool"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="tool" action="create" userRole={user?.role}>
                        <button
                          onClick={() => handleDuplicateTool(tool)}
                          className="btn btn-secondary btn-sm"
                          title="Duplicate Tool"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="tool" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleToggleStatus(tool.id, tool.is_active)}
                          className={`btn btn-sm ${tool.is_active ? 'btn-warning' : 'btn-success'}`}
                          title={tool.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {tool.is_active ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="tool" action="delete" userRole={user?.role}>
                        <button
                          onClick={() => handleDeleteTool(tool.id)}
                          className="btn btn-danger btn-sm"
                          title="Delete Tool"
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
      <ToolModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        tool={selectedTool}
        onSuccess={onModalSuccess}
        user={user}
      />

      {/* Details Modal */}
      {showDetailsModal && selectedTool && (
        <div className="modal-backdrop" onClick={() => setShowDetailsModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Tool Details</h2>
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
                    <span>{selectedTool.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Type</label>
                    <span>{selectedTool.tool_type}</span>
                  </div>
                  <div className="detail-item">
                    <label>Status</label>
                    <span>{selectedTool.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Health</label>
                    <span>{selectedTool.health_status || 'Unknown'}</span>
                  </div>
                </div>
              </div>

              <div className="details-section">
                <h3>Configuration</h3>
                <div className="details-grid">
                  {selectedTool.endpoint_url && (
                    <div className="detail-item">
                      <label>Endpoint URL</label>
                      <span className="code-text">{selectedTool.endpoint_url}</span>
                    </div>
                  )}
                  <div className="detail-item">
                    <label>Rate Limit</label>
                    <span>{selectedTool.rate_limit || 'No limit'} calls/hour</span>
                  </div>
                  <div className="detail-item">
                    <label>Timeout</label>
                    <span>{selectedTool.timeout || 30} seconds</span>
                  </div>
                  <div className="detail-item">
                    <label>Authentication</label>
                    <span>{selectedTool.authentication?.type || 'None'}</span>
                  </div>
                </div>
              </div>

              {selectedTool.function_schema && (
                <div className="details-section">
                  <h3>Function Schema</h3>
                  <pre className="code-block">
                    {JSON.stringify(selectedTool.function_schema, null, 2)}
                  </pre>
                </div>
              )}

              {selectedTool.description && (
                <div className="details-section">
                  <h3>Description</h3>
                  <p>{selectedTool.description}</p>
                </div>
              )}

              {selectedTool.safety_tags && selectedTool.safety_tags.length > 0 && (
                <div className="details-section">
                  <h3>Safety Tags</h3>
                  <div className="tags-list">
                    {selectedTool.safety_tags.map((tag, index) => (
                      <span key={index} className="tag safety-tag">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedTool.tags && selectedTool.tags.length > 0 && (
                <div className="details-section">
                  <h3>Tags</h3>
                  <div className="tags-list">
                    {selectedTool.tags.map((tag, index) => (
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
      {showTestModal && selectedTool && (
        <div className="modal-backdrop" onClick={() => setShowTestModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Test Tool: {selectedTool.name}</h2>
              <button onClick={() => setShowTestModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="modal-body">
              <p>Tool testing interface would go here.</p>
              <p>This would include parameter input, execution controls, and result display.</p>
            </div>
            <div className="modal-footer">
              <button
                onClick={() => setShowTestModal(false)}
                className="btn btn-secondary"
              >
                Close
              </button>
              <button className="btn btn-primary">
                <TestTube className="w-4 h-4" />
                Run Test
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ToolsPage;