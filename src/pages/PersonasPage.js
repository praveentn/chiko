// src/pages/PersonasPage.js
import React, { useState, useEffect } from 'react';
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

  useEffect(() => {
    loadPersonas();
  }, [currentPage, searchTerm, visibilityFilter, statusFilter]);

  const loadPersonas = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage,
        per_page: 20,
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
        throw new Error('Failed to load personas');
      }
    } catch (error) {
      console.error('Failed to load personas:', error);
      setError('Failed to load personas');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePersona = () => {
    setShowCreateModal(true);
  };

  const handleEditPersona = (persona) => {
    setSelectedPersona(persona);
    setShowCreateModal(true);
  };

  const handleDeletePersona = async (personaId) => {
    if (window.confirm('Are you sure you want to delete this persona?')) {
      try {
        const response = await authService.apiCall(`/personas/${personaId}`, {
          method: 'DELETE'
        });
        
        if (response?.ok) {
          setPersonas(personas.filter(persona => persona.id !== personaId));
        } else {
          throw new Error('Failed to delete persona');
        }
      } catch (error) {
        console.error('Delete persona error:', error);
        setError('Failed to delete persona');
      }
    }
  };

  const handleTestPersona = (persona) => {
    setSelectedPersona(persona);
    setShowTestModal(true);
  };

  const handleDuplicatePersona = async (persona) => {
    try {
      const response = await authService.apiCall(`/personas/${persona.id}/duplicate`, {
        method: 'POST'
      });
      
      if (response?.ok) {
        const data = await response.json();
        setPersonas([data.persona, ...personas]);
      } else {
        throw new Error('Failed to duplicate persona');
      }
    } catch (error) {
      console.error('Duplicate persona error:', error);
      setError('Failed to duplicate persona');
    }
  };

  const handleApprovePersona = async (personaId) => {
    try {
      const response = await authService.apiCall(`/personas/${personaId}/approve`, {
        method: 'PUT'
      });
      
      if (response?.ok) {
        setPersonas(personas.map(persona => 
          persona.id === personaId 
            ? { ...persona, is_approved: true }
            : persona
        ));
      } else {
        throw new Error('Failed to approve persona');
      }
    } catch (error) {
      console.error('Approve persona error:', error);
      setError('Failed to approve persona');
    }
  };

  const handleViewDetails = (persona) => {
    setSelectedPersona(persona);
    setShowDetailsModal(true);
  };

  if (isLoading) {
    return (
      <div className="page-loading">
        <LoadingSpinner size="large" />
        <p>Loading personas...</p>
      </div>
    );
  }

  return (
    <div className="personas-page">
      <div className="page-header">
        <div className="header-content">
          <div className="header-text">
            <h1 className="page-title">
              <Users className="page-icon" />
              Personas
            </h1>
            <p className="page-subtitle">
              Create and manage AI personas with custom behaviors and personalities
            </p>
          </div>
          <PermissionGate 
            userRole={user?.role} 
            requiredRoles={['Admin', 'Developer', 'Business User']}
          >
            <button 
              className="btn btn-primary"
              onClick={handleCreatePersona}
            >
              <Plus size={20} />
              Create Persona
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
              placeholder="Search personas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-controls">
            <select
              value={visibilityFilter}
              onChange={(e) => setVisibilityFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Visibility</option>
              <option value="public">Public</option>
              <option value="team">Team</option>
              <option value="private">Private</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Status</option>
              <option value="approved">Approved</option>
              <option value="pending">Pending</option>
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

        {/* Personas Grid */}
        <div className="personas-grid">
          {personas.length > 0 ? (
            personas.map((persona) => (
              <PersonaCard
                key={persona.id}
                persona={persona}
                user={user}
                onEdit={handleEditPersona}
                onDelete={handleDeletePersona}
                onTest={handleTestPersona}
                onDuplicate={handleDuplicatePersona}
                onApprove={handleApprovePersona}
                onViewDetails={handleViewDetails}
              />
            ))
          ) : (
            <div className="empty-state">
              <Users size={64} />
              <h3>No personas found</h3>
              <p>Create your first AI persona to get started</p>
              <button 
                className="btn btn-primary"
                onClick={handleCreatePersona}
              >
                <Plus size={20} />
                Create Persona
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

// Persona Card Component
const PersonaCard = ({ persona, user, onEdit, onDelete, onTest, onDuplicate, onApprove, onViewDetails }) => {
  const canEdit = user?.role === 'Admin' || persona.created_by === user?.id;

  const getVisibilityIcon = (visibility) => {
    switch (visibility) {
      case 'public':
        return <Globe size={16} className="visibility-icon public" />;
      case 'team':
        return <Team size={16} className="visibility-icon team" />;
      case 'private':
        return <Lock size={16} className="visibility-icon private" />;
      default:
        return <Lock size={16} className="visibility-icon private" />;
    }
  };

  return (
    <div className="persona-card">
      <div className="persona-card-header">
        <div className="persona-info">
          <div className="persona-meta">
            {getVisibilityIcon(persona.visibility)}
            <span className="visibility-text">{persona.visibility}</span>
            {persona.is_approved ? (
              <CheckCircle size={16} className="status-icon approved" />
            ) : (
              <XCircle size={16} className="status-icon pending" />
            )}
          </div>
          <h3 className="persona-name">{persona.name}</h3>
          <p className="persona-description">
            {persona.description || 'No description provided'}
          </p>
        </div>
      </div>

      <div className="persona-card-body">
        <div className="persona-prompt-preview">
          <div className="prompt-label">System Prompt:</div>
          <div className="prompt-text">
            {persona.system_prompt && persona.system_prompt.length > 120 
              ? `${persona.system_prompt.substring(0, 120)}...`
              : persona.system_prompt || 'No system prompt defined'
            }
          </div>
        </div>

        {persona.tags && persona.tags.length > 0 && (
          <div className="persona-tags">
            {persona.tags.slice(0, 3).map((tag, index) => (
              <span key={index} className="tag">
                {tag}
              </span>
            ))}
            {persona.tags.length > 3 && (
              <span className="tag-more">+{persona.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>

      <div className="persona-card-footer">
        <div className="persona-meta">
          <span className="created-by">
            Created by {persona.created_by_name || 'Unknown'}
          </span>
          <span className="created-date">
            {new Date(persona.created_at).toLocaleDateString()}
          </span>
        </div>

        <div className="persona-actions">
          <button
            onClick={() => onViewDetails(persona)}
            className="action-btn secondary"
            title="View Details"
          >
            <Eye size={16} />
          </button>
          
          <button
            onClick={() => onTest(persona)}
            className="action-btn primary"
            title="Test Persona"
          >
            <TestTube size={16} />
          </button>

          {canEdit && (
            <>
              <button
                onClick={() => onEdit(persona)}
                className="action-btn secondary"
                title="Edit Persona"
              >
                <Edit size={16} />
              </button>
              
              <button
                onClick={() => onDuplicate(persona)}
                className="action-btn secondary"
                title="Duplicate Persona"
              >
                <Copy size={16} />
              </button>
              
              {user?.role === 'Admin' && !persona.is_approved && (
                <button
                  onClick={() => onApprove(persona.id)}
                  className="action-btn success"
                  title="Approve Persona"
                >
                  <Check size={16} />
                </button>
              )}
              
              <button
                onClick={() => onDelete(persona.id)}
                className="action-btn danger"
                title="Delete Persona"
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

export default PersonasPage;