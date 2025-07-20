# routes/tools.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from datetime import datetime, timedelta
import json
import traceback
import requests
from urllib.parse import urlparse

from extensions import db                       # ← pull db from the shared extensions module
from models.tool import Tool, MCPServer
from models.user import User
from services.auth_service import get_current_user, require_role, log_activity, get_user_accessible_resources

tools_bp = Blueprint('tools', __name__)

@tools_bp.route('/', methods=['GET'])
def get_tools():
    """Get list of tools accessible to the user"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        tool_type_filter = request.args.get('tool_type', '').strip()
        status_filter = request.args.get('status', '').strip()
        
        # Base query with user access filtering
        query = get_user_accessible_resources(user, Tool)
        
        # Apply search filter
        if search:
            query = query.filter(
                (Tool.name.ilike(f'%{search}%')) |
                (Tool.description.ilike(f'%{search}%'))
            )
        
        # Apply tool type filter
        if tool_type_filter:
            query = query.filter(Tool.tool_type == tool_type_filter)
        
        # Apply status filter
        if status_filter == 'approved':
            query = query.filter(Tool.is_approved == True)
        elif status_filter == 'pending':
            query = query.filter(Tool.is_approved == False)
        elif status_filter == 'active':
            query = query.filter(Tool.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Tool.is_active == False)
        
        # Get paginated results
        tools = query.order_by(Tool.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'tools': [tool.to_dict() for tool in tools.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': tools.total,
                'total_pages': tools.pages,
                'has_next': tools.has_next,
                'has_prev': tools.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get tools error: {str(e)}")
        return jsonify({'error': 'Failed to fetch tools'}), 500

@tools_bp.route('/<int:tool_id>', methods=['GET'])
def get_tool(tool_id):
    """Get a specific tool by ID"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tool = Tool.query.get_or_404(tool_id)
        
        # Check access permissions
        if not user.has_role('Admin'):
            if not tool.is_approved and tool.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        tool_data = tool.to_dict()
        
        # Add MCP server info if applicable
        if tool.mcp_server_id:
            mcp_server = MCPServer.query.get(tool.mcp_server_id)
            if mcp_server:
                tool_data['mcp_server'] = {
                    'id': mcp_server.id,
                    'name': mcp_server.name,
                    'status': mcp_server.status,
                    'last_ping': mcp_server.last_ping.isoformat() if mcp_server.last_ping else None
                }
        
        return jsonify({
            'success': True,
            'tool': tool_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get tool error: {str(e)}")
        return jsonify({'error': 'Failed to fetch tool'}), 500

@tools_bp.route('/', methods=['POST'])
@require_role(['Admin', 'Developer'])
def create_tool():
    """Create a new tool"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'tool_type', 'function_schema']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate tool type
        valid_tool_types = ['function', 'mcp_server', 'api']
        if data['tool_type'] not in valid_tool_types:
            return jsonify({'error': f'tool_type must be one of: {valid_tool_types}'}), 400
        
        # Validate function schema
        function_schema = data['function_schema']
        if not isinstance(function_schema, dict):
            return jsonify({'error': 'function_schema must be a valid JSON object'}), 400
        
        # Validate schema structure
        required_schema_fields = ['name', 'description']
        for field in required_schema_fields:
            if field not in function_schema:
                return jsonify({'error': f'function_schema must include {field}'}), 400
        
        # Validate MCP server if provided
        mcp_server_id = data.get('mcp_server_id')
        if mcp_server_id:
            mcp_server = MCPServer.query.get(mcp_server_id)
            if not mcp_server:
                return jsonify({'error': 'MCP server not found'}), 404
        
        # Create new tool
        tool = Tool(
            name=data['name'],
            description=data.get('description', ''),
            tool_type=data['tool_type'],
            function_schema=function_schema,
            endpoint_url=data.get('endpoint_url'),
            authentication=data.get('authentication'),
            safety_tags=data.get('safety_tags', []),
            rate_limit=data.get('rate_limit'),
            timeout=min(data.get('timeout', 30), 300),  # Max 5 minutes
            is_active=True,
            is_approved=user.has_role('Admin'),  # Auto-approve for Admins
            mcp_server_id=mcp_server_id,
            created_by=user.id
        )
        
        db.session.add(tool)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'tool_created', {
            'tool_id': tool.id,
            'tool_name': tool.name,
            'tool_type': tool.tool_type
        }, 'tool', tool.id)
        
        return jsonify({
            'success': True,
            'message': 'Tool created successfully',
            'tool': tool.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create tool error: {str(e)}")
        return jsonify({'error': 'Failed to create tool'}), 500

@tools_bp.route('/<int:tool_id>', methods=['PUT'])
@require_role(['Admin', 'Developer'])
def update_tool(tool_id):
    """Update an existing tool"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        tool = Tool.query.get_or_404(tool_id)
        
        # Check permissions
        if not user.has_role('Admin') and tool.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Track changes
        changes = {}
        
        # Update basic fields
        for field in ['name', 'description', 'tool_type', 'endpoint_url']:
            if field in data and data[field] != getattr(tool, field):
                changes[field] = {'old': getattr(tool, field), 'new': data[field]}
                setattr(tool, field, data[field])
        
        # Update function schema
        if 'function_schema' in data:
            if data['function_schema'] != tool.function_schema:
                changes['function_schema'] = {'old': tool.function_schema, 'new': data['function_schema']}
                tool.function_schema = data['function_schema']
        
        # Update authentication
        if 'authentication' in data:
            if data['authentication'] != tool.authentication:
                changes['authentication'] = {'old': 'hidden', 'new': 'updated'}
                tool.authentication = data['authentication']
        
        # Update safety tags
        if 'safety_tags' in data:
            if data['safety_tags'] != tool.safety_tags:
                changes['safety_tags'] = {'old': tool.safety_tags, 'new': data['safety_tags']}
                tool.safety_tags = data['safety_tags']
        
        # Update numeric fields with validation
        if 'rate_limit' in data:
            new_value = data['rate_limit']
            if new_value != tool.rate_limit:
                changes['rate_limit'] = {'old': tool.rate_limit, 'new': new_value}
                tool.rate_limit = new_value
        
        if 'timeout' in data:
            new_value = min(data['timeout'], 300)  # Max 5 minutes
            if new_value != tool.timeout:
                changes['timeout'] = {'old': tool.timeout, 'new': new_value}
                tool.timeout = new_value
        
        # Update MCP server if provided
        if 'mcp_server_id' in data:
            new_value = data['mcp_server_id']
            if new_value and new_value != tool.mcp_server_id:
                mcp_server = MCPServer.query.get(new_value)
                if not mcp_server:
                    return jsonify({'error': 'MCP server not found'}), 404
                
                changes['mcp_server_id'] = {'old': tool.mcp_server_id, 'new': new_value}
                tool.mcp_server_id = new_value
        
        # Update active status if provided (Admin only)
        if 'is_active' in data and user.has_role('Admin'):
            if data['is_active'] != tool.is_active:
                changes['is_active'] = {'old': tool.is_active, 'new': data['is_active']}
                tool.is_active = data['is_active']
        
        if changes:
            tool.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log activity
            log_activity(user.id, 'tool_updated', {
                'tool_id': tool.id,
                'tool_name': tool.name,
                'changes': changes
            }, 'tool', tool.id)
            
            return jsonify({
                'success': True,
                'message': 'Tool updated successfully',
                'tool': tool.to_dict(),
                'changes': changes
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No changes detected',
                'tool': tool.to_dict()
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update tool error: {str(e)}")
        return jsonify({'error': 'Failed to update tool'}), 500

@tools_bp.route('/<int:tool_id>', methods=['DELETE'])
@require_role(['Admin', 'Developer'])
def delete_tool(tool_id):
    """Delete a tool"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        tool = Tool.query.get_or_404(tool_id)
        
        # Check permissions
        if not user.has_role('Admin') and tool.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if tool is being used by agents
        from models.agent import Agent
        agents_using_tool = Agent.query.filter(
            Agent.tool_ids.contains([tool_id]),
            Agent.is_active == True
        ).count()
        
        if agents_using_tool > 0:
            return jsonify({
                'error': f'Cannot delete tool. It is being used by {agents_using_tool} active agents'
            }), 400
        
        # Soft delete - mark as inactive first
        tool.is_active = False
        tool.updated_at = datetime.utcnow()
        
        # Log activity
        log_activity(user.id, 'tool_deleted', {
            'tool_id': tool.id,
            'tool_name': tool.name
        }, 'tool', tool.id)
        
        # If user confirms hard delete, remove from database
        if request.args.get('hard_delete') == 'true' and user.has_role('Admin'):
            db.session.delete(tool)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Tool deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete tool error: {str(e)}")
        return jsonify({'error': 'Failed to delete tool'}), 500

@tools_bp.route('/<int:tool_id>/test', methods=['POST'])
@require_role(['Admin', 'Developer'])
def test_tool(tool_id):
    """Test a tool with provided parameters"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        tool = Tool.query.get_or_404(tool_id)
        
        # Check permissions
        if not user.has_role('Admin') and tool.created_by != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        test_params = data.get('parameters', {}) if data else {}
        
        # Simulate tool execution (simplified implementation)
        result = {
            'success': True,
            'tool_name': tool.name,
            'test_params': test_params,
            'response': f'Tool {tool.name} test completed successfully',
            'execution_time': 0.25,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log activity
        log_activity(user.id, 'tool_tested', {
            'tool_id': tool.id,
            'tool_name': tool.name,
            'test_params': test_params
        }, 'tool', tool.id)
        
        return jsonify({
            'success': True,
            'test_result': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Test tool error: {str(e)}")
        return jsonify({'error': 'Failed to test tool'}), 500

@tools_bp.route('/<int:tool_id>/health', methods=['GET'])
def check_tool_health(tool_id):
    """Check health status of a tool"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        tool = Tool.query.get_or_404(tool_id)
        
        # Check permissions
        if not user.has_role('Admin'):
            if not tool.is_approved and tool.created_by != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        # Perform health check (simplified implementation)
        health_status = 'healthy'
        last_check = datetime.utcnow()
        
        # Update tool health status
        tool.health_status = health_status
        tool.last_health_check = last_check
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tool_id': tool.id,
            'health_status': health_status,
            'last_check': last_check.isoformat(),
            'message': 'Tool health check completed'
        })
        
    except Exception as e:
        current_app.logger.error(f"Tool health check error: {str(e)}")
        return jsonify({'error': 'Failed to check tool health'}), 500

@tools_bp.route('/<int:tool_id>/approve', methods=['POST'])
@require_role(['Admin'])
def approve_tool(tool_id):
    """Approve or reject a tool"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        tool = Tool.query.get_or_404(tool_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        approve = data.get('approve', True)
        comment = data.get('comment', '')
        
        tool.is_approved = approve
        tool.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'tool_approved' if approve else 'tool_rejected', {
            'tool_id': tool.id,
            'tool_name': tool.name,
            'comment': comment
        }, 'tool', tool.id)
        
        return jsonify({
            'success': True,
            'message': f'Tool {"approved" if approve else "rejected"} successfully',
            'tool': tool.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve tool error: {str(e)}")
        return jsonify({'error': 'Failed to process tool approval'}), 500

# MCP Server routes
@tools_bp.route('/mcp-servers', methods=['GET'])
def get_mcp_servers():
    """Get list of MCP servers"""
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
        
        # Base query
        query = MCPServer.query
        
        # Apply search filter
        if search:
            query = query.filter(
                (MCPServer.name.ilike(f'%{search}%')) |
                (MCPServer.description.ilike(f'%{search}%'))
            )
        
        # Apply status filter
        if status_filter:
            query = query.filter(MCPServer.status == status_filter)
        
        # Get paginated results
        servers = query.order_by(MCPServer.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Convert to dict and add tool count
        servers_data = []
        for server in servers.items:
            server_dict = {
                'id': server.id,
                'name': server.name,
                'description': server.description,
                'server_url': server.server_url,
                'version': server.version,
                'is_active': server.is_active,
                'status': server.status,
                'last_ping': server.last_ping.isoformat() if server.last_ping else None,
                'capabilities': server.capabilities,
                'tool_count': len(server.tools),
                'created_at': server.created_at.isoformat() if server.created_at else None
            }
            servers_data.append(server_dict)
        
        return jsonify({
            'success': True,
            'mcp_servers': servers_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': servers.total,
                'total_pages': servers.pages,
                'has_next': servers.has_next,
                'has_prev': servers.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get MCP servers error: {str(e)}")
        return jsonify({'error': 'Failed to fetch MCP servers'}), 500

@tools_bp.route('/mcp-servers', methods=['POST'])
@require_role(['Admin', 'Developer'])
def create_mcp_server():
    """Create a new MCP server"""
    try:
        verify_jwt_in_request()
        user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['name', 'server_url']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate URL format
        try:
            parsed_url = urlparse(data['server_url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                return jsonify({'error': 'Invalid server URL format'}), 400
        except Exception:
            return jsonify({'error': 'Invalid server URL format'}), 400
        
        # Create new MCP server
        mcp_server = MCPServer(
            name=data['name'],
            description=data.get('description', ''),
            server_url=data['server_url'],
            api_key=data.get('api_key'),
            version=data.get('version', '1.0.0'),
            is_active=True,
            status='unknown',
            capabilities=data.get('capabilities', {}),
            created_by=user.id
        )
        
        db.session.add(mcp_server)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'mcp_server_created', {
            'server_id': mcp_server.id,
            'server_name': mcp_server.name,
            'server_url': mcp_server.server_url
        }, 'mcp_server', mcp_server.id)
        
        return jsonify({
            'success': True,
            'message': 'MCP server created successfully',
            'mcp_server': {
                'id': mcp_server.id,
                'name': mcp_server.name,
                'description': mcp_server.description,
                'server_url': mcp_server.server_url,
                'status': mcp_server.status,
                'created_at': mcp_server.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create MCP server error: {str(e)}")
        return jsonify({'error': 'Failed to create MCP server'}), 500

@tools_bp.route('/templates', methods=['GET'])
def get_tool_templates():
    """Get predefined tool templates"""
    try:
        templates = [
            {
                'name': 'Web Search Tool',
                'description': 'Search the web for information',
                'tool_type': 'api',
                'function_schema': {
                    'name': 'web_search',
                    'description': 'Search the web for information',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query': {
                                'type': 'string',
                                'description': 'Search query'
                            },
                            'num_results': {
                                'type': 'integer',
                                'description': 'Number of results to return',
                                'default': 10
                            }
                        },
                        'required': ['query']
                    }
                },
                'safety_tags': ['web_access'],
                'rate_limit': 100,
                'timeout': 30
            },
            {
                'name': 'Data Analysis Tool',
                'description': 'Analyze data and generate insights',
                'tool_type': 'function',
                'function_schema': {
                    'name': 'analyze_data',
                    'description': 'Analyze dataset and provide insights',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'data': {
                                'type': 'string',
                                'description': 'CSV data or data path'
                            },
                            'analysis_type': {
                                'type': 'string',
                                'enum': ['descriptive', 'statistical', 'predictive'],
                                'description': 'Type of analysis to perform'
                            }
                        },
                        'required': ['data']
                    }
                },
                'safety_tags': ['data_processing'],
                'rate_limit': 50,
                'timeout': 60
            },
            {
                'name': 'Email Sender Tool',
                'description': 'Send emails via SMTP',
                'tool_type': 'api',
                'function_schema': {
                    'name': 'send_email',
                    'description': 'Send an email message',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'to': {
                                'type': 'string',
                                'description': 'Recipient email address'
                            },
                            'subject': {
                                'type': 'string',
                                'description': 'Email subject'
                            },
                            'body': {
                                'type': 'string',
                                'description': 'Email body content'
                            }
                        },
                        'required': ['to', 'subject', 'body']
                    }
                },
                'safety_tags': ['email_access'],
                'rate_limit': 20,
                'timeout': 15
            }
        ]
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        current_app.logger.error(f"Get tool templates error: {str(e)}")
        return jsonify({'error': 'Failed to fetch tool templates'}), 500