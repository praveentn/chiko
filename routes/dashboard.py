# routes/dashboard.py
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import func, text
from datetime import datetime, timedelta
import traceback

from extensions import db                       # ← pull db from the shared extensions module
from models.user import User
from models.model import Model
from models.persona import Persona
from models.agent import Agent, AgentExecution
from models.workflow import Workflow, WorkflowExecution
from models.tool import Tool
from models.audit import AuditLog
from services.auth_service import get_current_user

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get base statistics
        stats = {
            'agents': get_agent_stats(user),
            'workflows': get_workflow_stats(user),
            'executions': get_execution_stats(user),
            'models': get_model_stats(user),
            'personas': get_persona_stats(user),
            'tools': get_tool_stats(user),
            'cost': get_cost_stats(user),
            'success_rate': get_success_rate(user)
        }
        
        # Get recent activity
        recent_activity = get_recent_activity(user, limit=20)
        
        # Get recent items
        recent_items = {
            'agents': get_recent_agents(user, limit=5),
            'workflows': get_recent_workflows(user, limit=5),
            'executions': get_recent_executions(user, limit=10)
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'recent_activity': recent_activity,
            'recent': recent_items
        })
        
    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Failed to load dashboard statistics'}), 500

def get_agent_stats(user):
    """Get agent-related statistics"""
    try:
        base_query = Agent.query
        
        # Filter by user access level
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                (Agent.is_approved == True) | (Agent.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                (Agent.created_by == user.id) | (Agent.is_approved == True)
            )
        # Admin can see all
        
        total = base_query.count()
        active = base_query.filter_by(is_active=True).count()
        user_created = base_query.filter_by(created_by=user.id).count()
        approved = base_query.filter_by(is_approved=True).count()
        
        return {
            'total': total,
            'active': active,
            'user_created': user_created,
            'approved': approved,
            'pending_approval': total - approved
        }
    except Exception as e:
        current_app.logger.error(f"Agent stats error: {str(e)}")
        return {'total': 0, 'active': 0, 'user_created': 0, 'approved': 0, 'pending_approval': 0}

def get_workflow_stats(user):
    """Get workflow-related statistics"""
    try:
        base_query = Workflow.query
        
        # Filter by user access level
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                (Workflow.is_approved == True) | (Workflow.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                (Workflow.created_by == user.id) | (Workflow.is_approved == True)
            )
        
        total = base_query.count()
        active = base_query.filter_by(is_active=True).count()
        user_created = base_query.filter_by(created_by=user.id).count()
        approved = base_query.filter_by(is_approved=True).count()
        
        return {
            'total': total,
            'active': active,
            'user_created': user_created,
            'approved': approved,
            'pending_approval': total - approved
        }
    except Exception as e:
        current_app.logger.error(f"Workflow stats error: {str(e)}")
        return {'total': 0, 'active': 0, 'user_created': 0, 'approved': 0, 'pending_approval': 0}

def get_execution_stats(user):
    """Get execution statistics"""
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # Base query for executions user can see
        base_query = AgentExecution.query
        
        if user.role.name != 'Admin':
            # Filter executions by user's agents or executions they initiated
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).subquery()
            base_query = base_query.filter(
                (AgentExecution.executed_by == user.id) |
                (AgentExecution.agent_id.in_(user_agent_ids))
            )
        
        total = base_query.count()
        today = base_query.filter(AgentExecution.started_at >= today_start).count()
        this_week = base_query.filter(AgentExecution.started_at >= week_start).count()
        this_month = base_query.filter(AgentExecution.started_at >= month_start).count()
        
        successful = base_query.filter_by(status='completed').count()
        failed = base_query.filter_by(status='failed').count()
        running = base_query.filter_by(status='running').count()
        
        return {
            'total': total,
            'today': today,
            'this_week': this_week,
            'this_month': this_month,
            'successful': successful,
            'failed': failed,
            'running': running
        }
    except Exception as e:
        current_app.logger.error(f"Execution stats error: {str(e)}")
        return {'total': 0, 'today': 0, 'this_week': 0, 'this_month': 0, 'successful': 0, 'failed': 0, 'running': 0}

def get_model_stats(user):
    """Get model statistics"""
    try:
        total = Model.query.count()
        active = Model.query.filter_by(is_active=True).count()
        approved = Model.query.filter_by(is_approved=True).count()
        
        if user.role.name != 'Admin':
            # Non-admin users only see approved models
            accessible = approved
        else:
            accessible = total
        
        return {
            'total': total,
            'active': active,
            'approved': approved,
            'accessible': accessible,
            'pending_approval': total - approved
        }
    except Exception as e:
        current_app.logger.error(f"Model stats error: {str(e)}")
        return {'total': 0, 'active': 0, 'approved': 0, 'accessible': 0, 'pending_approval': 0}

def get_persona_stats(user):
    """Get persona statistics"""
    try:
        base_query = Persona.query
        
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                (Persona.is_approved == True) | (Persona.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                (Persona.created_by == user.id) | (Persona.is_approved == True)
            )
        
        total = base_query.count()
        user_created = base_query.filter_by(created_by=user.id).count()
        approved = Persona.query.filter_by(is_approved=True).count()
        public = Persona.query.filter_by(visibility='public').count()
        
        return {
            'total': total,
            'user_created': user_created,
            'approved': approved,
            'public': public,
            'pending_approval': Persona.query.count() - approved
        }
    except Exception as e:
        current_app.logger.error(f"Persona stats error: {str(e)}")
        return {'total': 0, 'user_created': 0, 'approved': 0, 'public': 0, 'pending_approval': 0}

def get_tool_stats(user):
    """Get tool statistics"""
    try:
        total = Tool.query.count()
        active = Tool.query.filter_by(is_active=True).count()
        approved = Tool.query.filter_by(is_approved=True).count()
        healthy = Tool.query.filter_by(health_status='healthy').count()
        
        return {
            'total': total,
            'active': active,
            'approved': approved,
            'healthy': healthy,
            'pending_approval': total - approved
        }
    except Exception as e:
        current_app.logger.error(f"Tool stats error: {str(e)}")
        return {'total': 0, 'active': 0, 'approved': 0, 'healthy': 0, 'pending_approval': 0}

def get_cost_stats(user):
    """Get cost statistics"""
    try:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        
        # Base query for executions user can see
        base_query = AgentExecution.query
        
        if user.role.name != 'Admin':
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).subquery()
            base_query = base_query.filter(
                (AgentExecution.executed_by == user.id) |
                (AgentExecution.agent_id.in_(user_agent_ids))
            )
        
        # Current month cost
        this_month = base_query.filter(
            AgentExecution.started_at >= month_start
        ).with_entities(func.sum(AgentExecution.cost)).scalar() or 0
        
        # Last month cost
        last_month = base_query.filter(
            AgentExecution.started_at >= last_month_start,
            AgentExecution.started_at < month_start
        ).with_entities(func.sum(AgentExecution.cost)).scalar() or 0
        
        # Total cost
        total = base_query.with_entities(func.sum(AgentExecution.cost)).scalar() or 0
        
        return {
            'total': round(total, 2),
            'this_month': round(this_month, 2),
            'last_month': round(last_month, 2),
            'average_per_execution': round(total / max(base_query.count(), 1), 4)
        }
    except Exception as e:
        current_app.logger.error(f"Cost stats error: {str(e)}")
        return {'total': 0, 'this_month': 0, 'last_month': 0, 'average_per_execution': 0}

def get_success_rate(user):
    """Get overall success rate"""
    try:
        base_query = AgentExecution.query
        
        if user.role.name != 'Admin':
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).subquery()
            base_query = base_query.filter(
                (AgentExecution.executed_by == user.id) |
                (AgentExecution.agent_id.in_(user_agent_ids))
            )
        
        total = base_query.count()
        successful = base_query.filter_by(status='completed').count()
        
        if total == 0:
            return 0
        
        return round((successful / total) * 100, 1)
    except Exception as e:
        current_app.logger.error(f"Success rate error: {str(e)}")
        return 0

def get_recent_activity(user, limit=20):
    """Get recent user activity"""
    try:
        query = AuditLog.query
        
        if user.role.name != 'Admin':
            # Non-admin users only see their own activity
            query = query.filter_by(user_id=user.id)
        
        recent_logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        activity = []
        for log in recent_logs:
            activity.append({
                'id': log.id,
                'action': log.action,
                'description': format_activity_description(log),
                'user_email': log.user.email if log.user else 'System',
                'created_at': log.created_at.isoformat(),
                'success': log.success,
                'resource_type': log.resource_type
            })
        
        return activity
    except Exception as e:
        current_app.logger.error(f"Recent activity error: {str(e)}")
        return []

def format_activity_description(log):
    """Format activity description for display"""
    action_descriptions = {
        'agent_created': 'Created a new agent',
        'agent_executed': 'Executed an agent',
        'workflow_created': 'Created a new workflow',
        'workflow_executed': 'Executed a workflow',
        'model_created': 'Added a new model',
        'persona_created': 'Created a new persona',
        'tool_created': 'Registered a new tool',
        'user_login': 'Logged in',
        'user_logout': 'Logged out',
        'sql_execution': 'Executed SQL query',
        'llm_completion': 'Made LLM API call'
    }
    
    base_description = action_descriptions.get(log.action, log.action.replace('_', ' ').title())
    
    # Add resource name if available
    if log.details and isinstance(log.details, dict):
        resource_name = log.details.get('resource_name') or log.details.get('name')
        if resource_name:
            base_description += f': {resource_name}'
    
    return base_description

def get_recent_agents(user, limit=5):
    """Get recently created agents"""
    try:
        query = Agent.query
        
        if user.role.name == 'Business User':
            query = query.filter(
                (Agent.is_approved == True) | (Agent.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            query = query.filter(
                (Agent.created_by == user.id) | (Agent.is_approved == True)
            )
        
        agents = query.order_by(Agent.created_at.desc()).limit(limit).all()
        
        return [
            {
                'id': agent.id,
                'name': agent.name,
                'description': agent.description,
                'status': 'approved' if agent.is_approved else 'pending',
                'created_at': agent.created_at.isoformat(),
                'created_by': agent.created_by_user.full_name if agent.created_by_user else None
            }
            for agent in agents
        ]
    except Exception as e:
        current_app.logger.error(f"Recent agents error: {str(e)}")
        return []

def get_recent_workflows(user, limit=5):
    """Get recently created workflows"""
    try:
        query = Workflow.query
        
        if user.role.name == 'Business User':
            query = query.filter(
                (Workflow.is_approved == True) | (Workflow.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            query = query.filter(
                (Workflow.created_by == user.id) | (Workflow.is_approved == True)
            )
        
        workflows = query.order_by(Workflow.created_at.desc()).limit(limit).all()
        
        return [
            {
                'id': workflow.id,
                'name': workflow.name,
                'description': workflow.description,
                'status': 'approved' if workflow.is_approved else 'pending',
                'created_at': workflow.created_at.isoformat(),
                'created_by': workflow.created_by_user.full_name if workflow.created_by_user else None
            }
            for workflow in workflows
        ]
    except Exception as e:
        current_app.logger.error(f"Recent workflows error: {str(e)}")
        return []

def get_recent_executions(user, limit=10):
    """Get recent executions"""
    try:
        base_query = AgentExecution.query
        
        if user.role.name != 'Admin':
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).subquery()
            base_query = base_query.filter(
                (AgentExecution.executed_by == user.id) |
                (AgentExecution.agent_id.in_(user_agent_ids))
            )
        
        executions = base_query.order_by(AgentExecution.started_at.desc()).limit(limit).all()
        
        return [
            {
                'id': execution.id,
                'agent_name': execution.agent.name if execution.agent else 'Unknown',
                'status': execution.status,
                'cost': round(execution.cost, 4) if execution.cost else 0,
                'tokens_used': execution.tokens_used,
                'execution_time': round(execution.execution_time, 3) if execution.execution_time else None,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'error_message': execution.error_message
            }
            for execution in executions
        ]
    except Exception as e:
        current_app.logger.error(f"Recent executions error: {str(e)}")
        return []

@dashboard_bp.route('/health', methods=['GET'])
def get_system_health():
    """Get system health metrics"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user or user.role.name != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        # Database health
        try:
            db.session.execute(text('SELECT 1'))
            db_status = 'healthy'
            db_message = 'Database connection successful'
        except Exception as e:
            db_status = 'unhealthy'
            db_message = f'Database error: {str(e)}'
        
        # LLM service health
        from services.llm_service import llm_service
        try:
            models = llm_service.get_available_models()
            llm_status = 'healthy' if models else 'warning'
            llm_message = f'{len(models)} models available'
        except Exception as e:
            llm_status = 'unhealthy'
            llm_message = f'LLM service error: {str(e)}'
        
        # System metrics
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy' if db_status == 'healthy' and llm_status in ['healthy', 'warning'] else 'unhealthy',
            'components': {
                'database': {
                    'status': db_status,
                    'message': db_message
                },
                'llm_service': {
                    'status': llm_status,
                    'message': llm_message
                }
            },
            'system_metrics': {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'disk_percent': round((disk.used / disk.total) * 100, 1),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2)
            }
        }
        
        return jsonify({
            'success': True,
            'health': health_data
        })
        
    except ImportError:
        # psutil not available
        return jsonify({
            'success': True,
            'health': {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'healthy',
                'components': {
                    'database': {'status': 'healthy', 'message': 'Database connection successful'},
                    'llm_service': {'status': 'healthy', 'message': 'LLM service operational'}
                },
                'system_metrics': {
                    'message': 'System metrics unavailable (psutil not installed)'
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Health check error: {str(e)}")
        return jsonify({'error': 'Health check failed'}), 500