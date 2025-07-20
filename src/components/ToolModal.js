// src/components/ToolModal.js
import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, CheckCircle, TestTube } from 'lucide-react';
import authService from '../services/authService';

const ToolModal = ({ 
  isOpen, 
  onClose, 
  tool = null, 
  onSuccess,
  user 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tool_type: 'function',
    function_schema: '',
    endpoint_url: '',
    authentication: {
      type: 'none',
      api_key: '',
      bearer_token: '',
      headers: {}
    },
    safety_tags: [],
    rate_limit: 100,
    timeout: 30,
    tags: []
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState('');
  const [safetyTagInput, setSafetyTagInput] = useState('');
  const [activeTab, setActiveTab] = useState('basic');
  const [testResult, setTestResult] = useState(null);

  const toolTypeOptions = [
    { value: 'function', label: 'Function Call', description: 'Direct function execution' },
    { value: 'api', label: 'API Endpoint', description: 'HTTP API call' },
    { value: 'webhook', label: 'Webhook', description: 'Webhook trigger' },
    { value: 'mcp_server', label: 'MCP Server', description: 'Model Context Protocol server' }
  ];

  const authenticationTypes = [
    { value: 'none', label: 'None' },
    { value: 'api_key', label: 'API Key' },
    { value: 'bearer_token', label: 'Bearer Token' },
    { value: 'basic_auth', label: 'Basic Authentication' },
    { value: 'custom_headers', label: 'Custom Headers' }
  ];

  const defaultSchemas = {
    function: {
      type: "object",
      properties: {
        input: {
          type: "string",
          description: "Input parameter"
        }
      },
      required: ["input"]
    },
    api: {
      endpoint: "/api/v1/action",
      method: "POST",
      parameters: {
        query: {
          type: "object",
          properties: {}
        },
        body: {
          type: "object",
          properties: {}
        }
      }
    }
  };

  useEffect(() => {
    if (tool) {
      setFormData({
        name: tool.name || '',
        description: tool.description || '',
        tool_type: tool.tool_type || 'function',
        function_schema: tool.function_schema ? JSON.stringify(tool.function_schema, null, 2) : '',
        endpoint_url: tool.endpoint_url || '',
        authentication: tool.authentication || { type: 'none', api_key: '', bearer_token: '', headers: {} },
        safety_tags: tool.safety_tags || [],
        rate_limit: tool.rate_limit || 100,
        timeout: tool.timeout || 30,
        tags: tool.tags || []
      });
    } else {
      // Reset form for new tool
      setFormData({
        name: '',
        description: '',
        tool_type: 'function',
        function_schema: JSON.stringify(defaultSchemas.function, null, 2),
        endpoint_url: '',
        authentication: { type: 'none', api_key: '', bearer_token: '', headers: {} },
        safety_tags: [],
        rate_limit: 100,
        timeout: 30,
        tags: []
      });
    }
    setError(null);
    setTestResult(null);
  }, [tool, isOpen]);

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

  const handleToolTypeChange = (toolType) => {
    setFormData(prev => ({
      ...prev,
      tool_type: toolType,
      function_schema: JSON.stringify(defaultSchemas[toolType] || {}, null, 2),
      endpoint_url: toolType === 'api' || toolType === 'webhook' ? 'https://api.example.com/endpoint' : ''
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

  const handleAddSafetyTag = () => {
    if (safetyTagInput.trim() && !formData.safety_tags.includes(safetyTagInput.trim())) {
      setFormData(prev => ({
        ...prev,
        safety_tags: [...prev.safety_tags, safetyTagInput.trim()]
      }));
      setSafetyTagInput('');
    }
  };

  const handleRemoveSafetyTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      safety_tags: prev.safety_tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError('Name is required');
      return false;
    }
    
    if (!formData.tool_type) {
      setError('Tool type is required');
      return false;
    }

    if (!formData.function_schema.trim()) {
      setError('Function schema is required');
      return false;
    }

    // Validate JSON schema
    try {
      JSON.parse(formData.function_schema);
    } catch (e) {
      setError('Invalid function schema JSON');
      return false;
    }

    if ((formData.tool_type === 'api' || formData.tool_type === 'webhook') && !formData.endpoint_url.trim()) {
      setError('Endpoint URL is required for API and webhook tools');
      return false;
    }

    if (formData.rate_limit < 1 || formData.rate_limit > 10000) {
      setError('Rate limit must be between 1 and 10,000');
      return false;
    }

    if (formData.timeout < 1 || formData.timeout > 300) {
      setError('Timeout must be between 1 and 300 seconds');
      return false;
    }

    return true;
  };

  const handleTestTool = async () => {
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setTestResult(null);
    
    try {
      const payload = {
        name: formData.name.trim(),
        tool_type: formData.tool_type,
        function_schema: JSON.parse(formData.function_schema),
        endpoint_url: formData.endpoint_url.trim() || null,
        authentication: formData.authentication,
        timeout: parseInt(formData.timeout)
      };

      const response = await authService.apiCall('/tools/test', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (response?.ok) {
        const result = await response.json();
        setTestResult({
          success: true,
          message: 'Tool test completed successfully',
          details: result
        });
      } else {
        const errorData = response ? await response.json() : {};
        setTestResult({
          success: false,
          message: errorData.error || 'Tool test failed',
          details: errorData
        });
      }
    } catch (error) {
      console.error('Tool test error:', error);
      setTestResult({
        success: false,
        message: error.message || 'Tool test failed',
        details: null
      });
    } finally {
      setIsLoading(false);
    }
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
        tool_type: formData.tool_type,
        function_schema: JSON.parse(formData.function_schema),
        endpoint_url: formData.endpoint_url.trim() || null,
        authentication: formData.authentication,
        safety_tags: formData.safety_tags,
        rate_limit: parseInt(formData.rate_limit),
        timeout: parseInt(formData.timeout),
        tags: formData.tags
      };

      const url = tool ? `/tools/${tool.id}` : '/tools';
      const method = tool ? 'PUT' : 'POST';

      const response = await authService.apiCall(url, {
        method,
        body: JSON.stringify(payload)
      });

      if (response?.ok) {
        onSuccess && onSuccess();
        onClose();
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to save tool');
      }
    } catch (error) {
      console.error('Save tool error:', error);
      setError(error.message || 'Failed to save tool');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal tool-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{tool ? 'Edit Tool' : 'Add New Tool'}</h2>
          <button 
            onClick={onClose}
            className="modal-close-btn"
            disabled={isLoading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="modal-tabs">
          <button
            className={`tab-btn ${activeTab === 'basic' ? 'active' : ''}`}
            onClick={() => setActiveTab('basic')}
          >
            Basic Info
          </button>
          <button
            className={`tab-btn ${activeTab === 'config' ? 'active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            Configuration
          </button>
          <button
            className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            Security & Limits
          </button>
          <button
            className={`tab-btn ${activeTab === 'test' ? 'active' : ''}`}
            onClick={() => setActiveTab('test')}
          >
            Test Tool
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && (
            <div className="error-message">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          )}

          {activeTab === 'basic' && (
            <>
              <div className="form-group">
                <label htmlFor="name">Name *</label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Enter tool name"
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
                  placeholder="Describe what this tool does"
                  rows={3}
                  disabled={isLoading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="tool_type">Tool Type *</label>
                <select
                  id="tool_type"
                  value={formData.tool_type}
                  onChange={(e) => handleToolTypeChange(e.target.value)}
                  disabled={isLoading}
                  required
                >
                  {toolTypeOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label} - {option.description}
                    </option>
                  ))}
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
            </>
          )}

          {activeTab === 'config' && (
            <>
              <div className="form-group">
                <label htmlFor="function_schema">Function Schema *</label>
                <textarea
                  id="function_schema"
                  value={formData.function_schema}
                  onChange={(e) => handleInputChange('function_schema', e.target.value)}
                  placeholder="JSON schema defining the tool's interface"
                  rows={8}
                  disabled={isLoading}
                  required
                  style={{ fontFamily: 'Monaco, Menlo, Ubuntu Mono, monospace' }}
                />
                <small>JSON schema that defines the tool's parameters and return values</small>
              </div>

              {(formData.tool_type === 'api' || formData.tool_type === 'webhook') && (
                <div className="form-group">
                  <label htmlFor="endpoint_url">Endpoint URL *</label>
                  <input
                    type="url"
                    id="endpoint_url"
                    value={formData.endpoint_url}
                    onChange={(e) => handleInputChange('endpoint_url', e.target.value)}
                    placeholder="https://api.example.com/endpoint"
                    disabled={isLoading}
                    required
                  />
                </div>
              )}

              <div className="form-section">
                <h4>Authentication</h4>
                
                <div className="form-group">
                  <label htmlFor="auth_type">Authentication Type</label>
                  <select
                    id="auth_type"
                    value={formData.authentication.type}
                    onChange={(e) => handleInputChange('authentication.type', e.target.value)}
                    disabled={isLoading}
                  >
                    {authenticationTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                {formData.authentication.type === 'api_key' && (
                  <div className="form-group">
                    <label htmlFor="api_key">API Key</label>
                    <input
                      type="password"
                      id="api_key"
                      value={formData.authentication.api_key}
                      onChange={(e) => handleInputChange('authentication.api_key', e.target.value)}
                      placeholder="Enter API key"
                      disabled={isLoading}
                    />
                  </div>
                )}

                {formData.authentication.type === 'bearer_token' && (
                  <div className="form-group">
                    <label htmlFor="bearer_token">Bearer Token</label>
                    <input
                      type="password"
                      id="bearer_token"
                      value={formData.authentication.bearer_token}
                      onChange={(e) => handleInputChange('authentication.bearer_token', e.target.value)}
                      placeholder="Enter bearer token"
                      disabled={isLoading}
                    />
                  </div>
                )}
              </div>
            </>
          )}

          {activeTab === 'security' && (
            <>
              <div className="form-group">
                <label>Safety Tags</label>
                <div className="tag-input">
                  <input
                    type="text"
                    value={safetyTagInput}
                    onChange={(e) => setSafetyTagInput(e.target.value)}
                    placeholder="Add safety tags..."
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddSafetyTag();
                      }
                    }}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={handleAddSafetyTag}
                    className="btn btn-secondary btn-sm"
                    disabled={isLoading}
                  >
                    Add
                  </button>
                </div>
                {formData.safety_tags.length > 0 && (
                  <div className="tags-list">
                    {formData.safety_tags.map((tag, index) => (
                      <span key={index} className="tag safety-tag">
                        {tag}
                        <button
                          type="button"
                          onClick={() => handleRemoveSafetyTag(tag)}
                          disabled={isLoading}
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <small>Tags that indicate potential security or safety considerations</small>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="rate_limit">Rate Limit (calls/hour)</label>
                  <input
                    type="number"
                    id="rate_limit"
                    value={formData.rate_limit}
                    onChange={(e) => handleInputChange('rate_limit', e.target.value)}
                    min="1"
                    max="10000"
                    disabled={isLoading}
                  />
                  <small>Maximum calls per hour</small>
                </div>

                <div className="form-group">
                  <label htmlFor="timeout">Timeout (seconds)</label>
                  <input
                    type="number"
                    id="timeout"
                    value={formData.timeout}
                    onChange={(e) => handleInputChange('timeout', e.target.value)}
                    min="1"
                    max="300"
                    disabled={isLoading}
                  />
                  <small>Maximum execution time</small>
                </div>
              </div>
            </>
          )}

          {activeTab === 'test' && (
            <>
              <div className="test-section">
                <div className="test-header">
                  <h4>Test Tool Configuration</h4>
                  <button
                    type="button"
                    onClick={handleTestTool}
                    className="btn btn-secondary"
                    disabled={isLoading}
                  >
                    <TestTube className="w-4 h-4" />
                    {isLoading ? 'Testing...' : 'Run Test'}
                  </button>
                </div>

                {testResult && (
                  <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
                    <div className="result-header">
                      {testResult.success ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      )}
                      <span>{testResult.message}</span>
                    </div>
                    {testResult.details && (
                      <pre className="result-details">
                        {JSON.stringify(testResult.details, null, 2)}
                      </pre>
                    )}
                  </div>
                )}

                <div className="test-info">
                  <h5>Test Information</h5>
                  <p>
                    This will validate your tool configuration by attempting to:
                  </p>
                  <ul>
                    <li>Parse the function schema</li>
                    <li>Validate the endpoint URL (if applicable)</li>
                    <li>Test authentication credentials</li>
                    <li>Check connectivity and response times</li>
                  </ul>
                  <p className="test-note">
                    <strong>Note:</strong> No actual tool execution will occur during testing.
                  </p>
                </div>
              </div>
            </>
          )}
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
                {tool ? 'Updating...' : 'Adding...'}
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {tool ? 'Update Tool' : 'Add Tool'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ToolModal;