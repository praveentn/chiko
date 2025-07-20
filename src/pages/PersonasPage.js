// src/pages/PersonasPage.js
import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Users,
  Edit,
  Trash2,
  Eye,
  TestTube,
  Copy,
  Check,
  Globe,
  Lock,
  Users as Team,
  AlertCircle,
  CheckCircle,
  XCircle,
  Code,
  FileText,
  Zap,
  X
} from 'lucide-react';

import LoadingSpinner from '../components/LoadingSpinner';
import PersonaModal from '../components/PersonaModal';
import { PermissionGate } from '../components/ProtectedRoute';
import authService from '../services/authService';
import './PersonasPage.css';

const PersonasPage = ({ user }) => {
  const [personas, setPersonas] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const loadPersonas = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '20',
        ...(searchTerm && { search: searchTerm }),
        ...(visibilityFilter && { visibility: visibilityFilter }),
        ...(statusFilter && { status: statusFilter })
      });

      const response = await authService.apiCall(`/personas?${params}`);
      if (response?.ok) {
        const data = await response.json();
        setPersonas(data.personas || []);
        setPagination(data.pagination);
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to load personas');
      }
    } catch (error) {
      console.error('Failed to load personas:', error);
      setError(error.message || 'Failed to load personas');
      setPersonas([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, searchTerm, visibilityFilter, statusFilter]);

  useEffect(() => {
    loadPersonas();
  }, [loadPersonas]);

  const handleCreatePersona = () => {
    setSelectedPersona(null);
    setShowCreateModal(true);
  };

  const handleEditPersona = (persona) => {
    setSelectedPersona(persona);
    setShowCreateModal(true);
  };

  const handleDeletePersona = async (personaId) => {
    if (!window.confirm('Are you sure you want to delete this persona?')) {
      return;
    }

    try {
      const response = await authService.apiCall(`/personas/${personaId}`, {
        method: 'DELETE'
      });

      if (response?.ok) {
        await loadPersonas(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to delete persona');
      }
    } catch (error) {
      console.error('Delete persona error:', error);
      setError(error.message || 'Failed to delete persona');
    }
  };

  const handleToggleStatus = async (personaId, currentStatus) => {
    try {
      const response = await authService.apiCall(`/personas/${personaId}`, {
        method: 'PUT',
        body: JSON.stringify({
          is_active: !currentStatus
        })
      });

      if (response?.ok) {
        await loadPersonas(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to update persona status');
      }
    } catch (error) {
      console.error('Toggle status error:', error);
      setError(error.message || 'Failed to update persona status');
    }
  };

  const handleDuplicatePersona = async (persona) => {
    try {
      const response = await authService.apiCall(`/personas/${persona.id}/duplicate`, {
        method: 'POST'
      });

      if (response?.ok) {
        await loadPersonas(); // Reload the list
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to duplicate persona');
      }
    } catch (error) {
      console.error('Duplicate persona error:', error);
      setError(error.message || 'Failed to duplicate persona');
    }
  };

  const handleViewDetails = (persona) => {
    setSelectedPersona(persona);
    setShowDetailsModal(true);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const handleVisibilityFilterChange = (e) => {
    setVisibilityFilter(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
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

  const getStatusIcon = (isActive, isApproved) => {
    if (isActive && isApproved) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    } else if (!isActive) {
      return <XCircle className="w-4 h-4 text-red-500" />;
    } else {
      return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };

  const onModalSuccess = () => {
    loadPersonas();
  };

  return (
    <div className="personas-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1>
              <Users className="w-6 h-6" />
              AI Personas
            </h1>
            <p>Define AI personalities and behaviors for your agents</p>
          </div>
          <PermissionGate resource="persona" action="create" userRole={user?.role}>
            <button
              onClick={handleCreatePersona}
              className="btn btn-primary"
              disabled={isLoading}
            >
              <Plus className="w-4 h-4" />
              Create Persona
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
            placeholder="Search personas..."
            value={searchTerm}
            onChange={handleSearchChange}
            disabled={isLoading}
          />
        </div>

        <div className="filter-controls">
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

          <select
            value={statusFilter}
            onChange={handleStatusFilterChange}
            className="filter-select"
            disabled={isLoading}
          >
            <option value="">All Status</option>
            <option value="approved">Approved</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      <div className="content-area">
        {isLoading ? (
          <div className="loading-container">
            <LoadingSpinner size="large" />
            <p>Loading personas...</p>
          </div>
        ) : personas.length === 0 ? (
          <div className="empty-state">
            <Users className="w-12 h-12 text-gray-400" />
            <h3>No personas found</h3>
            <p>
              {searchTerm || visibilityFilter || statusFilter
                ? 'Try adjusting your search or filters'
                : 'Get started by creating your first AI persona'
              }
            </p>
            {!searchTerm && !visibilityFilter && !statusFilter && (
              <PermissionGate resource="persona" action="create" userRole={user?.role}>
                <button onClick={handleCreatePersona} className="btn btn-primary">
                  <Plus className="w-4 h-4" />
                  Create Your First Persona
                </button>
              </PermissionGate>
            )}
          </div>
        ) : (
          <>
            <div className="personas-grid">
              {personas.map((persona) => (
                <div key={persona.id} className="persona-card">
                  <div className="card-header">
                    <div className="card-title">
                      <h3>{persona.name}</h3>
                      <div className="card-badges">
                        {getVisibilityIcon(persona.visibility, persona.is_approved)}
                        {getStatusIcon(persona.is_active, persona.is_approved)}
                      </div>
                    </div>
                    <p className="card-description">{persona.description}</p>
                  </div>

                  <div className="card-content">
                    <div className="card-stats">
                      <div className="stat-item">
                        <span className="stat-label">Visibility</span>
                        <span className="stat-value">{persona.visibility}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Status</span>
                        <span className={`stat-value ${persona.is_active ? 'text-green-600' : 'text-red-600'}`}>
                          {persona.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    {persona.tags && persona.tags.length > 0 && (
                      <div className="card-tags">
                        {persona.tags.slice(0, 3).map((tag, index) => (
                          <span key={index} className="tag">{tag}</span>
                        ))}
                        {persona.tags.length > 3 && (
                          <span className="tag-more">+{persona.tags.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card-footer">
                    <div className="card-meta">
                      <span>By {persona.created_by}</span>
                      <span>{new Date(persona.created_at).toLocaleDateString()}</span>
                    </div>

                    <div className="card-actions">
                      <button
                        onClick={() => handleViewDetails(persona)}
                        className="btn btn-secondary btn-sm"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <PermissionGate resource="persona" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleEditPersona(persona)}
                          className="btn btn-secondary btn-sm"
                          title="Edit Persona"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="persona" action="create" userRole={user?.role}>
                        <button
                          onClick={() => handleDuplicatePersona(persona)}
                          className="btn btn-secondary btn-sm"
                          title="Duplicate Persona"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="persona" action="update" userRole={user?.role}>
                        <button
                          onClick={() => handleToggleStatus(persona.id, persona.is_active)}
                          className={`btn btn-sm ${persona.is_active ? 'btn-warning' : 'btn-success'}`}
                          title={persona.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {persona.is_active ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                        </button>
                      </PermissionGate>

                      <PermissionGate resource="persona" action="delete" userRole={user?.role}>
                        <button
                          onClick={() => handleDeletePersona(persona.id)}
                          className="btn btn-danger btn-sm"
                          title="Delete Persona"
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
      <PersonaModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        persona={selectedPersona}
        onSuccess={onModalSuccess}
        user={user}
      />

      {/* Details Modal */}
      {showDetailsModal && selectedPersona && (
        <div className="modal-backdrop" onClick={() => setShowDetailsModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Persona Details</h2>
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
                    <span>{selectedPersona.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Description</label>
                    <span>{selectedPersona.description || 'No description'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Visibility</label>
                    <span>{selectedPersona.visibility}</span>
                  </div>
                  <div className="detail-item">
                    <label>Status</label>
                    <span>{selectedPersona.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                </div>
              </div>

              <div className="details-section">
                <h3>System Prompt</h3>
                <pre className="code-block">{selectedPersona.system_prompt}</pre>
              </div>

              {selectedPersona.user_prompt_template && (
                <div className="details-section">
                  <h3>User Prompt Template</h3>
                  <pre className="code-block">{selectedPersona.user_prompt_template}</pre>
                </div>
              )}

              {selectedPersona.tags && selectedPersona.tags.length > 0 && (
                <div className="details-section">
                  <h3>Tags</h3>
                  <div className="tags-list">
                    {selectedPersona.tags.map((tag, index) => (
                      <span key={index} className="tag">{tag}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PersonasPage;