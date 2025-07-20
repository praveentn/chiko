# services/auth_service.py
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from functools import wraps
import re
from datetime import datetime

from extensions import db
from models.user import User, Role
from models.audit import AuditLog

def require_role(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())  # Convert back to int
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
            
            if isinstance(required_role, list):
                if not user.role or user.role.name not in required_role:
                    return {'error': 'Insufficient permissions'}, 403
            else:
                if not user.role or user.role.name != required_role:
                    return {'error': 'Insufficient permissions'}, 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_permission(permission_name):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())  # Convert back to int
            user = User.query.get(user_id)
            
            if not user or not user.has_permission(permission_name):
                return {'error': 'Insufficient permissions'}, 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Get current authenticated user"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        return User.query.get(user_id)
    except:
        return None

def log_activity(user_id, action, details=None, resource_type=None, resource_id=None, success=True, error_message=None):
    """Log user activity for auditing"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            details=details,
            success=success,
            error_message=error_message
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Failed to log activity: {e}")

def validate_password_strength(password):
    """Validate password strength requirements"""
    if len(password) < 8:
        return {'valid': False, 'message': 'Password must be at least 8 characters long'}
    
    if len(password) > 128:
        return {'valid': False, 'message': 'Password must be less than 128 characters'}
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return {'valid': False, 'message': 'Password must contain at least one uppercase letter'}
    
    # Check for lowercase letter  
    if not re.search(r'[a-z]', password):
        return {'valid': False, 'message': 'Password must contain at least one lowercase letter'}
    
    # Check for digit
    if not re.search(r'\d', password):
        return {'valid': False, 'message': 'Password must contain at least one number'}
    
    # Check for special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?~`]', password):
        return {'valid': False, 'message': 'Password must contain at least one special character'}
    
    # Check for common weak passwords
    weak_passwords = [
        'password', '12345678', 'qwerty123', 'admin123', 'letmein123',
        'password123', 'admin1234', 'welcome123', 'changeme123'
    ]
    
    if password.lower() in weak_passwords:
        return {'valid': False, 'message': 'Password is too common. Please choose a stronger password'}
    
    return {'valid': True, 'message': 'Password is strong'}

def check_user_permissions(user, action, resource_type=None):
    """Check if user has permission to perform action on resource"""
    if not user:
        return False
    
    # Admin users have all permissions
    if user.role and user.role.name == 'Admin':
        return True
    
    # Map actions to permission patterns
    permission_map = {
        'create': f'{resource_type}_create',
        'read': f'{resource_type}_read', 
        'update': f'{resource_type}_update',
        'delete': f'{resource_type}_delete',
        'approve': f'{resource_type}_approve',
        'execute': f'{resource_type}_execute'
    }
    
    permission_name = permission_map.get(action)
    if permission_name and hasattr(user, 'has_permission'):
        return user.has_permission(permission_name)
    
    return False

def can_access_resource(user, resource_obj, action='read'):
    """Check if user can access specific resource instance"""
    if not user or not resource_obj:
        return False
    
    # Admin users can access everything
    if user.role and user.role.name == 'Admin':
        return True
    
    # Check if user owns the resource
    if hasattr(resource_obj, 'created_by') and resource_obj.created_by == user.id:
        return True
    
    # Check visibility settings for resources that support it
    if hasattr(resource_obj, 'visibility'):
        if resource_obj.visibility == 'public':
            return True
        elif resource_obj.visibility == 'team':
            # TODO: Implement team-based access control
            return True
        elif resource_obj.visibility == 'private':
            return resource_obj.created_by == user.id
    
    # Check approval status for read access
    if action == 'read' and hasattr(resource_obj, 'is_approved'):
        return resource_obj.is_approved
    
    return False

def get_user_accessible_resources(user, model_class, query=None):
    """Get resources that user can access"""
    from sqlalchemy import or_
    
    if query is None:
        query = model_class.query
    
    # Admin users can see everything
    if user.role and user.role.name == 'Admin':
        return query
    
    # Regular users can see approved resources or their own resources
    access_conditions = []
    
    # Can see approved/public resources
    if hasattr(model_class, 'is_approved'):
        access_conditions.append(model_class.is_approved == True)
    
    # Can see own resources
    if hasattr(model_class, 'created_by'):
        access_conditions.append(model_class.created_by == user.id)
    
    # Can see public visibility resources
    if hasattr(model_class, 'visibility'):
        access_conditions.append(model_class.visibility == 'public')
    
    if access_conditions:
        return query.filter(or_(*access_conditions))
    
    return query

def detect_device_type(user_agent):
    """Detect device type from user agent"""
    if not user_agent:
        return 'unknown'
    
    user_agent = user_agent.lower()
    
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'

def create_default_permissions():
    """Create default system permissions"""
    permissions_data = [
        # Model permissions
        {'name': 'model_create', 'description': 'Create new models', 'resource': 'model', 'action': 'create'},
        {'name': 'model_read', 'description': 'View models', 'resource': 'model', 'action': 'read'},
        {'name': 'model_update', 'description': 'Update models', 'resource': 'model', 'action': 'update'},
        {'name': 'model_delete', 'description': 'Delete models', 'resource': 'model', 'action': 'delete'},
        {'name': 'model_approve', 'description': 'Approve models', 'resource': 'model', 'action': 'approve'},
        
        # Persona permissions
        {'name': 'persona_create', 'description': 'Create new personas', 'resource': 'persona', 'action': 'create'},
        {'name': 'persona_read', 'description': 'View personas', 'resource': 'persona', 'action': 'read'},
        {'name': 'persona_update', 'description': 'Update personas', 'resource': 'persona', 'action': 'update'},
        {'name': 'persona_delete', 'description': 'Delete personas', 'resource': 'persona', 'action': 'delete'},
        {'name': 'persona_approve', 'description': 'Approve personas', 'resource': 'persona', 'action': 'approve'},
        
        # Agent permissions
        {'name': 'agent_create', 'description': 'Create new agents', 'resource': 'agent', 'action': 'create'},
        {'name': 'agent_read', 'description': 'View agents', 'resource': 'agent', 'action': 'read'},
        {'name': 'agent_update', 'description': 'Update agents', 'resource': 'agent', 'action': 'update'},
        {'name': 'agent_delete', 'description': 'Delete agents', 'resource': 'agent', 'action': 'delete'},
        {'name': 'agent_execute', 'description': 'Execute agents', 'resource': 'agent', 'action': 'execute'},
        {'name': 'agent_approve', 'description': 'Approve agents', 'resource': 'agent', 'action': 'approve'},
        
        # Workflow permissions
        {'name': 'workflow_create', 'description': 'Create new workflows', 'resource': 'workflow', 'action': 'create'},
        {'name': 'workflow_read', 'description': 'View workflows', 'resource': 'workflow', 'action': 'read'},
        {'name': 'workflow_update', 'description': 'Update workflows', 'resource': 'workflow', 'action': 'update'},
        {'name': 'workflow_delete', 'description': 'Delete workflows', 'resource': 'workflow', 'action': 'delete'},
        {'name': 'workflow_execute', 'description': 'Execute workflows', 'resource': 'workflow', 'action': 'execute'},
        {'name': 'workflow_approve', 'description': 'Approve workflows', 'resource': 'workflow', 'action': 'approve'},
        
        # Tool permissions
        {'name': 'tool_create', 'description': 'Create new tools', 'resource': 'tool', 'action': 'create'},
        {'name': 'tool_read', 'description': 'View tools', 'resource': 'tool', 'action': 'read'},
        {'name': 'tool_update', 'description': 'Update tools', 'resource': 'tool', 'action': 'update'},
        {'name': 'tool_delete', 'description': 'Delete tools', 'resource': 'tool', 'action': 'delete'},
        {'name': 'tool_approve', 'description': 'Approve tools', 'resource': 'tool', 'action': 'approve'},
        
        # Admin permissions
        {'name': 'admin_access', 'description': 'Access admin panel', 'resource': 'admin', 'action': 'access'},
        {'name': 'user_management', 'description': 'Manage users', 'resource': 'user', 'action': 'manage'},
        {'name': 'system_settings', 'description': 'Manage system settings', 'resource': 'system', 'action': 'settings'},
    ]
    
    for perm_data in permissions_data:
        permission = Permission.query.filter_by(name=perm_data['name']).first()
        if not permission:
            permission = Permission(
                name=perm_data['name'],
                description=perm_data['description'],
                resource=perm_data['resource'],
                action=perm_data['action']
            )
            db.session.add(permission)
    
    db.session.commit()

def assign_role_permissions():
    """Assign permissions to default roles"""
    from models.user import Permission
    
    # Get roles
    admin_role = Role.query.filter_by(name='Admin').first()
    developer_role = Role.query.filter_by(name='Developer').first()
    business_role = Role.query.filter_by(name='Business User').first()
    
    # Get permissions
    all_permissions = Permission.query.all()
    
    if admin_role:
        # Admin gets all permissions
        admin_role.permissions = all_permissions
    
    if developer_role:
        # Developer gets most permissions except user management
        dev_permissions = [p for p in all_permissions if not p.name.startswith('user_management')]
        developer_role.permissions = dev_permissions
    
    if business_role:
        # Business User gets read and execute permissions
        business_permissions = [
            p for p in all_permissions 
            if p.action in ['read', 'execute', 'create'] and p.resource in ['agent', 'workflow', 'persona']
        ]
        business_role.permissions = business_permissions
    
    db.session.commit()