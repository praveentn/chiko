# routes/personas.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime
import json
import traceback

from extensions import db                       # ← pull db from the shared extensions module
from models.persona import Persona, PersonaVersion
from models.user import User
from services.auth_service import get_current_user, require_role, log_activity, get_user_accessible_resources

personas_bp = Blueprint('personas', __name__)

@personas_bp.route('/', methods=['GET'])
def get_personas():
    """Get list of personas accessible to the user"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        visibility_filter = request.args.get('visibility', '').strip()
        status_filter = request.args.get('status', '').strip()
        
        # Base query with user access filtering
        query = get_user_accessible_resources(user, Persona)
        
        # Apply search filter
        if search:
            query = query.filter(
                (Persona.name.ilike(f'%{search}%')) |
                (Persona.description.ilike(f'%{search}%'))
            )
        
        # Apply visibility filter
        if visibility_filter:
            query = query.filter(Persona.visibility == visibility_filter)
        
        # Apply status filter
        if status_filter == 'approved':
            query = query.filter(Persona.is_approved == True)
        elif status_filter == 'pending':
            query = query.filter(Persona.is_approved == False)
        
        # Get paginated results
        personas = query.order_by(Persona.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'personas': [persona.to_dict() for persona in personas.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': personas.total,
                'total_pages': personas.pages,
                'has_next': personas.has_next,
                'has_prev': personas.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get personas error: {str(e)}")
        return jsonify({'error': 'Failed to fetch personas'}), 500

@personas_bp.route('/<int:persona_id>', methods=['GET'])
def get_persona(persona_id):
    """Get a specific persona by ID"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        persona = Persona.query.get_or_404(persona_id)
        
        # Check access permissions
        if not user.has_role('Admin'):
            if not persona.is_approved and persona.created_by != user.id:
                if persona.visibility == 'private':
                    return jsonify({'error': 'Access denied'}), 403
        
        # Get persona versions
        versions = PersonaVersion.query.filter_by(persona_id=persona_id).order_by(
            PersonaVersion.created_at.desc()
        ).all()
        
        persona_data = persona.to_dict()
        persona_data['versions'] = [
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
            'persona': persona_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get persona error: {str(e)}")
        return jsonify({'error': 'Failed to fetch persona'}), 500

@personas_bp.route('/', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def create_persona():
    """Create a new persona"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'system_prompt']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if persona name already exists for this user
        existing_persona = Persona.query.filter_by(
            name=data['name'], 
            created_by=user.id
        ).first()
        if existing_persona:
            return jsonify({'error': 'You already have a persona with this name'}), 400
        
        # Validate JSON schemas if provided
        input_schema = data.get('input_schema')
        output_schema = data.get('output_schema')
        
        if input_schema:
            try:
                if isinstance(input_schema, str):
                    input_schema = json.loads(input_schema)
                # Basic validation - should be a dict with proper schema structure
                if not isinstance(input_schema, dict):
                    raise ValueError("Input schema must be a valid JSON object")
            except (json.JSONDecodeError, ValueError) as e:
                return jsonify({'error': f'Invalid input schema: {str(e)}'}), 400
        
        if output_schema:
            try:
                if isinstance(output_schema, str):
                    output_schema = json.loads(output_schema)
                if not isinstance(output_schema, dict):
                    raise ValueError("Output schema must be a valid JSON object")
            except (json.JSONDecodeError, ValueError) as e:
                return jsonify({'error': f'Invalid output schema: {str(e)}'}), 400
        
        # Parse variables if provided
        variables = data.get('variables', {})
        if isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid variables format'}), 400
        
        # Create persona
        persona = Persona(
            name=data['name'],
            description=data.get('description'),
            system_prompt=data['system_prompt'],
            user_prompt_template=data.get('user_prompt_template'),
            input_schema=input_schema,
            output_schema=output_schema,
            visibility=data.get('visibility', 'private'),
            tags=data.get('tags', []),
            variables=variables,
            created_by=user.id,
            is_approved=user.has_role('Admin')  # Auto-approve for admins
        )
        
        db.session.add(persona)
        db.session.flush()  # Get the persona ID
        
        # Create initial version
        version = PersonaVersion(
            persona_id=persona.id,
            version='1.0.0',
            system_prompt=persona.system_prompt,
            user_prompt_template=persona.user_prompt_template,
            input_schema=persona.input_schema,
            output_schema=persona.output_schema,
            changelog='Initial version',
            is_active=True,
            created_by=user.id
        )
        
        db.session.add(version)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'persona_created', {
            'persona_id': persona.id,
            'persona_name': persona.name,
            'visibility': persona.visibility
        }, 'persona', persona.id)
        
        return jsonify({
            'success': True,
            'message': 'Persona created successfully',
            'persona': persona.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create persona error: {str(e)}")
        return jsonify({'error': 'Failed to create persona'}), 500

@personas_bp.route('/<int:persona_id>', methods=['PUT'])
@require_role(['Admin', 'Developer', 'Business User'])
def update_persona(persona_id):
    """Update an existing persona"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        persona = Persona.query.get_or_404(persona_id)
        
        # Check permissions
        if not user.has_role('Admin') and persona.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Update persona fields
        updatable_fields = [
            'name', 'description', 'system_prompt', 'user_prompt_template',
            'input_schema', 'output_schema', 'visibility', 'tags', 'variables'
        ]
        
        # Check for name conflicts
        if 'name' in data and data['name'] != persona.name:
            existing_persona = Persona.query.filter_by(
                name=data['name'], 
                created_by=user.id
            ).first()
            if existing_persona:
                return jsonify({'error': 'You already have a persona with this name'}), 400
        
        changes = {}
        significant_changes = False
        
        for field in updatable_fields:
            if field in data:
                old_value = getattr(persona, field)
                new_value = data[field]
                
                # Handle JSON fields
                if field in ['input_schema', 'output_schema', 'variables']:
                    if isinstance(new_value, str) and new_value:
                        try:
                            new_value = json.loads(new_value)
                        except json.JSONDecodeError:
                            return jsonify({'error': f'Invalid {field} format'}), 400
                
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
                    setattr(persona, field, new_value)
                    
                    # Check if this is a significant change that requires versioning
                    if field in ['system_prompt', 'user_prompt_template', 'input_schema', 'output_schema']:
                        significant_changes = True
        
        # Update approval status if admin
        if user.has_role('Admin'):
            if 'is_approved' in data:
                old_approved = persona.is_approved
                persona.is_approved = data['is_approved']
                if old_approved != persona.is_approved:
                    changes['is_approved'] = {'old': old_approved, 'new': persona.is_approved}
        
        if changes:
            persona.updated_at = datetime.utcnow()
            
            # Create new version if significant changes
            if significant_changes:
                # Get current version number
                latest_version = PersonaVersion.query.filter_by(persona_id=persona_id).order_by(
                    PersonaVersion.created_at.desc()
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
                version = PersonaVersion(
                    persona_id=persona.id,
                    version=new_version,
                    system_prompt=persona.system_prompt,
                    user_prompt_template=persona.user_prompt_template,
                    input_schema=persona.input_schema,
                    output_schema=persona.output_schema,
                    changelog=f"Updated: {', '.join([k for k in changes.keys() if k in ['system_prompt', 'user_prompt_template', 'input_schema', 'output_schema']])}",
                    is_active=True,
                    created_by=user.id
                )
                
                # Deactivate previous version
                if latest_version:
                    latest_version.is_active = False
                
                db.session.add(version)
            
            db.session.commit()
            
            # Log activity
            log_activity(user.id, 'persona_updated', {
                'persona_id': persona.id,
                'persona_name': persona.name,
                'changes': changes,
                'significant_changes': significant_changes
            }, 'persona', persona.id)
            
            return jsonify({
                'success': True,
                'message': 'Persona updated successfully',
                'persona': persona.to_dict(),
                'changes': changes
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No changes detected',
                'persona': persona.to_dict()
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update persona error: {str(e)}")
        return jsonify({'error': 'Failed to update persona'}), 500

@personas_bp.route('/<int:persona_id>', methods=['DELETE'])
@require_role(['Admin', 'Developer', 'Business User'])
def delete_persona(persona_id):
    """Delete a persona"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        persona = Persona.query.get_or_404(persona_id)
        
        # Check permissions
        if not user.has_role('Admin') and persona.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if persona is being used
        from models.agent import Agent
        agents_using_persona = Agent.query.filter_by(persona_id=persona_id, is_active=True).count()
        
        if agents_using_persona > 0:
            return jsonify({
                'error': f'Cannot delete persona. It is being used by {agents_using_persona} active agent(s)'
            }), 400
        
        persona_name = persona.name
        
        # Delete associated versions
        PersonaVersion.query.filter_by(persona_id=persona_id).delete()
        
        # Delete the persona
        db.session.delete(persona)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'persona_deleted', {
            'persona_id': persona_id,
            'persona_name': persona_name
        }, 'persona', persona_id)
        
        return jsonify({
            'success': True,
            'message': 'Persona deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete persona error: {str(e)}")
        return jsonify({'error': 'Failed to delete persona'}), 500

@personas_bp.route('/<int:persona_id>/approve', methods=['POST'])
@require_role(['Admin'])
def approve_persona(persona_id):
    """Approve a persona for general use"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        persona = Persona.query.get_or_404(persona_id)
        
        if persona.is_approved:
            return jsonify({'error': 'Persona is already approved'}), 400
        
        persona.is_approved = True
        persona.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'persona_approved', {
            'persona_id': persona.id,
            'persona_name': persona.name
        }, 'persona', persona.id)
        
        return jsonify({
            'success': True,
            'message': 'Persona approved successfully',
            'persona': persona.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve persona error: {str(e)}")
        return jsonify({'error': 'Failed to approve persona'}), 500

@personas_bp.route('/<int:persona_id>/duplicate', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def duplicate_persona(persona_id):
    """Create a duplicate of an existing persona"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        original_persona = Persona.query.get_or_404(persona_id)
        
        # Check access permissions
        if not user.has_role('Admin'):
            if not original_persona.is_approved and original_persona.created_by != user.id:
                if original_persona.visibility == 'private':
                    return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json() or {}
        new_name = data.get('name', f"{original_persona.name} (Copy)")
        
        # Check if new name already exists for this user
        existing_persona = Persona.query.filter_by(
            name=new_name,
            created_by=user.id
        ).first()
        if existing_persona:
            return jsonify({'error': 'You already have a persona with this name'}), 400
        
        # Create duplicate persona
        duplicate = Persona(
            name=new_name,
            description=data.get('description', original_persona.description),
            system_prompt=original_persona.system_prompt,
            user_prompt_template=original_persona.user_prompt_template,
            input_schema=original_persona.input_schema,
            output_schema=original_persona.output_schema,
            visibility=data.get('visibility', 'private'),  # Always start as private
            tags=original_persona.tags.copy() if original_persona.tags else [],
            variables=original_persona.variables.copy() if original_persona.variables else {},
            created_by=user.id,
            is_approved=False  # New copies need approval
        )
        
        db.session.add(duplicate)
        db.session.flush()
        
        # Create initial version for duplicate
        version = PersonaVersion(
            persona_id=duplicate.id,
            version='1.0.0',
            system_prompt=duplicate.system_prompt,
            user_prompt_template=duplicate.user_prompt_template,
            input_schema=duplicate.input_schema,
            output_schema=duplicate.output_schema,
            changelog=f'Duplicated from "{original_persona.name}"',
            is_active=True,
            created_by=user.id
        )
        
        db.session.add(version)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'persona_duplicated', {
            'original_persona_id': original_persona.id,
            'original_persona_name': original_persona.name,
            'duplicate_persona_id': duplicate.id,
            'duplicate_persona_name': duplicate.name
        }, 'persona', duplicate.id)
        
        return jsonify({
            'success': True,
            'message': 'Persona duplicated successfully',
            'persona': duplicate.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Duplicate persona error: {str(e)}")
        return jsonify({'error': 'Failed to duplicate persona'}), 500

@personas_bp.route('/<int:persona_id>/test', methods=['POST'])
@require_role(['Admin', 'Developer', 'Business User'])
def test_persona(persona_id):
    """Test a persona with sample input"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        persona = Persona.query.get_or_404(persona_id)
        
        # Check access permissions
        if not user.has_role('Admin') and persona.created_by != user.id:
            if not persona.is_approved or persona.visibility == 'private':
                return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data or 'test_input' not in data:
            return jsonify({'error': 'Test input is required'}), 400
        
        test_input = data['test_input']
        model_id = data.get('model_id')  # Optional model to test with
        
        # Build test messages
        messages = [
            {"role": "system", "content": persona.system_prompt}
        ]
        
        # Add user prompt template if available
        if persona.user_prompt_template:
            # Simple template variable replacement
            user_content = persona.user_prompt_template
            if persona.variables:
                for var, default_value in persona.variables.items():
                    placeholder = f"{{{{{var}}}}}"
                    if placeholder in user_content:
                        # Use provided value or default
                        value = data.get('variables', {}).get(var, default_value)
                        user_content = user_content.replace(placeholder, str(value))
            
            # Replace main input placeholder
            user_content = user_content.replace("{{input}}", test_input)
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": test_input})
        
        # Test with LLM service
        from services.llm_service import llm_service
        
        result = llm_service.complete_chat(
            messages=messages,
            model_id=model_id,
            user_id=user.id,
            context={
                'persona_id': persona.id,
                'persona_name': persona.name,
                'test_mode': True
            }
        )
        
        # Log the test
        log_activity(user.id, 'persona_tested', {
            'persona_id': persona.id,
            'persona_name': persona.name,
            'test_input_length': len(test_input),
            'test_success': result['success'],
            'model_id': model_id
        }, 'persona', persona.id)
        
        return jsonify({
            'success': True,
            'test_result': result,
            'messages_sent': messages
        })
        
    except Exception as e:
        current_app.logger.error(f"Test persona error: {str(e)}")
        return jsonify({'error': 'Failed to test persona'}), 500

@personas_bp.route('/templates', methods=['GET'])
def get_persona_templates():
    """Get predefined persona templates"""
    try:
        verify_jwt_in_request()
        
        templates = [
            {
                'name': 'AI Assistant',
                'description': 'A helpful AI assistant for general tasks',
                'system_prompt': 'You are a helpful AI assistant. Provide clear, accurate, and concise responses to user queries. Be polite and professional in your interactions.',
                'user_prompt_template': 'User question: {{input}}',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'The user\'s question or request'
                        }
                    },
                    'required': ['query']
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'response': {
                            'type': 'string',
                            'description': 'The assistant\'s response'
                        },
                        'confidence': {
                            'type': 'number',
                            'description': 'Confidence level (0-1)'
                        }
                    },
                    'required': ['response']
                },
                'tags': ['general', 'assistant', 'helpful']
            },
            {
                'name': 'Code Reviewer',
                'description': 'Reviews code for quality, security, and best practices',
                'system_prompt': 'You are an expert code reviewer. Analyze the provided code for:\n1. Code quality and readability\n2. Security vulnerabilities\n3. Performance issues\n4. Best practices\n5. Potential bugs\n\nProvide constructive feedback with specific suggestions for improvement.',
                'user_prompt_template': 'Please review this {{language}} code:\n\n```{{language}}\n{{input}}\n```\n\nProvide detailed feedback on code quality, security, and best practices.',
                'variables': {
                    'language': 'python'
                },
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'code': {
                            'type': 'string',
                            'description': 'The code to review'
                        },
                        'language': {
                            'type': 'string',
                            'description': 'Programming language'
                        }
                    },
                    'required': ['code']
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'overall_rating': {
                            'type': 'string',
                            'enum': ['excellent', 'good', 'fair', 'poor']
                        },
                        'issues': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'type': {'type': 'string'},
                                    'severity': {'type': 'string'},
                                    'description': {'type': 'string'},
                                    'suggestion': {'type': 'string'}
                                }
                            }
                        },
                        'strengths': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        }
                    }
                },
                'tags': ['code', 'review', 'development', 'quality']
            },
            {
                'name': 'Content Summarizer',
                'description': 'Summarizes long content into key points',
                'system_prompt': 'You are a content summarization expert. Create concise, accurate summaries that capture the key points and main ideas of the provided content. Focus on the most important information and maintain the original context.',
                'user_prompt_template': 'Please summarize the following content in {{length}} length:\n\n{{input}}\n\nProvide a clear summary with the main points.',
                'variables': {
                    'length': 'medium'
                },
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'The content to summarize'
                        },
                        'length': {
                            'type': 'string',
                            'enum': ['short', 'medium', 'long'],
                            'description': 'Desired summary length'
                        }
                    },
                    'required': ['content']
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'summary': {
                            'type': 'string',
                            'description': 'The summarized content'
                        },
                        'key_points': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'List of key points'
                        },
                        'word_count': {
                            'type': 'number',
                            'description': 'Word count of summary'
                        }
                    },
                    'required': ['summary', 'key_points']
                },
                'tags': ['summary', 'content', 'analysis']
            },
            {
                'name': 'Data Analyst',
                'description': 'Analyzes data and provides insights',
                'system_prompt': 'You are a data analyst expert. Analyze the provided data to identify patterns, trends, and insights. Provide clear explanations of your findings and actionable recommendations based on the data.',
                'user_prompt_template': 'Analyze this {{data_type}} data and provide insights:\n\n{{input}}\n\nPlease identify key patterns, trends, and provide actionable recommendations.',
                'variables': {
                    'data_type': 'numerical'
                },
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'data': {
                            'type': 'string',
                            'description': 'The data to analyze'
                        },
                        'data_type': {
                            'type': 'string',
                            'description': 'Type of data being analyzed'
                        }
                    },
                    'required': ['data']
                },
                'output_schema': {
                    'type': 'object',
                    'properties': {
                        'insights': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Key insights from the data'
                        },
                        'trends': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Identified trends'
                        },
                        'recommendations': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Actionable recommendations'
                        }
                    },
                    'required': ['insights']
                },
                'tags': ['data', 'analysis', 'insights', 'business']
            }
        ]
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        current_app.logger.error(f"Get persona templates error: {str(e)}")
        return jsonify({'error': 'Failed to fetch persona templates'}), 500

@personas_bp.route('/<int:persona_id>/usage', methods=['GET'])
def get_persona_usage(persona_id):
    """Get usage statistics for a persona"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        persona = Persona.query.get_or_404(persona_id)
        
        # Check permissions
        if not user.has_role('Admin') and persona.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get usage statistics
        from models.agent import Agent, AgentExecution
        from sqlalchemy import func
        
        # Agents using this persona
        agents_count = Agent.query.filter_by(persona_id=persona_id).count()
        active_agents_count = Agent.query.filter_by(persona_id=persona_id, is_active=True).count()
        
        # Executions through agents using this persona
        executions_query = db.session.query(AgentExecution).join(Agent).filter(Agent.persona_id == persona_id)
        
        total_executions = executions_query.count()
        successful_executions = executions_query.filter(AgentExecution.status == 'completed').count()
        
        # Recent usage (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_executions = executions_query.filter(
            AgentExecution.started_at >= thirty_days_ago
        ).count()
        
        # Total cost and tokens
        total_cost = executions_query.with_entities(func.sum(AgentExecution.cost)).scalar() or 0
        total_tokens = executions_query.with_entities(func.sum(AgentExecution.tokens_used)).scalar() or 0
        
        usage_stats = {
            'agents_count': agents_count,
            'active_agents_count': active_agents_count,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': round((successful_executions / max(total_executions, 1)) * 100, 1),
            'recent_executions_30d': recent_executions,
            'total_cost': round(total_cost, 4),
            'total_tokens': total_tokens,
            'average_cost_per_execution': round(total_cost / max(total_executions, 1), 4),
            'average_tokens_per_execution': round(total_tokens / max(total_executions, 1), 0)
        }
        
        return jsonify({
            'success': True,
            'usage': usage_stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Get persona usage error: {str(e)}")
        return jsonify({'error': 'Failed to fetch persona usage'}), 500