# routes/models.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime
import traceback

from extensions import db                       # ← pull db from the shared extensions module
from models.model import Model, ModelVersion
from models.user import User
from services.auth_service import get_current_user, require_role, log_activity, get_user_accessible_resources
from services.llm_service import llm_service

models_bp = Blueprint('models', __name__)

@models_bp.route('/', methods=['GET'])
def get_models():
    """Get list of models accessible to the user"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        provider_filter = request.args.get('provider', '').strip()
        status_filter = request.args.get('status', '').strip()
        
        # Base query with user access filtering
        query = get_user_accessible_resources(user, Model)
        
        # Apply search filter
        if search:
            query = query.filter(
                (Model.name.ilike(f'%{search}%')) |
                (Model.description.ilike(f'%{search}%')) |
                (Model.model_name.ilike(f'%{search}%'))
            )
        
        # Apply provider filter
        if provider_filter:
            query = query.filter(Model.provider == provider_filter)
        
        # Apply status filter
        if status_filter == 'active':
            query = query.filter(Model.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Model.is_active == False)
        elif status_filter == 'approved':
            query = query.filter(Model.is_approved == True)
        elif status_filter == 'pending':
            query = query.filter(Model.is_approved == False)
        
        # Get paginated results
        models = query.order_by(Model.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'models': [model.to_dict() for model in models.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': models.total,
                'total_pages': models.pages,
                'has_next': models.has_next,
                'has_prev': models.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get models error: {str(e)}")
        return jsonify({'error': 'Failed to fetch models'}), 500

@models_bp.route('/<int:model_id>', methods=['GET'])
def get_model(model_id):
    """Get a specific model by ID"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        model = Model.query.get_or_404(model_id)
        
        # Check access permissions
        if not user.has_role('Admin'):
            if not model.is_approved and model.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Get model versions
        versions = ModelVersion.query.filter_by(model_id=model_id).order_by(
            ModelVersion.created_at.desc()
        ).all()
        
        model_data = model.to_dict()
        model_data['versions'] = [
            {
                'id': version.id,
                'version': version.version,
                'is_active': version.is_active,
                'changelog': version.changelog,
                'created_at': version.created_at.isoformat() if version.created_at else None
            }
            for version in versions
        ]
        
        return jsonify({
            'success': True,
            'model': model_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get model error: {str(e)}")
        return jsonify({'error': 'Failed to fetch model'}), 500

@models_bp.route('/', methods=['POST'])
@require_role(['Admin', 'Developer'])
def create_model():
    """Create a new model"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'provider', 'model_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if model name already exists
        existing_model = Model.query.filter_by(name=data['name']).first()
        if existing_model:
            return jsonify({'error': 'Model with this name already exists'}), 400
        
        # Validate provider-specific configuration
        provider = data['provider']
        model_config = {
            'deployment_id': data.get('deployment_id'),
            'model_name': data['model_name'],
            'api_endpoint': data.get('api_endpoint'),
            'api_version': data.get('api_version'),
            'max_tokens': data.get('max_tokens'),
            'temperature': data.get('temperature')
        }
        
        # Validate configuration using LLM service
        if provider in ['azure_openai', 'openai']:
            validation_result = llm_service.validate_model_config(provider, model_config)
            if not validation_result['valid']:
                return jsonify({
                    'error': 'Invalid model configuration',
                    'details': validation_result['errors']
                }), 400
        
        # Create model
        model = Model(
            name=data['name'],
            provider=provider,
            deployment_id=data.get('deployment_id'),
            model_name=data['model_name'],
            api_endpoint=data.get('api_endpoint'),
            api_version=data.get('api_version'),
            context_window=data.get('context_window'),
            max_tokens=data.get('max_tokens'),
            temperature=data.get('temperature', 0.1),
            input_cost_per_token=data.get('input_cost_per_token'),
            output_cost_per_token=data.get('output_cost_per_token'),
            description=data.get('description'),
            tags=data.get('tags', []),
            configuration=data.get('configuration', {}),
            created_by=user.id,
            is_approved=user.has_role('Admin')  # Auto-approve for admins
        )
        
        db.session.add(model)
        db.session.flush()  # Get the model ID
        
        # Create initial version
        version = ModelVersion(
            model_id=model.id,
            version='1.0.0',
            configuration=model_config,
            changelog='Initial version',
            is_active=True,
            created_by=user.id
        )
        
        db.session.add(version)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'model_created', {
            'model_id': model.id,
            'model_name': model.name,
            'provider': model.provider
        }, 'model', model.id)
        
        return jsonify({
            'success': True,
            'message': 'Model created successfully',
            'model': model.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create model error: {str(e)}")
        return jsonify({'error': 'Failed to create model'}), 500

@models_bp.route('/<int:model_id>', methods=['PUT'])
@require_role(['Admin', 'Developer'])
def update_model(model_id):
    """Update an existing model"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        model = Model.query.get_or_404(model_id)
        
        # Check permissions
        if not user.has_role('Admin') and model.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Update model fields
        updatable_fields = [
            'name', 'description', 'api_endpoint', 'api_version',
            'context_window', 'max_tokens', 'temperature',
            'input_cost_per_token', 'output_cost_per_token',
            'tags', 'configuration'
        ]
        
        # Check for name conflicts
        if 'name' in data and data['name'] != model.name:
            existing_model = Model.query.filter_by(name=data['name']).first()
            if existing_model:
                return jsonify({'error': 'Model with this name already exists'}), 400
        
        changes = {}
        for field in updatable_fields:
            if field in data:
                old_value = getattr(model, field)
                new_value = data[field]
                
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
                    setattr(model, field, new_value)
        
        # Update status fields if admin
        if user.has_role('Admin'):
            if 'is_active' in data:
                old_active = model.is_active
                model.is_active = data['is_active']
                if old_active != model.is_active:
                    changes['is_active'] = {'old': old_active, 'new': model.is_active}
            
            if 'is_approved' in data:
                old_approved = model.is_approved
                model.is_approved = data['is_approved']
                if old_approved != model.is_approved:
                    changes['is_approved'] = {'old': old_approved, 'new': model.is_approved}
        
        if changes:
            model.updated_at = datetime.utcnow()
            
            # Create new version if significant changes
            if any(field in changes for field in ['api_endpoint', 'configuration', 'max_tokens', 'temperature']):
                # Get current version number
                latest_version = ModelVersion.query.filter_by(model_id=model_id).order_by(
                    ModelVersion.created_at.desc()
                ).first()
                
                if latest_version:
                    # Increment version number
                    try:
                        major, minor, patch = latest_version.version.split('.')
                        new_version = f"{major}.{int(minor) + 1}.0"
                    except:
                        new_version = f"{latest_version.version}.1"
                else:
                    new_version = "1.0.0"
                
                # Create new version
                version = ModelVersion(
                    model_id=model.id,
                    version=new_version,
                    configuration={
                        'api_endpoint': model.api_endpoint,
                        'api_version': model.api_version,
                        'max_tokens': model.max_tokens,
                        'temperature': model.temperature,
                        'configuration': model.configuration
                    },
                    changelog=f"Updated: {', '.join(changes.keys())}",
                    is_active=True,
                    created_by=user.id
                )
                
                # Deactivate previous version
                if latest_version:
                    latest_version.is_active = False
                
                db.session.add(version)
            
            db.session.commit()
            
            # Log activity
            log_activity(user.id, 'model_updated', {
                'model_id': model.id,
                'model_name': model.name,
                'changes': changes
            }, 'model', model.id)
            
            return jsonify({
                'success': True,
                'message': 'Model updated successfully',
                'model': model.to_dict(),
                'changes': changes
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No changes detected',
                'model': model.to_dict()
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update model error: {str(e)}")
        return jsonify({'error': 'Failed to update model'}), 500

@models_bp.route('/<int:model_id>', methods=['DELETE'])
@require_role(['Admin', 'Developer'])
def delete_model(model_id):
    """Delete a model"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        model = Model.query.get_or_404(model_id)
        
        # Check permissions
        if not user.has_role('Admin') and model.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if model is being used
        from models.agent import Agent
        agents_using_model = Agent.query.filter_by(model_id=model_id, is_active=True).count()
        
        if agents_using_model > 0:
            return jsonify({
                'error': f'Cannot delete model. It is being used by {agents_using_model} active agent(s)'
            }), 400
        
        model_name = model.name
        
        # Delete associated versions
        ModelVersion.query.filter_by(model_id=model_id).delete()
        
        # Delete the model
        db.session.delete(model)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'model_deleted', {
            'model_id': model_id,
            'model_name': model_name
        }, 'model', model_id)
        
        return jsonify({
            'success': True,
            'message': 'Model deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete model error: {str(e)}")
        return jsonify({'error': 'Failed to delete model'}), 500

@models_bp.route('/<int:model_id>/test', methods=['POST'])
@require_role(['Admin', 'Developer'])
def test_model(model_id):
    """Test connection to a model"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        model = Model.query.get_or_404(model_id)
        
        # Check permissions
        if not user.has_role('Admin') and model.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Test the model connection
        test_result = llm_service.test_model_connection(model_id)
        
        # Log the test
        log_activity(user.id, 'model_tested', {
            'model_id': model.id,
            'model_name': model.name,
            'test_result': test_result['success'],
            'error': test_result.get('error')
        }, 'model', model.id)
        
        return jsonify({
            'success': True,
            'test_result': test_result
        })
        
    except Exception as e:
        current_app.logger.error(f"Test model error: {str(e)}")
        return jsonify({'error': 'Failed to test model'}), 500

@models_bp.route('/<int:model_id>/approve', methods=['POST'])
@require_role(['Admin'])
def approve_model(model_id):
    """Approve a model for general use"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        model = Model.query.get_or_404(model_id)
        
        if model.is_approved:
            return jsonify({'error': 'Model is already approved'}), 400
        
        model.is_approved = True
        model.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'model_approved', {
            'model_id': model.id,
            'model_name': model.name
        }, 'model', model.id)
        
        return jsonify({
            'success': True,
            'message': 'Model approved successfully',
            'model': model.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve model error: {str(e)}")
        return jsonify({'error': 'Failed to approve model'}), 500

@models_bp.route('/providers', methods=['GET'])
def get_providers():
    """Get available model providers"""
    try:
        verify_jwt_in_request()
        
        providers = [
            {
                'name': 'azure_openai',
                'display_name': 'Azure OpenAI',
                'description': 'Microsoft Azure OpenAI Service',
                'supported_models': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'required_fields': ['deployment_id', 'api_endpoint', 'api_version'],
                'optional_fields': ['max_tokens', 'temperature', 'top_p']
            },
            {
                'name': 'openai',
                'display_name': 'OpenAI',
                'description': 'OpenAI API',
                'supported_models': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'required_fields': ['model_name'],
                'optional_fields': ['max_tokens', 'temperature', 'top_p', 'frequency_penalty', 'presence_penalty']
            }
        ]
        
        return jsonify({
            'success': True,
            'providers': providers
        })
        
    except Exception as e:
        current_app.logger.error(f"Get providers error: {str(e)}")
        return jsonify({'error': 'Failed to fetch providers'}), 500

@models_bp.route('/available', methods=['GET'])
def get_available_models():
    """Get available models from LLM service"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get available models from LLM service
        available_models = llm_service.get_available_models()
        
        return jsonify({
            'success': True,
            'available_models': available_models
        })
        
    except Exception as e:
        current_app.logger.error(f"Get available models error: {str(e)}")
        return jsonify({'error': 'Failed to fetch available models'}), 500

@models_bp.route('/<int:model_id>/usage', methods=['GET'])
def get_model_usage(model_id):
    """Get usage statistics for a model"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        model = Model.query.get_or_404(model_id)
        
        # Check permissions
        if not user.has_role('Admin') and model.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get usage statistics
        from models.agent import AgentExecution
        from sqlalchemy import func
        
        # Total executions
        total_executions = AgentExecution.query.filter_by(model_id=model_id).count()
        
        # Successful executions
        successful_executions = AgentExecution.query.filter_by(
            model_id=model_id, status='completed'
        ).count()
        
        # Total cost
        total_cost = db.session.query(func.sum(AgentExecution.cost)).filter_by(
            model_id=model_id
        ).scalar() or 0
        
        # Total tokens
        total_tokens = db.session.query(func.sum(AgentExecution.tokens_used)).filter_by(
            model_id=model_id
        ).scalar() or 0
        
        # Recent usage (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_executions = AgentExecution.query.filter(
            AgentExecution.model_id == model_id,
            AgentExecution.started_at >= thirty_days_ago
        ).count()
        
        usage_stats = {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': round((successful_executions / max(total_executions, 1)) * 100, 1),
            'total_cost': round(total_cost, 4),
            'total_tokens': total_tokens,
            'recent_executions_30d': recent_executions,
            'average_cost_per_execution': round(total_cost / max(total_executions, 1), 4),
            'average_tokens_per_execution': round(total_tokens / max(total_executions, 1), 0)
        }
        
        return jsonify({
            'success': True,
            'usage': usage_stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Get model usage error: {str(e)}")
        return jsonify({'error': 'Failed to fetch model usage'}), 500