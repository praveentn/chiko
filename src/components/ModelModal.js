// src/components/ModelModal.js
import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, CheckCircle } from 'lucide-react';
import authService from '../services/authService';

const ModelModal = ({ 
  isOpen, 
  onClose, 
  model = null, 
  onSuccess,
  user 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    provider: 'azure_openai',
    deployment_id: '',
    model_name: '',
    api_endpoint: '',
    api_version: '2024-02-01',
    context_window: 4096,
    max_tokens: 4000,
    temperature: 0.1,
    input_cost_per_token: 0.00001,
    output_cost_per_token: 0.00003,
    description: '',
    tags: []
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState('');

  const providerOptions = [
    { value: 'azure_openai', label: 'Azure OpenAI' },
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic' },
    { value: 'google', label: 'Google (Gemini)' },
    { value: 'huggingface', label: 'Hugging Face' },
    { value: 'ollama', label: 'Ollama (Local)' }
  ];

  const modelNameOptions = {
    azure_openai: ['gpt-4', 'gpt-4-turbo', 'gpt-35-turbo', 'gpt-4o'],
    openai: ['gpt-4', 'gpt-4-turbo-preview', 'gpt-3.5-turbo', 'gpt-4o'],
    anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
    google: ['gemini-pro', 'gemini-pro-vision', 'gemini-ultra'],
    huggingface: ['meta-llama/Llama-2-70b-chat-hf', 'microsoft/DialoGPT-large'],
    ollama: ['llama2', 'codellama', 'mistral', 'phi']
  };

  useEffect(() => {
    if (model) {
      setFormData({
        name: model.name || '',
        provider: model.provider || 'azure_openai',
        deployment_id: model.deployment_id || '',
        model_name: model.model_name || '',
        api_endpoint: model.api_endpoint || '',
        api_version: model.api_version || '2024-02-01',
        context_window: model.context_window || 4096,
        max_tokens: model.max_tokens || 4000,
        temperature: model.temperature || 0.1,
        input_cost_per_token: model.input_cost_per_token || 0.00001,
        output_cost_per_token: model.output_cost_per_token || 0.00003,
        description: model.description || '',
        tags: model.tags || []
      });
    } else {
      // Reset form for new model
      setFormData({
        name: '',
        provider: 'azure_openai',
        deployment_id: '',
        model_name: '',
        api_endpoint: '',
        api_version: '2024-02-01',
        context_window: 4096,
        max_tokens: 4000,
        temperature: 0.1,
        input_cost_per_token: 0.00001,
        output_cost_per_token: 0.00003,
        description: '',
        tags: []
      });
    }
    setError(null);
  }, [model, isOpen]);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleProviderChange = (provider) => {
    setFormData(prev => ({
      ...prev,
      provider,
      model_name: '', // Reset model name when provider changes
      deployment_id: '',
      api_endpoint: getDefaultEndpoint(provider),
      api_version: getDefaultApiVersion(provider)
    }));
  };

  const getDefaultEndpoint = (provider) => {
    switch (provider) {
      case 'azure_openai':
        return 'https://your-resource.openai.azure.com/';
      case 'openai':
        return 'https://api.openai.com/v1';
      case 'anthropic':
        return 'https://api.anthropic.com';
      case 'google':
        return 'https://generativelanguage.googleapis.com';
      case 'ollama':
        return 'http://localhost:11434';
      default:
        return '';
    }
  };

  const getDefaultApiVersion = (provider) => {
    switch (provider) {
      case 'azure_openai':
        return '2024-02-01';
      case 'google':
        return 'v1';
      default:
        return '';
    }
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
    
    if (!formData.provider) {
      setError('Provider is required');
      return false;
    }

    if (!formData.model_name.trim()) {
      setError('Model name is required');
      return false;
    }

    if (formData.provider === 'azure_openai' && !formData.deployment_id.trim()) {
      setError('Deployment ID is required for Azure OpenAI');
      return false;
    }

    if (!formData.api_endpoint.trim()) {
      setError('API endpoint is required');
      return false;
    }

    if (formData.context_window < 1 || formData.context_window > 200000) {
      setError('Context window must be between 1 and 200,000');
      return false;
    }

    if (formData.max_tokens < 1 || formData.max_tokens > formData.context_window) {
      setError('Max tokens must be between 1 and context window size');
      return false;
    }

    if (formData.temperature < 0 || formData.temperature > 2) {
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
        provider: formData.provider,
        deployment_id: formData.deployment_id.trim() || null,
        model_name: formData.model_name.trim(),
        api_endpoint: formData.api_endpoint.trim(),
        api_version: formData.api_version.trim() || null,
        context_window: parseInt(formData.context_window),
        max_tokens: parseInt(formData.max_tokens),
        temperature: parseFloat(formData.temperature),
        input_cost_per_token: parseFloat(formData.input_cost_per_token),
        output_cost_per_token: parseFloat(formData.output_cost_per_token),
        description: formData.description.trim(),
        tags: formData.tags
      };

      const url = model ? `/models/${model.id}` : '/models';
      const method = model ? 'PUT' : 'POST';

      const response = await authService.apiCall(url, {
        method,
        body: JSON.stringify(payload)
      });

      if (response?.ok) {
        onSuccess && onSuccess();
        onClose();
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to save model');
      }
    } catch (error) {
      console.error('Save model error:', error);
      setError(error.message || 'Failed to save model');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal model-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{model ? 'Edit Model' : 'Add New Model'}</h2>
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
              placeholder="Enter model name (e.g., GPT-4 Production)"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="provider">Provider *</label>
              <select
                id="provider"
                value={formData.provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                disabled={isLoading}
                required
              >
                {providerOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="model_name">Model Name *</label>
              <select
                id="model_name"
                value={formData.model_name}
                onChange={(e) => handleInputChange('model_name', e.target.value)}
                disabled={isLoading}
                required
              >
                <option value="">Select model</option>
                {(modelNameOptions[formData.provider] || []).map(modelName => (
                  <option key={modelName} value={modelName}>
                    {modelName}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="api_endpoint">API Endpoint *</label>
            <input
              type="url"
              id="api_endpoint"
              value={formData.api_endpoint}
              onChange={(e) => handleInputChange('api_endpoint', e.target.value)}
              placeholder="https://your-resource.openai.azure.com/"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-row">
            {formData.provider === 'azure_openai' && (
              <div className="form-group">
                <label htmlFor="deployment_id">Deployment ID *</label>
                <input
                  type="text"
                  id="deployment_id"
                  value={formData.deployment_id}
                  onChange={(e) => handleInputChange('deployment_id', e.target.value)}
                  placeholder="your-deployment-name"
                  disabled={isLoading}
                  required
                />
              </div>
            )}

            {(formData.provider === 'azure_openai' || formData.provider === 'google') && (
              <div className="form-group">
                <label htmlFor="api_version">API Version</label>
                <input
                  type="text"
                  id="api_version"
                  value={formData.api_version}
                  onChange={(e) => handleInputChange('api_version', e.target.value)}
                  placeholder="2024-02-01"
                  disabled={isLoading}
                />
              </div>
            )}
          </div>

          <div className="form-section">
            <h3>Model Configuration</h3>
            
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="context_window">Context Window</label>
                <input
                  type="number"
                  id="context_window"
                  value={formData.context_window}
                  onChange={(e) => handleInputChange('context_window', e.target.value)}
                  min="1"
                  max="200000"
                  disabled={isLoading}
                />
                <small>Maximum number of tokens the model can process</small>
              </div>

              <div className="form-group">
                <label htmlFor="max_tokens">Max Tokens</label>
                <input
                  type="number"
                  id="max_tokens"
                  value={formData.max_tokens}
                  onChange={(e) => handleInputChange('max_tokens', e.target.value)}
                  min="1"
                  max={formData.context_window}
                  disabled={isLoading}
                />
                <small>Maximum tokens to generate in response</small>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="temperature">Temperature</label>
              <input
                type="number"
                id="temperature"
                value={formData.temperature}
                onChange={(e) => handleInputChange('temperature', e.target.value)}
                min="0"
                max="2"
                step="0.1"
                disabled={isLoading}
              />
              <small>Controls randomness (0 = deterministic, 2 = very random)</small>
            </div>
          </div>

          <div className="form-section">
            <h3>Pricing (per token)</h3>
            
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="input_cost_per_token">Input Cost</label>
                <input
                  type="number"
                  id="input_cost_per_token"
                  value={formData.input_cost_per_token}
                  onChange={(e) => handleInputChange('input_cost_per_token', e.target.value)}
                  min="0"
                  step="0.000001"
                  disabled={isLoading}
                />
                <small>Cost per input token in USD</small>
              </div>

              <div className="form-group">
                <label htmlFor="output_cost_per_token">Output Cost</label>
                <input
                  type="number"
                  id="output_cost_per_token"
                  value={formData.output_cost_per_token}
                  onChange={(e) => handleInputChange('output_cost_per_token', e.target.value)}
                  min="0"
                  step="0.000001"
                  disabled={isLoading}
                />
                <small>Cost per output token in USD</small>
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Describe the model's purpose and capabilities"
              rows={3}
              disabled={isLoading}
            />
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
                {model ? 'Updating...' : 'Adding...'}
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {model ? 'Update Model' : 'Add Model'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelModal;