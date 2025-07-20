# routes/workflows.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime, timedelta
import json
import traceback
from threading import Thread
import uuid

from extensions import db                       # ← pull db from the shared extensions module
from models.workflow import Workflow, WorkflowExecution
from models.user import User
from models.agent import Agent
from models.tool import Tool
from services.auth_service import get_current_user, require_role, log_activity, get_user_accessible_resources

workflows_bp = Blueprint('workflows', __name__)

@workflows_bp.route('/', methods=['GET'])
def get_workflows():
    """Get list of workflows accessible to the user"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        
        # Base query with user access filtering
        query = get_user_accessible_resources(user, Workflow)
        
        # Apply search filter
        if search:
            query = query.filter(
                (Workflow.name.ilike(f'%{search}%')) |
                (Workflow.description.ilike(f'%{search}%'))
            )
        
        # Apply status filter
        if status_filter == 'approved':
            query = query.filter(Workflow.is_approved == True)
        elif status_filter == 'pending':
            query = query.filter(Workflow.is_approved == False)
        elif status_filter == 'active':
            query = query.filter(Workflow.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Workflow.is_active == False)
        
        # Get paginated results
        workflows = query.order_by(Workflow.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'workflows': [workflow.to_dict() for workflow in workflows.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': workflows.total,
                'total_pages': workflows.pages,
                'has_next': workflows.has_next,
                'has_prev': workflows.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get workflows error: {str(e)}")
        return jsonify({'error': 'Failed to fetch workflows'}), 500

@workflows_bp.route('/<int:workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """Get a specific workflow by ID"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        # Check access permissions
        if not user.has_role('Admin'):
            if not workflow.is_approved and workflow.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Get recent executions
        recent_executions = WorkflowExecution.query.filter_by(workflow_id=workflow_id).order_by(
            WorkflowExecution.started_at.desc()
        ).limit(10).all()
        
        workflow_data = workflow.to_dict()
        workflow_data['recent_executions'] = [
            {
                'id': execution.id,
                'status': execution.status,
                'total_cost': round(execution.total_cost, 3) if execution.total_cost else 0,
                'execution_time': round(execution.execution_time, 2) if execution.execution_time else None,
                'trigger_type': execution.trigger_type,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
            }
            for execution in recent_executions
        ]
        
        return jsonify({
            'success': True,
            'workflow': workflow_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get workflow error: {str(e)}")
        return jsonify({'error': 'Failed to fetch workflow'}), 500

@workflows_bp.route('/', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def create_workflow():
    """Create a new workflow"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'workflow_definition']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate workflow definition structure
        workflow_def = data['workflow_definition']
        if not isinstance(workflow_def, dict):
            return jsonify({'error': 'workflow_definition must be a valid JSON object'}), 400
        
        # Validate basic workflow structure
        if 'nodes' not in workflow_def or 'edges' not in workflow_def:
            return jsonify({'error': 'workflow_definition must include nodes and edges'}), 400
        
        # Validate nodes contain at least start and end
        nodes = workflow_def['nodes']
        if not isinstance(nodes, list) or len(nodes) < 2:
            return jsonify({'error': 'Workflow must have at least start and end nodes'}), 400
        
        # Check for start and end nodes
        node_types = [node.get('type') for node in nodes]
        if 'start' not in node_types or 'end' not in node_types:
            return jsonify({'error': 'Workflow must have start and end nodes'}), 400
        
        # Validate schedule configuration if provided
        schedule_config = data.get('schedule_config')
        if schedule_config and not isinstance(schedule_config, dict):
            return jsonify({'error': 'schedule_config must be a valid JSON object'}), 400
        
        # Create new workflow
        workflow = Workflow(
            name=data['name'],
            description=data.get('description', ''),
            workflow_definition=workflow_def,
            schedule_config=schedule_config,
            tags=data.get('tags', []),
            is_active=True,
            is_approved=user.has_role('Admin'),  # Auto-approve for Admins
            created_by=user.id
        )
        
        db.session.add(workflow)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'workflow_created', {
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'node_count': len(workflow_def['nodes'])
        }, 'workflow', workflow.id)
        
        return jsonify({
            'success': True,
            'message': 'Workflow created successfully',
            'workflow': workflow.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create workflow error: {str(e)}")
        return jsonify({'error': 'Failed to create workflow'}), 500

@workflows_bp.route('/<int:workflow_id>', methods=['PUT'])
@require_role(['Admin', 'Developer'])
def update_workflow(workflow_id):
    """Update an existing workflow"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        # Check permissions
        if not user.has_role('Admin') and workflow.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Track changes
        changes = {}
        
        # Update basic fields
        for field in ['name', 'description']:
            if field in data and data[field] != getattr(workflow, field):
                changes[field] = {'old': getattr(workflow, field), 'new': data[field]}
                setattr(workflow, field, data[field])
        
        # Update workflow definition
        if 'workflow_definition' in data:
            new_def = data['workflow_definition']
            if new_def != workflow.workflow_definition:
                # Validate new definition
                if not isinstance(new_def, dict) or 'nodes' not in new_def or 'edges' not in new_def:
                    return jsonify({'error': 'Invalid workflow definition structure'}), 400
                
                changes['workflow_definition'] = {
                    'old': f"{len(workflow.workflow_definition.get('nodes', []))} nodes",
                    'new': f"{len(new_def.get('nodes', []))} nodes"
                }
                workflow.workflow_definition = new_def
        
        # Update schedule configuration
        if 'schedule_config' in data:
            new_schedule = data['schedule_config']
            if new_schedule != workflow.schedule_config:
                changes['schedule_config'] = {'old': 'hidden', 'new': 'updated'}
                workflow.schedule_config = new_schedule
        
        # Update tags
        if 'tags' in data and data['tags'] != workflow.tags:
            changes['tags'] = {'old': workflow.tags, 'new': data['tags']}
            workflow.tags = data['tags']
        
        # Update active status if provided (Admin only)
        if 'is_active' in data and user.has_role('Admin'):
            if data['is_active'] != workflow.is_active:
                changes['is_active'] = {'old': workflow.is_active, 'new': data['is_active']}
                workflow.is_active = data['is_active']
        
        if changes:
            workflow.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log activity
            log_activity(user.id, 'workflow_updated', {
                'workflow_id': workflow.id,
                'workflow_name': workflow.name,
                'changes': changes
            }, 'workflow', workflow.id)
            
            return jsonify({
                'success': True,
                'message': 'Workflow updated successfully',
                'workflow': workflow.to_dict(),
                'changes': changes
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No changes detected',
                'workflow': workflow.to_dict()
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update workflow error: {str(e)}")
        return jsonify({'error': 'Failed to update workflow'}), 500

@workflows_bp.route('/<int:workflow_id>', methods=['DELETE'])
@require_role(['Admin', 'Developer'])
def delete_workflow(workflow_id):
    """Delete a workflow"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        # Check permissions
        if not user.has_role('Admin') and workflow.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if workflow has running executions
        running_executions = WorkflowExecution.query.filter_by(
            workflow_id=workflow_id, 
            status='running'
        ).count()
        
        if running_executions > 0:
            return jsonify({
                'error': f'Cannot delete workflow with {running_executions} running executions'
            }), 400
        
        # Soft delete - mark as inactive first
        workflow.is_active = False
        workflow.updated_at = datetime.utcnow()
        
        # Log activity
        log_activity(user.id, 'workflow_deleted', {
            'workflow_id': workflow.id,
            'workflow_name': workflow.name
        }, 'workflow', workflow.id)
        
        # If user confirms hard delete, remove from database
        if request.args.get('hard_delete') == 'true' and user.has_role('Admin'):
            db.session.delete(workflow)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Workflow deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete workflow error: {str(e)}")
        return jsonify({'error': 'Failed to delete workflow'}), 500

@workflows_bp.route('/<int:workflow_id>/execute', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def execute_workflow(workflow_id):
    """Execute a workflow with provided input"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        # Check permissions
        if not user.has_role('Admin'):
            if not workflow.is_approved or not workflow.is_active:
                return jsonify({'error': 'Workflow not available for execution'}), 403
        
        data = request.get_json()
        input_data = data.get('input', {}) if data else {}
        trigger_type = data.get('trigger_type', 'manual') if data else 'manual'
        
        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            input_data=input_data,
            status='running',
            executed_by=user.id,
            trigger_type=trigger_type,
            started_at=datetime.utcnow()
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # Start async execution
        execution_thread = Thread(
            target=_execute_workflow_async,
            args=(execution.id, workflow.id, input_data, user.id)
        )
        execution_thread.start()
        
        # Log activity
        log_activity(user.id, 'workflow_executed', {
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'execution_id': execution.id,
            'trigger_type': trigger_type
        }, 'workflow', workflow.id)
        
        return jsonify({
            'success': True,
            'message': 'Workflow execution started',
            'execution_id': execution.id,
            'execution': {
                'id': execution.id,
                'status': execution.status,
                'trigger_type': execution.trigger_type,
                'started_at': execution.started_at.isoformat()
            }
        }), 202
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Execute workflow error: {str(e)}")
        return jsonify({'error': 'Failed to start workflow execution'}), 500

@workflows_bp.route('/<int:workflow_id>/executions', methods=['GET'])
def get_workflow_executions(workflow_id):
    """Get execution history for a workflow"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        # Check permissions
        if not user.has_role('Admin'):
            if not workflow.is_approved and workflow.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status', '').strip()
        
        # Build query
        query = WorkflowExecution.query.filter_by(workflow_id=workflow_id)
        
        if status_filter:
            query = query.filter(WorkflowExecution.status == status_filter)
        
        # Get paginated results
        executions = query.order_by(WorkflowExecution.started_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'executions': [
                {
                    'id': execution.id,
                    'status': execution.status,
                    'total_cost': round(execution.total_cost, 3) if execution.total_cost else 0,
                    'execution_time': round(execution.execution_time, 2) if execution.execution_time else None,
                    'trigger_type': execution.trigger_type,
                    'error_message': execution.error_message,
                    'started_at': execution.started_at.isoformat() if execution.started_at else None,
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
                }
                for execution in executions.items
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': executions.total,
                'total_pages': executions.pages,
                'has_next': executions.has_next,
                'has_prev': executions.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get workflow executions error: {str(e)}")
        return jsonify({'error': 'Failed to fetch executions'}), 500

@workflows_bp.route('/executions/<int:execution_id>', methods=['GET'])
def get_execution_details(execution_id):
    """Get detailed execution information"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        execution = WorkflowExecution.query.get_or_404(execution_id)
        workflow = execution.workflow
        
        # Check permissions
        if not user.has_role('Admin'):
            if execution.executed_by != user.id and workflow.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        execution_data = {
            'id': execution.id,
            'workflow_id': execution.workflow_id,
            'workflow_name': workflow.name,
            'status': execution.status,
            'input_data': execution.input_data,
            'output_data': execution.output_data,
            'trace_data': execution.trace_data,
            'total_cost': round(execution.total_cost, 3) if execution.total_cost else 0,
            'execution_time': round(execution.execution_time, 2) if execution.execution_time else None,
            'trigger_type': execution.trigger_type,
            'error_message': execution.error_message,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
        }
        
        return jsonify({
            'success': True,
            'execution': execution_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get execution details error: {str(e)}")
        return jsonify({'error': 'Failed to fetch execution details'}), 500

@workflows_bp.route('/<int:workflow_id>/approve', methods=['POST'])
@require_role(['Admin'])
def approve_workflow(workflow_id):
    """Approve or reject a workflow"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        approve = data.get('approve', True)
        comment = data.get('comment', '')
        
        workflow.is_approved = approve
        workflow.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'workflow_approved' if approve else 'workflow_rejected', {
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'comment': comment
        }, 'workflow', workflow.id)
        
        return jsonify({
            'success': True,
            'message': f'Workflow {"approved" if approve else "rejected"} successfully',
            'workflow': workflow.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve workflow error: {str(e)}")
        return jsonify({'error': 'Failed to process workflow approval'}), 500

@workflows_bp.route('/<int:workflow_id>/validate', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def validate_workflow(workflow_id):
    """Validate a workflow configuration"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        workflow = Workflow.query.get_or_404(workflow_id)
        
        # Check permissions
        if not user.has_role('Admin'):
            if not workflow.is_approved and workflow.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Perform validation
        validation_results = _validate_workflow_definition(workflow.workflow_definition)
        
        return jsonify({
            'success': True,
            'validation': validation_results
        })
        
    except Exception as e:
        current_app.logger.error(f"Validate workflow error: {str(e)}")
        return jsonify({'error': 'Failed to validate workflow'}), 500

@workflows_bp.route('/templates', methods=['GET'])
def get_workflow_templates():
    """Get predefined workflow templates"""
    try:
        templates = [
            {
                'name': 'Simple Agent Workflow',
                'description': 'A basic workflow with one agent execution',
                'workflow_definition': {
                    'nodes': [
                        {
                            'id': 'start',
                            'type': 'start',
                            'position': {'x': 100, 'y': 100},
                            'data': {'label': 'Start'}
                        },
                        {
                            'id': 'input-form',
                            'type': 'input_form',
                            'position': {'x': 300, 'y': 100},
                            'data': {
                                'label': 'Input Form',
                                'fields': [
                                    {'name': 'query', 'type': 'text', 'required': True}
                                ]
                            }
                        },
                        {
                            'id': 'agent',
                            'type': 'agent',
                            'position': {'x': 500, 'y': 100},
                            'data': {
                                'label': 'Execute Agent',
                                'agent_id': None,
                                'config': {}
                            }
                        },
                        {
                            'id': 'end',
                            'type': 'end',
                            'position': {'x': 700, 'y': 100},
                            'data': {'label': 'End'}
                        }
                    ],
                    'edges': [
                        {'id': 'e1', 'source': 'start', 'target': 'input-form'},
                        {'id': 'e2', 'source': 'input-form', 'target': 'agent'},
                        {'id': 'e3', 'source': 'agent', 'target': 'end'}
                    ]
                },
                'tags': ['basic', 'agent']
            },
            {
                'name': 'Data Analysis Pipeline',
                'description': 'Multi-step data analysis workflow',
                'workflow_definition': {
                    'nodes': [
                        {
                            'id': 'start',
                            'type': 'start',
                            'position': {'x': 100, 'y': 200},
                            'data': {'label': 'Start'}
                        },
                        {
                            'id': 'data-input',
                            'type': 'input_form',
                            'position': {'x': 300, 'y': 200},
                            'data': {
                                'label': 'Data Input',
                                'fields': [
                                    {'name': 'dataset', 'type': 'file', 'required': True}
                                ]
                            }
                        },
                        {
                            'id': 'analyze-agent',
                            'type': 'agent',
                            'position': {'x': 500, 'y': 200},
                            'data': {
                                'label': 'Analyze Data',
                                'agent_id': None,
                                'config': {'max_tokens': 4000}
                            }
                        },
                        {
                            'id': 'report-agent',
                            'type': 'agent',
                            'position': {'x': 700, 'y': 200},
                            'data': {
                                'label': 'Generate Report',
                                'agent_id': None,
                                'config': {'max_tokens': 6000}
                            }
                        },
                        {
                            'id': 'email-output',
                            'type': 'tool',
                            'position': {'x': 900, 'y': 200},
                            'data': {
                                'label': 'Send Report',
                                'tool_id': None,
                                'config': {}
                            }
                        },
                        {
                            'id': 'end',
                            'type': 'end',
                            'position': {'x': 1100, 'y': 200},
                            'data': {'label': 'End'}
                        }
                    ],
                    'edges': [
                        {'id': 'e1', 'source': 'start', 'target': 'data-input'},
                        {'id': 'e2', 'source': 'data-input', 'target': 'analyze-agent'},
                        {'id': 'e3', 'source': 'analyze-agent', 'target': 'report-agent'},
                        {'id': 'e4', 'source': 'report-agent', 'target': 'email-output'},
                        {'id': 'e5', 'source': 'email-output', 'target': 'end'}
                    ]
                },
                'tags': ['data', 'analysis', 'reporting']
            },
            {
                'name': 'Content Creation Workflow',
                'description': 'Workflow for automated content creation and publishing',
                'workflow_definition': {
                    'nodes': [
                        {
                            'id': 'start',
                            'type': 'start',
                            'position': {'x': 100, 'y': 150},
                            'data': {'label': 'Start'}
                        },
                        {
                            'id': 'topic-input',
                            'type': 'input_form',
                            'position': {'x': 300, 'y': 150},
                            'data': {
                                'label': 'Topic Input',
                                'fields': [
                                    {'name': 'topic', 'type': 'text', 'required': True},
                                    {'name': 'tone', 'type': 'select', 'options': ['formal', 'casual', 'technical']}
                                ]
                            }
                        },
                        {
                            'id': 'research-agent',
                            'type': 'agent',
                            'position': {'x': 500, 'y': 100},
                            'data': {
                                'label': 'Research Topic',
                                'agent_id': None,
                                'config': {}
                            }
                        },
                        {
                            'id': 'writer-agent',
                            'type': 'agent',
                            'position': {'x': 500, 'y': 200},
                            'data': {
                                'label': 'Write Content',
                                'agent_id': None,
                                'config': {}
                            }
                        },
                        {
                            'id': 'merge',
                            'type': 'merge',
                            'position': {'x': 700, 'y': 150},
                            'data': {'label': 'Merge Results'}
                        },
                        {
                            'id': 'end',
                            'type': 'end',
                            'position': {'x': 900, 'y': 150},
                            'data': {'label': 'End'}
                        }
                    ],
                    'edges': [
                        {'id': 'e1', 'source': 'start', 'target': 'topic-input'},
                        {'id': 'e2', 'source': 'topic-input', 'target': 'research-agent'},
                        {'id': 'e3', 'source': 'topic-input', 'target': 'writer-agent'},
                        {'id': 'e4', 'source': 'research-agent', 'target': 'merge'},
                        {'id': 'e5', 'source': 'writer-agent', 'target': 'merge'},
                        {'id': 'e6', 'source': 'merge', 'target': 'end'}
                    ]
                },
                'schedule_config': {
                    'enabled': false,
                    'cron': '0 9 * * 1',
                    'timezone': 'UTC'
                },
                'tags': ['content', 'automation', 'parallel']
            }
        ]
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        current_app.logger.error(f"Get workflow templates error: {str(e)}")
        return jsonify({'error': 'Failed to fetch workflow templates'}), 500

def _validate_workflow_definition(workflow_def):
    """Validate workflow definition structure"""
    errors = []
    warnings = []
    
    try:
        # Check basic structure
        if not isinstance(workflow_def, dict):
            errors.append("Workflow definition must be an object")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        if 'nodes' not in workflow_def or 'edges' not in workflow_def:
            errors.append("Workflow must have 'nodes' and 'edges' properties")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        nodes = workflow_def['nodes']
        edges = workflow_def['edges']
        
        if not isinstance(nodes, list) or not isinstance(edges, list):
            errors.append("Nodes and edges must be arrays")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Check for required node types
        node_types = [node.get('type') for node in nodes]
        if 'start' not in node_types:
            errors.append("Workflow must have a 'start' node")
        if 'end' not in node_types:
            errors.append("Workflow must have an 'end' node")
        
        # Validate node structure
        node_ids = set()
        for i, node in enumerate(nodes):
            if 'id' not in node:
                errors.append(f"Node {i} missing 'id' property")
            else:
                if node['id'] in node_ids:
                    errors.append(f"Duplicate node id: {node['id']}")
                node_ids.add(node['id'])
            
            if 'type' not in node:
                errors.append(f"Node {node.get('id', i)} missing 'type' property")
        
        # Validate edges
        edge_ids = set()
        for i, edge in enumerate(edges):
            if 'id' not in edge:
                warnings.append(f"Edge {i} missing 'id' property")
            else:
                if edge['id'] in edge_ids:
                    errors.append(f"Duplicate edge id: {edge['id']}")
                edge_ids.add(edge['id'])
            
            if 'source' not in edge or 'target' not in edge:
                errors.append(f"Edge {edge.get('id', i)} missing 'source' or 'target'")
            else:
                if edge['source'] not in node_ids:
                    errors.append(f"Edge references unknown source node: {edge['source']}")
                if edge['target'] not in node_ids:
                    errors.append(f"Edge references unknown target node: {edge['target']}")
        
        # Check connectivity
        if len(nodes) > 1 and len(edges) == 0:
            warnings.append("Workflow has nodes but no connections")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

def _execute_workflow_async(execution_id, workflow_id, input_data, user_id):
    """Asynchronously execute a workflow (simplified implementation)"""
    try:
        from app import app
        
        with app.app_context():
            execution = WorkflowExecution.query.get(execution_id)
            workflow = Workflow.query.get(workflow_id)
            
            if not execution or not workflow:
                return
            
            # Simulate workflow execution process
            import time
            import random
            
            # Simulate processing time based on workflow complexity
            node_count = len(workflow.workflow_definition.get('nodes', []))
            processing_time = random.uniform(3, 15) * (node_count / 5)
            time.sleep(processing_time)
            
            # Simulate success/failure
            success = random.choice([True, True, True, False])  # 75% success rate
            
            if success:
                # Simulate successful execution
                output_data = {
                    'result': f'Workflow {workflow.name} executed successfully',
                    'input_processed': input_data,
                    'nodes_executed': node_count,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                execution.status = 'completed'
                execution.output_data = output_data
                execution.total_cost = round(random.uniform(0.001, 0.5), 3)
                execution.trace_data = {
                    'execution_steps': [
                        {'step': i, 'node_id': f'node_{i}', 'status': 'completed', 'duration': random.uniform(0.1, 2.0)}
                        for i in range(1, node_count + 1)
                    ]
                }
            else:
                # Simulate failure
                execution.status = 'failed'
                execution.error_message = 'Simulated workflow execution error'
                execution.total_cost = round(random.uniform(0.001, 0.1), 3)
            
            execution.execution_time = round(processing_time, 2)
            execution.completed_at = datetime.utcnow()
            
            db.session.commit()
            
    except Exception as e:
        current_app.logger.error(f"Async workflow execution error: {str(e)}")
        # Update execution with error status
        try:
            with app.app_context():
                execution = WorkflowExecution.query.get(execution_id)
                if execution:
                    execution.status = 'failed'
                    execution.error_message = str(e)
                    execution.completed_at = datetime.utcnow()
                    db.session.commit()
        except:
            pass