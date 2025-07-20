// src/components/WorkflowModal.js
import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, CheckCircle, Plus, Trash2 } from 'lucide-react';
import authService from '../services/authService';

const WorkflowModal = ({ 
  isOpen, 
  onClose, 
  workflow = null, 
  onSuccess,
  user 
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    workflow_definition: {
      nodes: [],
      connections: []
    },
    schedule_config: {
      enabled: false,
      cron_expression: '',
      triggers: []
    },
    visibility: 'private',
    tags: []
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagInput, setTagInput] = useState('');
  const [activeTab, setActiveTab] = useState('basic');

  const predefinedNodes = [
    { type: 'start', name: 'Start', description: 'Workflow entry point' },
    { type: 'input', name: 'Input Form', description: 'Collect user input' },
    { type: 'agent', name: 'AI Agent', description: 'Execute AI agent' },
    { type: 'tool', name: 'Tool Call', description: 'Call external tool' },
    { type: 'decision', name: 'Decision', description: 'Conditional branching' },
    { type: 'merge', name: 'Merge', description: 'Combine multiple paths' },
    { type: 'delay', name: 'Delay', description: 'Wait for specified time' },
    { type: 'end', name: 'End', description: 'Workflow completion' }
  ];

  const cronPresets = [
    { label: 'Every minute', value: '* * * * *' },
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Daily at 9 AM', value: '0 9 * * *' },
    { label: 'Weekly on Monday', value: '0 9 * * 1' },
    { label: 'Monthly on 1st', value: '0 9 1 * *' }
  ];

  useEffect(() => {
    if (workflow) {
      setFormData({
        name: workflow.name || '',
        description: workflow.description || '',
        workflow_definition: workflow.workflow_definition || { nodes: [], connections: [] },
        schedule_config: workflow.schedule_config || { enabled: false, cron_expression: '', triggers: [] },
        visibility: workflow.visibility || 'private',
        tags: workflow.tags || []
      });
    } else {
      // Reset form for new workflow
      setFormData({
        name: '',
        description: '',
        workflow_definition: {
          nodes: [
            { id: 'start-1', type: 'start', name: 'Start', x: 100, y: 100 },
            { id: 'end-1', type: 'end', name: 'End', x: 400, y: 100 }
          ],
          connections: []
        },
        schedule_config: {
          enabled: false,
          cron_expression: '',
          triggers: []
        },
        visibility: 'private',
        tags: []
      });
    }
    setError(null);
  }, [workflow, isOpen]);

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

  const handleAddNode = (nodeType) => {
    const newNode = {
      id: `${nodeType}-${Date.now()}`,
      type: nodeType,
      name: predefinedNodes.find(n => n.type === nodeType)?.name || nodeType,
      x: Math.random() * 300 + 150,
      y: Math.random() * 200 + 150,
      config: {}
    };

    setFormData(prev => ({
      ...prev,
      workflow_definition: {
        ...prev.workflow_definition,
        nodes: [...prev.workflow_definition.nodes, newNode]
      }
    }));
  };

  const handleRemoveNode = (nodeId) => {
    setFormData(prev => ({
      ...prev,
      workflow_definition: {
        nodes: prev.workflow_definition.nodes.filter(node => node.id !== nodeId),
        connections: prev.workflow_definition.connections.filter(
          conn => conn.from !== nodeId && conn.to !== nodeId
        )
      }
    }));
  };

  const handleAddTrigger = () => {
    const newTrigger = {
      id: `trigger-${Date.now()}`,
      type: 'webhook',
      name: 'New Trigger',
      config: {}
    };

    setFormData(prev => ({
      ...prev,
      schedule_config: {
        ...prev.schedule_config,
        triggers: [...prev.schedule_config.triggers, newTrigger]
      }
    }));
  };

  const handleRemoveTrigger = (triggerId) => {
    setFormData(prev => ({
      ...prev,
      schedule_config: {
        ...prev.schedule_config,
        triggers: prev.schedule_config.triggers.filter(trigger => trigger.id !== triggerId)
      }
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
    
    if (formData.workflow_definition.nodes.length < 2) {
      setError('Workflow must have at least Start and End nodes');
      return false;
    }

    const hasStart = formData.workflow_definition.nodes.some(node => node.type === 'start');
    const hasEnd = formData.workflow_definition.nodes.some(node => node.type === 'end');
    
    if (!hasStart) {
      setError('Workflow must have a Start node');
      return false;
    }

    if (!hasEnd) {
      setError('Workflow must have an End node');
      return false;
    }

    if (formData.schedule_config.enabled && !formData.schedule_config.cron_expression.trim()) {
      setError('Cron expression is required when scheduling is enabled');
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
        workflow_definition: formData.workflow_definition,
        schedule_config: formData.schedule_config,
        visibility: formData.visibility,
        tags: formData.tags
      };

      const url = workflow ? `/workflows/${workflow.id}` : '/workflows';
      const method = workflow ? 'PUT' : 'POST';

      const response = await authService.apiCall(url, {
        method,
        body: JSON.stringify(payload)
      });

      if (response?.ok) {
        onSuccess && onSuccess();
        onClose();
      } else {
        const errorData = response ? await response.json() : {};
        throw new Error(errorData.error || 'Failed to save workflow');
      }
    } catch (error) {
      console.error('Save workflow error:', error);
      setError(error.message || 'Failed to save workflow');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal workflow-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{workflow ? 'Edit Workflow' : 'Create New Workflow'}</h2>
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
            className={`tab-btn ${activeTab === 'design' ? 'active' : ''}`}
            onClick={() => setActiveTab('design')}
          >
            Workflow Design
          </button>
          <button
            className={`tab-btn ${activeTab === 'schedule' ? 'active' : ''}`}
            onClick={() => setActiveTab('schedule')}
          >
            Schedule & Triggers
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
                  placeholder="Enter workflow name"
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
                  placeholder="Describe what this workflow does"
                  rows={3}
                  disabled={isLoading}
                />
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
            </>
          )}

          {activeTab === 'design' && (
            <>
              <div className="workflow-designer">
                <div className="designer-toolbar">
                  <h4>Available Nodes</h4>
                  <div className="node-palette">
                    {predefinedNodes.map(nodeType => (
                      <button
                        key={nodeType.type}
                        type="button"
                        onClick={() => handleAddNode(nodeType.type)}
                        className="btn btn-secondary btn-sm"
                        disabled={isLoading}
                        title={nodeType.description}
                      >
                        <Plus className="w-3 h-3" />
                        {nodeType.name}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="workflow-canvas">
                  <h4>Workflow Nodes ({formData.workflow_definition.nodes.length})</h4>
                  <div className="nodes-list">
                    {formData.workflow_definition.nodes.map(node => (
                      <div key={node.id} className="node-item">
                        <div className="node-info">
                          <span className="node-type">{node.type}</span>
                          <span className="node-name">{node.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveNode(node.id)}
                          className="btn btn-danger btn-sm"
                          disabled={isLoading || node.type === 'start' || node.type === 'end'}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <p className="designer-note">
                    🎨 Visual workflow designer would be implemented here with drag-and-drop node editing, 
                    connection drawing, and real-time validation.
                  </p>
                </div>
              </div>
            </>
          )}

          {activeTab === 'schedule' && (
            <>
              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.schedule_config.enabled}
                    onChange={(e) => handleInputChange('schedule_config.enabled', e.target.checked)}
                    disabled={isLoading}
                  />
                  <span>Enable Scheduled Execution</span>
                </label>
              </div>

              {formData.schedule_config.enabled && (
                <>
                  <div className="form-group">
                    <label htmlFor="cron_expression">Cron Expression *</label>
                    <input
                      type="text"
                      id="cron_expression"
                      value={formData.schedule_config.cron_expression}
                      onChange={(e) => handleInputChange('schedule_config.cron_expression', e.target.value)}
                      placeholder="0 9 * * *"
                      disabled={isLoading}
                    />
                    <small>Format: minute hour day month day-of-week</small>
                  </div>

                  <div className="form-group">
                    <label>Quick Presets</label>
                    <div className="preset-buttons">
                      {cronPresets.map(preset => (
                        <button
                          key={preset.value}
                          type="button"
                          onClick={() => handleInputChange('schedule_config.cron_expression', preset.value)}
                          className="btn btn-secondary btn-sm"
                          disabled={isLoading}
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <div className="form-section">
                <div className="section-header">
                  <h4>Event Triggers</h4>
                  <button
                    type="button"
                    onClick={handleAddTrigger}
                    className="btn btn-secondary btn-sm"
                    disabled={isLoading}
                  >
                    <Plus className="w-3 h-3" />
                    Add Trigger
                  </button>
                </div>

                <div className="triggers-list">
                  {formData.schedule_config.triggers.map(trigger => (
                    <div key={trigger.id} className="trigger-item">
                      <div className="trigger-info">
                        <span className="trigger-type">{trigger.type}</span>
                        <span className="trigger-name">{trigger.name}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveTrigger(trigger.id)}
                        className="btn btn-danger btn-sm"
                        disabled={isLoading}
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  {formData.schedule_config.triggers.length === 0 && (
                    <p className="no-triggers">No triggers configured</p>
                  )}
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
                {workflow ? 'Updating...' : 'Creating...'}
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {workflow ? 'Update Workflow' : 'Create Workflow'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WorkflowModal;