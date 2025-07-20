// src/components/AgentModal.js
import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, CheckCircle } from 'lucide-react';
import authService from '../services/authService';

const AgentModal = ({ 
  isOpen, 
  onClose, 
  agent = null, 
  onSuccess,
  user 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    model_id: '',
    persona_id: '',
    tools: [],
    execution_settings: {
      max_turns: 10,
      max_tokens: 4000,
      temperature: 0.7,
      pattern: 'sequential'
    },
    visibility: 'private',
    tags: []
  });
  
  const [models, setModels] = useState([]);
  const [personas, setPersonas] = useState([]);
  const [tools, setTools] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadFormData();
    }
  }, [isOpen]);

  useEffect(() => {
    if (agent) {
      setFormData({
        name: agent.name || '',
        description: agent.description || '',
        model_id: agent.model_id || '',
        persona_id: agent.persona_id || '',
        tools: agent.tools || [],
        execution_settings: agent.execution_settings || {
          max_turns: 10,
          max_tokens: 4000,
          temperature: 0.7,
          pattern: 'sequential'
        },
        visibility: agent.visibility || 'private',
        tags: agent.tags || []
      });
    } else {
      // Reset form for new agent
      setFormData({
        name: '',
        description: '',
        model_id: '',
        persona_id: '',
        tools: [],
        execution_settings: {
          max_turns: 10,
          max_tokens: 4000,
          temperature: 0.7,
          pattern: 'sequential'
        },
        visibility: 'private',
        tags: []
      });
    }
    setError(null);
  }, [agent, isOpen]);

  const loadFormData = async () => {
    setIsLoadingData(true);
    try {
      const [modelsResponse, personasResponse, toolsResponse] = await Promise.all([
        authService.apiCall('/models?per_page=100'),
        authService.apiCall('/personas?per_page=100'),
        authService.apiCall('/tools?per_page=100')
      ]);

      if (modelsResponse?.ok) {
        const modelsData = await modelsResponse.json();
        setModels(modelsData.models || []);
      }

      if (personasResponse?.ok) {
        const personasData = await personasResponse.json();
        setPersonas(personasData.personas || []);
      }

      if (toolsResponse?.ok) {
        const toolsData = await toolsResponse.json();
        setTools(toolsData.tools || []);
      }
    } catch (error) {
      console.error('Failed to load form data:', error);
      setError('Failed to load required data');
    } finally {
      setIsLoadingData(false);
    }
  };

  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const handleToolToggle = (toolId) => {
    setFormData(prev => ({
      ...prev,
      tools: prev.tools.includes(toolId)
        ? prev.tools.filter(id => id !== toolId)
        : [...prev.tools, toolId]
    }));
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()]
      }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError('Name is required');
      return false;
    }
    
    if (!formData.model_id) {
      setError('Model selection is required');
      return false;
    }

    if (!formData.persona_id) {
      setError('Persona selection is required');
      return false;
    }

    const settings = formData.execution_settings;
    if (settings.max_turns < 1 || settings.max_turns > 50) {
      setError('Max turns must be between 1 and 50');
      return false;
    }

    if (settings.max_tokens < 100 || settings.max_tokens > 8000) {
      setError('Max tokens must be between 100 and 8000');
      return false;
    }

    if (settings.temperature < 0 || settings.temperature > 2) {
      setError('Temperature must be between 0 and 2');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        model_id: parseInt(formData.model_id),
        persona_id: parseInt(formData.persona_id),
        tools: formData.tools.map(id => parseInt(id)),
        execution_settings: {
          max_turns: parseInt(formData.execution_settings.max_turns),
          max_tokens: parseInt(formData.execution_settings.max_tokens),
          temperature: parseFloat(formData.execution_settings.temperature),
          pattern: formData.execution_settings.pattern
        },
        visibility: formData.visibility,
        tags: formData.tags
      };

      const url = agent ? `/agents/${agent.id}` : '/agents';
      const method = agent ? 'PUT' : 'POST';

      const response = await authService.apiCall(url, {
        method,
        body: JSON.stringify(payload)
      });

      if (response?.ok) {
        onSuccess && onSuccess();
        onClose();
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to save agent');
      }
    } catch (error) {
      console.error('Save agent error:', error);
      setError(error.message || 'Failed to save agent');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal agent-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{agent ? 'Edit Agent' : 'Create New Agent'}</h2>
          <button 
            onClick={onClose}
            className="modal-close-btn"
            disabled={isLoading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoadingData ? (
          <div className="modal-body">
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Loading form data...</p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="modal-body">
            {error && (
              <div className="error-message">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="name">Name *</label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Enter agent name"
                disabled={isLoading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Describe what this agent does"
                rows={3}
                disabled={isLoading}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="model_id">Model *</label>
                <select
                  id="model_id"
                  value={formData.model_id}
                  onChange={(e) => handleInputChange('model_id', e.target.value)}
                  disabled={isLoading}
                  required
                >
                  <option value="">Select a model</option>
                  {models.filter(model => model.is_active && model.is_approved).map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="persona_id">Persona *</label>
                <select
                  id="persona_id"
                  value={formData.persona_id}
                  onChange={(e) => handleInputChange('persona_id', e.target.value)}
                  disabled={isLoading}
                  required
                >
                  <option value="">Select a persona</option>
                  {personas.filter(persona => persona.is_active && persona.is_approved).map(persona => (
                    <option key={persona.id} value={persona.id}>
                      {persona.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Tools</label>
              <div className="tools-selection">
                {tools.filter(tool => tool.is_active && tool.is_approved).map(tool => (
                  <label key={tool.id} className="tool-checkbox">
                    <input
                      type="checkbox"
                      checked={formData.tools.includes(tool.id)}
                      onChange={() => handleToolToggle(tool.id)}
                      disabled={isLoading}
                    />
                    <span>{tool.name}</span>
                  </label>
                ))}
                {tools.length === 0 && (
                  <p className="no-tools">No tools available</p>
                )}
              </div>
            </div>

            <div className="form-section">
              <h3>Execution Settings</h3>
              
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="max_turns">Max Turns</label>
                  <input
                    type="number"
                    id="max_turns"
                    value={formData.execution_settings.max_turns}
                    onChange={(e) => handleInputChange('execution_settings.max_turns', e.target.value)}
                    min="1"
                    max="50"
                    disabled={isLoading}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="max_tokens">Max Tokens</label>
                  <input
                    type="number"
                    id="max_tokens"
                    value={formData.execution_settings.max_tokens}
                    onChange={(e) => handleInputChange('execution_settings.max_tokens', e.target.value)}
                    min="100"
                    max="8000"
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="temperature">Temperature</label>
                  <input
                    type="number"
                    id="temperature"
                    value={formData.execution_settings.temperature}
                    onChange={(e) => handleInputChange('execution_settings.temperature', e.target.value)}
                    min="0"
                    max="2"
                    step="0.1"
                    disabled={isLoading}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="pattern">Execution Pattern</label>
                  <select
                    id="pattern"
                    value={formData.execution_settings.pattern}
                    onChange={(e) => handleInputChange('execution_settings.pattern', e.target.value)}
                    disabled={isLoading}
                  >
                    <option value="sequential">Sequential</option>
                    <option value="parallel">Parallel</option>
                    <option value="hierarchical">Hierarchical</option>
                    <option value="event_loop">Event Loop</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="visibility">Visibility</label>
              <select
                id="visibility"
                value={formData.visibility}
                onChange={(e) => handleInputChange('visibility', e.target.value)}
                disabled={isLoading}
              >
                <option value="private">Private</option>
                <option value="team">Team</option>
                <option value="public">Public</option>
              </select>
            </div>

            <div className="form-group">
              <label>Tags</label>
              <div className="tag-input">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  placeholder="Add tags..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="btn btn-secondary btn-sm"
                  disabled={isLoading}
                >
                  Add
                </button>
              </div>
              {formData.tags.length > 0 && (
                <div className="tags-list">
                  {formData.tags.map((tag, index) => (
                    <span key={index} className="tag">
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        disabled={isLoading}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </form>
        )}

        <div className="modal-footer">
          <button
            type="button"
            onClick={onClose}
            className="btn btn-secondary"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            className="btn btn-primary"
            disabled={isLoading || isLoadingData}
          >
            {isLoading ? (
              <>
                <div className="spinner"></div>
                {agent ? 'Updating...' : 'Creating...'}
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {agent ? 'Update Agent' : 'Create Agent'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentModal;