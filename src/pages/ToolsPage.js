// src/pages/ToolsPage.js
import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Wrench as ToolIcon,
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
  Code,
  Database,
  Cloud,
  Server
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './ToolsPage.css';

const ToolsPage = ({ user }) => {
  const [tools, setTools] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  useEffect(() => {
    loadTools();
  }, [currentPage, searchTerm, categoryFilter, statusFilter]);

  const loadTools = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage,
        per_page: 20,
        ...(searchTerm && { search: searchTerm }),
        ...(categoryFilter && { category: categoryFilter }),
        ...(statusFilter && { status: statusFilter })
      });

      const response = await authService.apiCall(`/tools?${params}`);
      if (response?.ok) {
        const data = await response.json();
        setTools(data.tools || []);
        setPagination(data.pagination);
      } else {
        throw new Error('Failed to load tools');
      }
    } catch (error) {
      console.error('Failed to load tools:', error);
      setError('Failed to load tools');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTool = () => {
    setShowCreateModal(true);
  };

  const handleEditTool = (tool) => {
    setSelectedTool(tool);
    setShowCreateModal(true);
  };

  const handleDeleteTool = async (toolId) => {
    if (window.confirm('Are you sure you want to delete this tool?')) {
      try {
        const response = await authService.apiCall(`/tools/${toolId}`, {
          method: 'DELETE'
        });
        
        if (response?.ok) {
          setTools(tools.filter(tool => tool.id !== toolId));
        } else {
          throw new Error('Failed to delete tool');
        }
      } catch (error) {
        console.error('Delete tool error:', error);
        setError('Failed to delete tool');
      }
    }
  };

  const handleTestTool = (tool) => {
    setSelectedTool(tool);
    setShowTestModal(true);
  };

  const handleToggleToolStatus = async (toolId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/tools/${toolId}/toggle`, {
        method: 'PUT'
      });
      
      if (response?.ok) {
        setTools(tools.map(tool => 
          tool.id === toolId 
            ? { ...tool, is_active: !currentStatus }
            : tool
        ));
      } else {
        throw new Error('Failed to toggle tool status');
      }
    } catch (error) {
      console.error('Toggle tool status error:', error);
      setError('Failed to toggle tool status');
    }
  };

  const handleDuplicateTool = async (tool) => {
    try {
      const response = await authService.apiCall(`/tools/${tool.id}/duplicate`, {
        method: 'POST'
      });
      
      if (response?.ok) {
        const data = await response.json();
        setTools([data.tool, ...tools]);
      } else {
        throw new Error('Failed to duplicate tool');
      }
    } catch (error) {
      console.error('Duplicate tool error:', error);
      setError('Failed to duplicate tool');
    }
  };

  const handleViewDetails = (tool) => {
    setSelectedTool(tool);
    setShowDetailsModal(true);
  };

  if (isLoading) {
    return (
      <div className="page-loading">
        <LoadingSpinner size="large" />
        <p>Loading tools...</p>
      </div>
    );
  }

  return (
    <div className="tools-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1 className="page-title">
              <ToolIcon className="page-icon" />
              Tools
            </h1>
            <p className="page-subtitle">
              Manage your AI tools and integrations
            </p>
          </div>
          <PermissionGate 
            userRole={user?.role} 
            requiredRoles={['Admin', 'Developer']}
          >
            <button 
              className="btn btn-primary"
              onClick={handleCreateTool}
            >
              <Plus size={20} />
              Add Tool
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
              placeholder="Search tools..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-controls">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Categories</option>
              <option value="api">API Tools</option>
              <option value="database">Database</option>
              <option value="file">File Processing</option>
              <option value="web">Web Scraping</option>
              <option value="ai">AI Services</option>
              <option value="automation">Automation</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="testing">Testing</option>
              <option value="deprecated">Deprecated</option>
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

        {/* Tools Grid */}
        <div className="tools-grid">
          {tools.length > 0 ? (
            tools.map((tool) => (
              <ToolCard
                key={tool.id}
                tool={tool}
                user={user}
                onEdit={handleEditTool}
                onDelete={handleDeleteTool}
                onTest={handleTestTool}
                onToggleStatus={handleToggleToolStatus}
                onDuplicate={handleDuplicateTool}
                onViewDetails={handleViewDetails}
              />
            ))
          ) : (
            <div className="empty-state">
              <ToolIcon size={64} />
              <h3>No tools found</h3>
              <p>Add your first tool to extend AI capabilities</p>
              <PermissionGate 
                userRole={user?.role} 
                requiredRoles={['Admin', 'Developer']}
              >
                <button 
                  className="btn btn-primary"
                  onClick={handleCreateTool}
                >
                  <Plus size={20} />
                  Add Tool
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

// Tool Card Component
const ToolCard = ({ tool, user, onEdit, onDelete, onTest, onToggleStatus, onDuplicate, onViewDetails }) => {
  const canEdit = user?.role === 'Admin' || user?.role === 'Developer';

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircle size={16} className="status-icon active" />;
      case 'inactive':
        return <Pause size={16} className="status-icon inactive" />;
      case 'testing':
        return <AlertCircle size={16} className="status-icon testing" />;
      case 'deprecated':
        return <XCircle size={16} className="status-icon deprecated" />;
      default:
        return <AlertCircle size={16} className="status-icon unknown" />;
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'api':
        return <Cloud size={16} className="category-icon api" />;
      case 'database':
        return <Database size={16} className="category-icon database" />;
      case 'file':
        return <Code size={16} className="category-icon file" />;
      case 'web':
        return <Globe size={16} className="category-icon web" />;
      case 'ai':
        return <Zap size={16} className="category-icon ai" />;
      case 'automation':
        return <Settings size={16} className="category-icon automation" />;
      default:
        return <ToolIcon size={16} className="category-icon default" />;
    }
  };

  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <div className="tool-info">
          <div className="tool-meta">
            {getStatusIcon(tool.status)}
            <span className="status-text">{tool.status || 'Unknown'}</span>
            {getCategoryIcon(tool.category)}
            <span className="category-text">{tool.category || 'General'}</span>
          </div>
          <h3 className="tool-name">{tool.name}</h3>
          <p className="tool-description">
            {tool.description || 'No description provided'}
          </p>
        </div>
      </div>

      <div className="tool-card-body">
        <div className="tool-details">
          <div className="detail-item">
            <span className="detail-label">Type:</span>
            <span className="detail-value">{tool.tool_type || 'Custom'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Version:</span>
            <span className="detail-value">{tool.version || '1.0.0'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Usage:</span>
            <span className="detail-value">{tool.usage_count || 0} times</span>
          </div>
        </div>

        {tool.tags && tool.tags.length > 0 && (
          <div className="tool-tags">
            {tool.tags.slice(0, 3).map((tag, index) => (
              <span key={index} className="tag">
                {tag}
              </span>
            ))}
            {tool.tags.length > 3 && (
              <span className="tag-more">+{tool.tags.length - 3}</span>
            )}
          </div>
        )}

        {tool.config && (
          <div className="tool-config-preview">
            <div className="config-label">Configuration:</div>
            <div className="config-text">
              {Object.keys(tool.config).length} parameters configured
            </div>
          </div>
        )}
      </div>

      <div className="tool-card-footer">
        <div className="tool-meta">
          <span className="created-by">
            Created by {tool.created_by_name || 'Unknown'}
          </span>
          <span className="created-date">
            {new Date(tool.created_at).toLocaleDateString()}
          </span>
        </div>

        <div className="tool-actions">
          <button
            onClick={() => onViewDetails(tool)}
            className="action-btn secondary"
            title="View Details"
          >
            <Eye size={16} />
          </button>
          
          <button
            onClick={() => onTest(tool)}
            className="action-btn primary"
            title="Test Tool"
            disabled={tool.status !== 'active'}
          >
            <Play size={16} />
          </button>

          {canEdit && (
            <>
              <button
                onClick={() => onEdit(tool)}
                className="action-btn secondary"
                title="Edit Tool"
              >
                <Edit size={16} />
              </button>
              
              <button
                onClick={() => onDuplicate(tool)}
                className="action-btn secondary"
                title="Duplicate Tool"
              >
                <Copy size={16} />
              </button>
              
              <button
                onClick={() => onToggleStatus(tool.id, tool.status === 'active')}
                className="action-btn secondary"
                title={tool.status === 'active' ? "Deactivate" : "Activate"}
              >
                {tool.status === 'active' ? <Pause size={16} /> : <Play size={16} />}
              </button>
              
              <button
                onClick={() => onDelete(tool.id)}
                className="action-btn danger"
                title="Delete Tool"
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

export default ToolsPage;