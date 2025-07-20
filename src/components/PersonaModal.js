// src/components/PersonaModal.js
import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, CheckCircle } from 'lucide-react';
import authService from '../services/authService';

const PersonaModal = ({ 
  isOpen, 
  onClose, 
  persona = null, 
  onSuccess,
  user 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    system_prompt: '',
    user_prompt_template: '',
    input_schema: '',
    output_schema: '',
    visibility: 'private',
    tags: []
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    if (persona) {
      setFormData({
        name: persona.name || '',
        description: persona.description || '',
        system_prompt: persona.system_prompt || '',
        user_prompt_template: persona.user_prompt_template || '',
        input_schema: persona.input_schema ? JSON.stringify(persona.input_schema, null, 2) : '',
        output_schema: persona.output_schema ? JSON.stringify(persona.output_schema, null, 2) : '',
        visibility: persona.visibility || 'private',
        tags: persona.tags || []
      });
    } else {
      // Reset form for new persona
      setFormData({
        name: '',
        description: '',
        system_prompt: '',
        user_prompt_template: '',
        input_schema: '',
        output_schema: '',
        visibility: 'private',
        tags: []
      });
    }
    setError(null);
  }, [persona, isOpen]);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
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
    
    if (!formData.system_prompt.trim()) {
      setError('System prompt is required');
      return false;
    }

    // Validate JSON schemas if provided
    if (formData.input_schema.trim()) {
      try {
        JSON.parse(formData.input_schema);
      } catch (e) {
        setError('Invalid input schema JSON');
        return false;
      }
    }

    if (formData.output_schema.trim()) {
      try {
        JSON.parse(formData.output_schema);
      } catch (e) {
        setError('Invalid output schema JSON');
        return false;
      }
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
        system_prompt: formData.system_prompt.trim(),
        user_prompt_template: formData.user_prompt_template.trim(),
        visibility: formData.visibility,
        tags: formData.tags
      };

      // Parse JSON schemas if provided
      if (formData.input_schema.trim()) {
        payload.input_schema = JSON.parse(formData.input_schema);
      }

      if (formData.output_schema.trim()) {
        payload.output_schema = JSON.parse(formData.output_schema);
      }

      const url = persona ? `/personas/${persona.id}` : '/personas';
      const method = persona ? 'PUT' : 'POST';

      const response = await authService.apiCall(url, {
        method,
        body: JSON.stringify(payload)
      });

      if (response?.ok) {
        onSuccess && onSuccess();
        onClose();
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to save persona');
      }
    } catch (error) {
      console.error('Save persona error:', error);
      setError(error.message || 'Failed to save persona');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{persona ? 'Edit Persona' : 'Create New Persona'}</h2>
          <button 
            onClick={onClose}
            className="modal-close-btn"
            disabled={isLoading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

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
              placeholder="Enter persona name"
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
              placeholder="Describe what this persona does"
              rows={3}
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="system_prompt">System Prompt *</label>
            <textarea
              id="system_prompt"
              value={formData.system_prompt}
              onChange={(e) => handleInputChange('system_prompt', e.target.value)}
              placeholder="Enter the system prompt that defines this persona's behavior"
              rows={6}
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="user_prompt_template">User Prompt Template</label>
            <textarea
              id="user_prompt_template"
              value={formData.user_prompt_template}
              onChange={(e) => handleInputChange('user_prompt_template', e.target.value)}
              placeholder="Optional template for user prompts (use {{variable}} for placeholders)"
              rows={4}
              disabled={isLoading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="input_schema">Input Schema (JSON)</label>
              <textarea
                id="input_schema"
                value={formData.input_schema}
                onChange={(e) => handleInputChange('input_schema', e.target.value)}
                placeholder='{"type": "object", "properties": {...}}'
                rows={4}
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="output_schema">Output Schema (JSON)</label>
              <textarea
                id="output_schema"
                value={formData.output_schema}
                onChange={(e) => handleInputChange('output_schema', e.target.value)}
                placeholder='{"type": "object", "properties": {...}}'
                rows={4}
                disabled={isLoading}
              />
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
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <div className="spinner"></div>
                {persona ? 'Updating...' : 'Creating...'}
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {persona ? 'Update Persona' : 'Create Persona'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PersonaModal;