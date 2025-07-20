# routes/agents.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime, timedelta
import json
import traceback
import asyncio
from threading import Thread
import uuid

from extensions import db                       # ← pull db from the shared extensions module
from models.agent import Agent, AgentExecution
from models.user import User
from models.model import Model
from models.persona import Persona
from models.tool import Tool
from services.auth_service import get_current_user, require_role, log_activity, get_user_accessible_resources

agents_bp = Blueprint('agents', __name__)

@agents_bp.route('/', methods=['GET'])
def get_agents():
    """Get list of agents accessible to the user"""
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
        model_filter = request.args.get('model_id', '', type=str)
        persona_filter = request.args.get('persona_id', '', type=str)
        
        # Base query with user access filtering
        query = get_user_accessible_resources(user, Agent)
        
        # Apply search filter
        if search:
            query = query.filter(
                (Agent.name.ilike(f'%{search}%')) |
                (Agent.description.ilike(f'%{search}%'))
            )
        
        # Apply status filter
        if status_filter == 'approved':
            query = query.filter(Agent.is_approved == True)
        elif status_filter == 'pending':
            query = query.filter(Agent.is_approved == False)
        elif status_filter == 'active':
            query = query.filter(Agent.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Agent.is_active == False)
        
        # Apply model filter
        if model_filter:
            query = query.filter(Agent.model_id == model_filter)
        
        # Apply persona filter
        if persona_filter:
            query = query.filter(Agent.persona_id == persona_filter)
        
        # Get paginated results
        agents = query.order_by(Agent.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'agents': [agent.to_dict() for agent in agents.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': agents.total,
                'total_pages': agents.pages,
                'has_next': agents.has_next,
                'has_prev': agents.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get agents error: {str(e)}")
        return jsonify({'error': 'Failed to fetch agents'}), 500

@agents_bp.route('/<int:agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get a specific agent by ID"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        agent = Agent.query.get_or_404(agent_id)
        
        # Check access permissions
        if not user.has_role('Admin'):
            if not agent.is_approved and agent.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Get recent executions
        recent_executions = AgentExecution.query.filter_by(agent_id=agent_id).order_by(
            AgentExecution.started_at.desc()
        ).limit(10).all()
        
        agent_data = agent.to_dict()
        agent_data['recent_executions'] = [execution.to_dict() for execution in recent_executions]
        
        return jsonify({
            'success': True,
            'agent': agent_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get agent error: {str(e)}")
        return jsonify({'error': 'Failed to fetch agent'}), 500

@agents_bp.route('/', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def create_agent():
    """Create a new agent"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'model_id', 'persona_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate model exists and is accessible
        model = Model.query.get(data['model_id'])
        if not model:
            return jsonify({'error': 'Model not found'}), 404
        
        if not user.has_role('Admin') and not model.is_approved:
            return jsonify({'error': 'Model not approved for use'}), 403
        
        # Validate persona exists and is accessible
        persona = Persona.query.get(data['persona_id'])
        if not persona:
            return jsonify({'error': 'Persona not found'}), 404
        
        if not user.has_role('Admin') and not persona.is_approved and persona.created_by != user.id:
            return jsonify({'error': 'Persona not accessible'}), 403
        
        # Validate tools if provided
        tool_ids = data.get('tool_ids', [])
        if tool_ids:
            existing_tools = Tool.query.filter(Tool.id.in_(tool_ids)).all()
            if len(existing_tools) != len(tool_ids):
                return jsonify({'error': 'One or more tools not found'}), 404
        
        # Create new agent
        agent = Agent(
            name=data['name'],
            description=data.get('description', ''),
            model_id=data['model_id'],
            persona_id=data['persona_id'],
            execution_pattern=data.get('execution_pattern', 'sequential'),
            max_turns=min(data.get('max_turns', 10), 50),  # Cap at 50
            max_tokens=min(data.get('max_tokens', 4000), 16000),  # Cap at 16k
            temperature=max(0.0, min(data.get('temperature', 0.7), 2.0)),  # Between 0-2
            memory_type=data.get('memory_type', 'stateless'),
            tool_ids=tool_ids,
            tags=data.get('tags', []),
            is_active=True,
            is_approved=user.has_role('Admin'),  # Auto-approve for Admins
            created_by=user.id
        )
        
        db.session.add(agent)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'agent_created', {
            'agent_id': agent.id,
            'agent_name': agent.name,
            'model_id': agent.model_id,
            'persona_id': agent.persona_id
        }, 'agent', agent.id)
        
        return jsonify({
            'success': True,
            'message': 'Agent created successfully',
            'agent': agent.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create agent error: {str(e)}")
        return jsonify({'error': 'Failed to create agent'}), 500

@agents_bp.route('/<int:agent_id>', methods=['PUT'])
@require_role(['Admin', 'Developer'])
def update_agent(agent_id):
    """Update an existing agent"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        agent = Agent.query.get_or_404(agent_id)
        
        # Check permissions
        if not user.has_role('Admin') and agent.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Track changes
        changes = {}
        
        # Update basic fields
        for field in ['name', 'description', 'execution_pattern', 'memory_type']:
            if field in data and data[field] != getattr(agent, field):
                changes[field] = {'old': getattr(agent, field), 'new': data[field]}
                setattr(agent, field, data[field])
        
        # Update numeric fields with validation
        if 'max_turns' in data:
            new_value = min(data['max_turns'], 50)
            if new_value != agent.max_turns:
                changes['max_turns'] = {'old': agent.max_turns, 'new': new_value}
                agent.max_turns = new_value
        
        if 'max_tokens' in data:
            new_value = min(data['max_tokens'], 16000)
            if new_value != agent.max_tokens:
                changes['max_tokens'] = {'old': agent.max_tokens, 'new': new_value}
                agent.max_tokens = new_value
        
        if 'temperature' in data:
            new_value = max(0.0, min(data['temperature'], 2.0))
            if new_value != agent.temperature:
                changes['temperature'] = {'old': agent.temperature, 'new': new_value}
                agent.temperature = round(new_value, 2)
        
        # Update model if provided
        if 'model_id' in data and data['model_id'] != agent.model_id:
            model = Model.query.get(data['model_id'])
            if not model:
                return jsonify({'error': 'Model not found'}), 404
            if not user.has_role('Admin') and not model.is_approved:
                return jsonify({'error': 'Model not approved for use'}), 403
            
            changes['model_id'] = {'old': agent.model_id, 'new': data['model_id']}
            agent.model_id = data['model_id']
        
        # Update persona if provided
        if 'persona_id' in data and data['persona_id'] != agent.persona_id:
            persona = Persona.query.get(data['persona_id'])
            if not persona:
                return jsonify({'error': 'Persona not found'}), 404
            if not user.has_role('Admin') and not persona.is_approved and persona.created_by != user.id:
                return jsonify({'error': 'Persona not accessible'}), 403
            
            changes['persona_id'] = {'old': agent.persona_id, 'new': data['persona_id']}
            agent.persona_id = data['persona_id']
        
        # Update tool_ids if provided
        if 'tool_ids' in data:
            new_tool_ids = data['tool_ids']
            if new_tool_ids != agent.tool_ids:
                # Validate tools exist
                if new_tool_ids:
                    existing_tools = Tool.query.filter(Tool.id.in_(new_tool_ids)).all()
                    if len(existing_tools) != len(new_tool_ids):
                        return jsonify({'error': 'One or more tools not found'}), 404
                
                changes['tool_ids'] = {'old': agent.tool_ids, 'new': new_tool_ids}
                agent.tool_ids = new_tool_ids
        
        # Update tags if provided
        if 'tags' in data and data['tags'] != agent.tags:
            changes['tags'] = {'old': agent.tags, 'new': data['tags']}
            agent.tags = data['tags']
        
        # Update active status if provided (Admin only)
        if 'is_active' in data and user.has_role('Admin'):
            if data['is_active'] != agent.is_active:
                changes['is_active'] = {'old': agent.is_active, 'new': data['is_active']}
                agent.is_active = data['is_active']
        
        if changes:
            agent.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log activity
            log_activity(user.id, 'agent_updated', {
                'agent_id': agent.id,
                'agent_name': agent.name,
                'changes': changes
            }, 'agent', agent.id)
            
            return jsonify({
                'success': True,
                'message': 'Agent updated successfully',
                'agent': agent.to_dict(),
                'changes': changes
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No changes detected',
                'agent': agent.to_dict()
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update agent error: {str(e)}")
        return jsonify({'error': 'Failed to update agent'}), 500

@agents_bp.route('/<int:agent_id>', methods=['DELETE'])
@require_role(['Admin', 'Developer'])
def delete_agent(agent_id):
    """Delete an agent"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        agent = Agent.query.get_or_404(agent_id)
        
        # Check permissions
        if not user.has_role('Admin') and agent.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if agent has running executions
        running_executions = AgentExecution.query.filter_by(
            agent_id=agent_id, 
            status='running'
        ).count()
        
        if running_executions > 0:
            return jsonify({
                'error': f'Cannot delete agent with {running_executions} running executions'
            }), 400
        
        # Soft delete - mark as inactive first
        agent.is_active = False
        agent.updated_at = datetime.utcnow()
        
        # Log activity
        log_activity(user.id, 'agent_deleted', {
            'agent_id': agent.id,
            'agent_name': agent.name
        }, 'agent', agent.id)
        
        # If user confirms hard delete, remove from database
        if request.args.get('hard_delete') == 'true' and user.has_role('Admin'):
            db.session.delete(agent)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Agent deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete agent error: {str(e)}")
        return jsonify({'error': 'Failed to delete agent'}), 500

@agents_bp.route('/<int:agent_id>/execute', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def execute_agent(agent_id):
    """Execute an agent with provided input"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        agent = Agent.query.get_or_404(agent_id)
        
        # Check permissions
        if not user.has_role('Admin'):
            if not agent.is_approved or not agent.is_active:
                return jsonify({'error': 'Agent not available for execution'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        input_data = data.get('input', {})
        
        # Create execution record
        execution = AgentExecution(
            agent_id=agent.id,
            input_data=input_data,
            status='running',
            executed_by=user.id,
            model_id=agent.model_id,
            started_at=datetime.utcnow()
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # Start async execution
        execution_thread = Thread(
            target=_execute_agent_async,
            args=(execution.id, agent.id, input_data, user.id)
        )
        execution_thread.start()
        
        # Log activity
        log_activity(user.id, 'agent_executed', {
            'agent_id': agent.id,
            'agent_name': agent.name,
            'execution_id': execution.id
        }, 'agent', agent.id)
        
        return jsonify({
            'success': True,
            'message': 'Agent execution started',
            'execution_id': execution.id,
            'execution': execution.to_dict()
        }), 202
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Execute agent error: {str(e)}")
        return jsonify({'error': 'Failed to start agent execution'}), 500

@agents_bp.route('/<int:agent_id>/executions', methods=['GET'])
def get_agent_executions(agent_id):
    """Get execution history for an agent"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        agent = Agent.query.get_or_404(agent_id)
        
        # Check permissions
        if not user.has_role('Admin'):
            if not agent.is_approved and agent.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status', '').strip()
        
        # Build query
        query = AgentExecution.query.filter_by(agent_id=agent_id)
        
        if status_filter:
            query = query.filter(AgentExecution.status == status_filter)
        
        # Get paginated results
        executions = query.order_by(AgentExecution.started_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'executions': [execution.to_dict() for execution in executions.items],
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
        current_app.logger.error(f"Get agent executions error: {str(e)}")
        return jsonify({'error': 'Failed to fetch executions'}), 500

@agents_bp.route('/executions/<int:execution_id>', methods=['GET'])
def get_execution_details(execution_id):
    """Get detailed execution information"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        execution = AgentExecution.query.get_or_404(execution_id)
        agent = execution.agent
        
        # Check permissions
        if not user.has_role('Admin'):
            if execution.executed_by != user.id and agent.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        execution_data = execution.to_dict()
        
        # Add trace data if available
        if execution.trace_data:
            execution_data['trace'] = execution.trace_data
        
        return jsonify({
            'success': True,
            'execution': execution_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get execution details error: {str(e)}")
        return jsonify({'error': 'Failed to fetch execution details'}), 500

@agents_bp.route('/<int:agent_id>/approve', methods=['POST'])
@require_role(['Admin'])
def approve_agent(agent_id):
    """Approve or reject an agent"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        agent = Agent.query.get_or_404(agent_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        approve = data.get('approve', True)
        comment = data.get('comment', '')
        
        agent.is_approved = approve
        agent.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'agent_approved' if approve else 'agent_rejected', {
            'agent_id': agent.id,
            'agent_name': agent.name,
            'comment': comment
        }, 'agent', agent.id)
        
        return jsonify({
            'success': True,
            'message': f'Agent {"approved" if approve else "rejected"} successfully',
            'agent': agent.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve agent error: {str(e)}")
        return jsonify({'error': 'Failed to process agent approval'}), 500

@agents_bp.route('/templates', methods=['GET'])
def get_agent_templates():
    """Get predefined agent templates"""
    try:
        templates = [
            {
                'name': 'Data Analyst Agent',
                'description': 'Analyzes data and provides insights',
                'execution_pattern': 'sequential',
                'max_turns': 5,
                'max_tokens': 4000,
                'temperature': 0.3,
                'memory_type': 'per_session',
                'suggested_tools': ['data_analysis', 'chart_generator'],
                'tags': ['data', 'analysis', 'insights']
            },
            {
                'name': 'Content Writer Agent',
                'description': 'Creates and edits written content',
                'execution_pattern': 'sequential',
                'max_turns': 3,
                'max_tokens': 6000,
                'temperature': 0.7,
                'memory_type': 'stateless',
                'suggested_tools': ['web_search', 'grammar_check'],
                'tags': ['content', 'writing', 'creative']
            },
            {
                'name': 'Research Assistant Agent',
                'description': 'Conducts research and summarizes findings',
                'execution_pattern': 'parallel',
                'max_turns': 8,
                'max_tokens': 8000,
                'temperature': 0.4,
                'memory_type': 'global',
                'suggested_tools': ['web_search', 'document_reader', 'summarizer'],
                'tags': ['research', 'analysis', 'summarization']
            }
        ]
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        current_app.logger.error(f"Get agent templates error: {str(e)}")
        return jsonify({'error': 'Failed to fetch agent templates'}), 500

def _execute_agent_async(execution_id, agent_id, input_data, user_id):
    """Asynchronously execute an agent (simplified implementation)"""
    try:
        from app import app
        
        with app.app_context():
            execution = AgentExecution.query.get(execution_id)
            agent = Agent.query.get(agent_id)
            
            if not execution or not agent:
                return
            
            # Simulate execution process
            import time
            import random
            
            # Simulate processing time
            processing_time = random.uniform(2, 10)
            time.sleep(processing_time)
            
            # Simulate success/failure
            success = random.choice([True, True, True, False])  # 75% success rate
            
            if success:
                # Simulate successful execution
                output_data = {
                    'result': f'Agent {agent.name} executed successfully',
                    'input_processed': input_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                execution.status = 'completed'
                execution.output_data = output_data
                execution.tokens_used = random.randint(100, 2000)
                execution.cost = round(execution.tokens_used * 0.0001, 3)
                execution.trace_data = {
                    'steps': [
                        {'step': 1, 'action': 'Input validation', 'status': 'completed'},
                        {'step': 2, 'action': 'Model execution', 'status': 'completed'},
                        {'step': 3, 'action': 'Output generation', 'status': 'completed'}
                    ]
                }
            else:
                # Simulate failure
                execution.status = 'failed'
                execution.error_message = 'Simulated execution error'
                execution.tokens_used = random.randint(50, 500)
                execution.cost = round(execution.tokens_used * 0.0001, 3)
            
            execution.execution_time = round(processing_time, 2)
            execution.completed_at = datetime.utcnow()
            
            db.session.commit()
            
    except Exception as e:
        current_app.logger.error(f"Async execution error: {str(e)}")
        # Update execution with error status
        try:
            with app.app_context():
                execution = AgentExecution.query.get(execution_id)
                if execution:
                    execution.status = 'failed'
                    execution.error_message = str(e)
                    execution.completed_at = datetime.utcnow()
                    db.session.commit()
        except:
            pass