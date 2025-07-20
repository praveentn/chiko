# routes/dashboard.py
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import func, text, and_, or_
from datetime import datetime, timedelta
import traceback

from extensions import db
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
        current_user_id = int(get_jwt_identity())  # Convert back to int
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get current time boundaries
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        
        # Get base statistics
        stats = {
            'agents': get_agent_stats(user, today_start, week_start, month_start),
            'workflows': get_workflow_stats(user, today_start, week_start, month_start),
            'executions': get_execution_stats(user, today_start, week_start, month_start),
            'models': get_model_stats(user),
            'personas': get_persona_stats(user),
            'tools': get_tool_stats(user),
            'cost': get_cost_stats(user, today_start, week_start, month_start),
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

def get_agent_stats(user, today_start, week_start, month_start):
    """Get agent-related statistics"""
    try:
        base_query = Agent.query
        
        # Filter by user access level
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                or_(Agent.is_approved == True, Agent.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                or_(Agent.is_approved == True, Agent.created_by == user.id)
            )
        
        total = base_query.count()
        active = base_query.filter_by(is_active=True).count()
        approved = base_query.filter_by(is_approved=True).count()
        created_today = base_query.filter(Agent.created_at >= today_start).count()
        created_this_week = base_query.filter(Agent.created_at >= week_start).count()
        created_this_month = base_query.filter(Agent.created_at >= month_start).count()
        
        # User's own agents
        my_agents = Agent.query.filter_by(created_by=user.id).count()
        
        return {
            'total': total,
            'active': active,
            'approved': approved,
            'my_agents': my_agents,
            'created_today': created_today,
            'created_this_week': created_this_week,
            'created_this_month': created_this_month,
            'pending_approval': total - approved
        }
        
    except Exception as e:
        current_app.logger.error(f"Agent stats error: {str(e)}")
        return {
            'total': 0, 'active': 0, 'approved': 0, 'my_agents': 0,
            'created_today': 0, 'created_this_week': 0, 'created_this_month': 0,
            'pending_approval': 0
        }

def get_workflow_stats(user, today_start, week_start, month_start):
    """Get workflow-related statistics"""
    try:
        base_query = Workflow.query
        
        # Filter by user access level
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                or_(Workflow.is_approved == True, Workflow.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                or_(Workflow.is_approved == True, Workflow.created_by == user.id)
            )
        
        total = base_query.count()
        active = base_query.filter_by(is_active=True).count()
        approved = base_query.filter_by(is_approved=True).count()
        created_today = base_query.filter(Workflow.created_at >= today_start).count()
        created_this_week = base_query.filter(Workflow.created_at >= week_start).count()
        created_this_month = base_query.filter(Workflow.created_at >= month_start).count()
        
        # User's own workflows
        my_workflows = Workflow.query.filter_by(created_by=user.id).count()
        
        return {
            'total': total,
            'active': active,
            'approved': approved,
            'my_workflows': my_workflows,
            'created_today': created_today,
            'created_this_week': created_this_week,
            'created_this_month': created_this_month,
            'pending_approval': total - approved
        }
        
    except Exception as e:
        current_app.logger.error(f"Workflow stats error: {str(e)}")
        return {
            'total': 0, 'active': 0, 'approved': 0, 'my_workflows': 0,
            'created_today': 0, 'created_this_week': 0, 'created_this_month': 0,
            'pending_approval': 0
        }

def get_execution_stats(user, today_start, week_start, month_start):
    """Get execution statistics"""
    try:
        # Base query for executions user can see
        if user.role.name == 'Admin':
            agent_executions = AgentExecution.query
            workflow_executions = WorkflowExecution.query
        else:
            # Users can see executions of their own agents/workflows or executions they initiated
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).scalar_subquery()
            user_workflow_ids = db.session.query(Workflow.id).filter_by(created_by=user.id).scalar_subquery()
            
            agent_executions = AgentExecution.query.filter(
                or_(
                    AgentExecution.executed_by == user.id,
                    AgentExecution.agent_id.in_(user_agent_ids)
                )
            )
            workflow_executions = WorkflowExecution.query.filter(
                or_(
                    WorkflowExecution.executed_by == user.id,
                    WorkflowExecution.workflow_id.in_(user_workflow_ids)
                )
            )
        
        # Agent execution stats
        agent_total = agent_executions.count()
        agent_today = agent_executions.filter(AgentExecution.started_at >= today_start).count()
        agent_week = agent_executions.filter(AgentExecution.started_at >= week_start).count()
        agent_month = agent_executions.filter(AgentExecution.started_at >= month_start).count()
        agent_successful = agent_executions.filter_by(status='completed').count()
        agent_failed = agent_executions.filter_by(status='failed').count()
        agent_running = agent_executions.filter_by(status='running').count()
        
        # Workflow execution stats
        workflow_total = workflow_executions.count()
        workflow_today = workflow_executions.filter(WorkflowExecution.started_at >= today_start).count()
        workflow_week = workflow_executions.filter(WorkflowExecution.started_at >= week_start).count()
        workflow_month = workflow_executions.filter(WorkflowExecution.started_at >= month_start).count()
        workflow_successful = workflow_executions.filter_by(status='completed').count()
        workflow_failed = workflow_executions.filter_by(status='failed').count()
        workflow_running = workflow_executions.filter_by(status='running').count()
        
        # Combined stats
        total = agent_total + workflow_total
        today = agent_today + workflow_today
        week = agent_week + workflow_week
        month = agent_month + workflow_month
        successful = agent_successful + workflow_successful
        failed = agent_failed + workflow_failed
        running = agent_running + workflow_running
        
        return {
            'total': total,
            'today': today,
            'this_week': week,
            'this_month': month,
            'successful': successful,
            'failed': failed,
            'running': running,
            'agents': {
                'total': agent_total,
                'successful': agent_successful,
                'failed': agent_failed,
                'running': agent_running
            },
            'workflows': {
                'total': workflow_total,
                'successful': workflow_successful,
                'failed': workflow_failed,
                'running': workflow_running
            }
        }
        
    except Exception as e:
        current_app.logger.error(f"Execution stats error: {str(e)}")
        return {
            'total': 0, 'today': 0, 'this_week': 0, 'this_month': 0,
            'successful': 0, 'failed': 0, 'running': 0,
            'agents': {'total': 0, 'successful': 0, 'failed': 0, 'running': 0},
            'workflows': {'total': 0, 'successful': 0, 'failed': 0, 'running': 0}
        }

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
        return {
            'total': 0, 'active': 0, 'approved': 0,
            'accessible': 0, 'pending_approval': 0
        }

def get_persona_stats(user):
    """Get persona statistics"""
    try:
        base_query = Persona.query
        
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                or_(Persona.is_approved == True, Persona.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                or_(Persona.is_approved == True, Persona.created_by == user.id)
            )
        
        total = base_query.count()
        active = base_query.filter_by(is_active=True).count()
        approved = base_query.filter_by(is_approved=True).count()
        
        # User's own personas
        my_personas = Persona.query.filter_by(created_by=user.id).count()
        
        return {
            'total': total,
            'active': active,
            'approved': approved,
            'my_personas': my_personas,
            'pending_approval': total - approved
        }
        
    except Exception as e:
        current_app.logger.error(f"Persona stats error: {str(e)}")
        return {
            'total': 0, 'active': 0, 'approved': 0,
            'my_personas': 0, 'pending_approval': 0
        }

def get_tool_stats(user):
    """Get tool statistics"""
    try:
        base_query = Tool.query
        
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                or_(Tool.is_approved == True, Tool.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                or_(Tool.is_approved == True, Tool.created_by == user.id)
            )
        
        total = base_query.count()
        active = base_query.filter_by(is_active=True).count()
        approved = base_query.filter_by(is_approved=True).count()
        
        # User's own tools
        my_tools = Tool.query.filter_by(created_by=user.id).count()
        
        return {
            'total': total,
            'active': active,
            'approved': approved,
            'my_tools': my_tools,
            'pending_approval': total - approved
        }
        
    except Exception as e:
        current_app.logger.error(f"Tool stats error: {str(e)}")
        return {
            'total': 0, 'active': 0, 'approved': 0,
            'my_tools': 0, 'pending_approval': 0
        }

def get_cost_stats(user, today_start, week_start, month_start):
    """Get cost statistics"""
    try:
        # This would typically aggregate costs from executions
        # For now, return mock data structure
        return {
            'total': round(0.00, 2),
            'today': round(0.00, 2),
            'this_week': round(0.00, 2),
            'this_month': round(0.00, 2),
            'currency': 'USD'
        }
        
    except Exception as e:
        current_app.logger.error(f"Cost stats error: {str(e)}")
        return {
            'total': 0.00, 'today': 0.00, 'this_week': 0.00,
            'this_month': 0.00, 'currency': 'USD'
        }

def get_success_rate(user):
    """Get overall success rate"""
    try:
        # Calculate success rate from executions
        if user.role.name == 'Admin':
            agent_executions = AgentExecution.query
            workflow_executions = WorkflowExecution.query
        else:
            # Users can see executions of their own agents/workflows or executions they initiated
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).scalar_subquery()
            user_workflow_ids = db.session.query(Workflow.id).filter_by(created_by=user.id).scalar_subquery()
            
            agent_executions = AgentExecution.query.filter(
                or_(
                    AgentExecution.executed_by == user.id,
                    AgentExecution.agent_id.in_(user_agent_ids)
                )
            )
            workflow_executions = WorkflowExecution.query.filter(
                or_(
                    WorkflowExecution.executed_by == user.id,
                    WorkflowExecution.workflow_id.in_(user_workflow_ids)
                )
            )
        
        total_executions = agent_executions.count() + workflow_executions.count()
        if total_executions == 0:
            return round(0.0, 2)
        
        successful_executions = (
            agent_executions.filter_by(status='completed').count() +
            workflow_executions.filter_by(status='completed').count()
        )
        
        success_rate = (successful_executions / total_executions) * 100
        return round(success_rate, 2)
        
    except Exception as e:
        current_app.logger.error(f"Success rate error: {str(e)}")
        return 0.0

def get_recent_activity(user, limit=20):
    """Get recent activity for the user"""
    try:
        # Get recent audit logs
        if user.role.name == 'Admin':
            # Admins can see all activity
            activities = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        else:
            # Users see their own activity
            activities = AuditLog.query.filter_by(user_id=user.id).order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return [
            {
                'id': activity.id,
                'action': activity.action,
                'resource_type': activity.resource_type,
                'resource_id': activity.resource_id,
                'user_id': activity.user_id,
                'details': activity.details,
                'created_at': activity.created_at.isoformat() if activity.created_at else None
            }
            for activity in activities
        ]
        
    except Exception as e:
        current_app.logger.error(f"Recent activity error: {str(e)}")
        return []

def get_recent_agents(user, limit=5):
    """Get recently created/updated agents"""
    try:
        base_query = Agent.query
        
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                or_(Agent.is_approved == True, Agent.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                or_(Agent.is_approved == True, Agent.created_by == user.id)
            )
        
        agents = base_query.order_by(Agent.updated_at.desc()).limit(limit).all()
        return [agent.to_dict() for agent in agents]
        
    except Exception as e:
        current_app.logger.error(f"Recent agents error: {str(e)}")
        return []

def get_recent_workflows(user, limit=5):
    """Get recently created/updated workflows"""
    try:
        base_query = Workflow.query
        
        if user.role.name == 'Business User':
            base_query = base_query.filter(
                or_(Workflow.is_approved == True, Workflow.created_by == user.id)
            )
        elif user.role.name == 'Developer':
            base_query = base_query.filter(
                or_(Workflow.is_approved == True, Workflow.created_by == user.id)
            )
        
        workflows = base_query.order_by(Workflow.updated_at.desc()).limit(limit).all()
        return [workflow.to_dict() for workflow in workflows]
        
    except Exception as e:
        current_app.logger.error(f"Recent workflows error: {str(e)}")
        return []

def get_recent_executions(user, limit=10):
    """Get recent executions"""
    try:
        if user.role.name == 'Admin':
            # Admin can see all executions
            agent_executions = AgentExecution.query.order_by(AgentExecution.started_at.desc()).limit(limit).all()
        else:
            # Users see executions they initiated or of their agents
            user_agent_ids = db.session.query(Agent.id).filter_by(created_by=user.id).scalar_subquery()
            agent_executions = AgentExecution.query.filter(
                or_(
                    AgentExecution.executed_by == user.id,
                    AgentExecution.agent_id.in_(user_agent_ids)
                )
            ).order_by(AgentExecution.started_at.desc()).limit(limit).all()
        
        return [execution.to_dict() for execution in agent_executions]
        
    except Exception as e:
        current_app.logger.error(f"Recent executions error: {str(e)}")
        return []