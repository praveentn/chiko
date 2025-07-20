# services/auth_service.py
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from functools import wraps
import re
from datetime import datetime

from extensions import db                       # ← pull db from the shared extensions module
from models.user import User, Role
from models.audit import AuditLog

def require_role(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
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
            user_id = get_jwt_identity()
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
        user_id = get_jwt_identity()
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
        # Don't let audit logging failure break the main operation
        print(f"Audit logging failed: {str(e)}")
        db.session.rollback()

def validate_password_strength(password):
    """Validate password strength requirements"""
    if not password:
        return {'valid': False, 'message': 'Password is required'}
    
    if len(password) < 8:
        return {'valid': False, 'message': 'Password must be at least 8 characters long'}
    
    if len(password) > 128:
        return {'valid': False, 'message': 'Password is too long (max 128 characters)'}
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return {'valid': False, 'message': 'Password must contain at least one uppercase letter'}
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return {'valid': False, 'message': 'Password must contain at least one lowercase letter'}
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return {'valid': False, 'message': 'Password must contain at least one number'}
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
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
    if user.has_role('Admin'):
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
    if permission_name:
        return user.has_permission(permission_name)
    
    return False

def can_access_resource(user, resource_obj, action='read'):
    """Check if user can access specific resource instance"""
    if not user or not resource_obj:
        return False
    
    # Admin users can access everything
    if user.has_role('Admin'):
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
    if query is None:
        query = model_class.query
    
    # Admin users can see everything
    if user.has_role('Admin'):
        return query
    
    # Business users can only see approved resources and their own
    if user.has_role('Business User'):
        if hasattr(model_class, 'is_approved') and hasattr(model_class, 'created_by'):
            query = query.filter(
                (model_class.is_approved == True) | 
                (model_class.created_by == user.id)
            )
        elif hasattr(model_class, 'is_approved'):
            query = query.filter(model_class.is_approved == True)
    
    # Developers can see their own and approved resources
    elif user.has_role('Developer'):
        if hasattr(model_class, 'created_by'):
            query = query.filter(
                (model_class.created_by == user.id) |
                (model_class.is_approved == True)
            )
    
    return query

def create_default_permissions():
    """Create default permissions if they don't exist"""
    from models.user import Permission
    
    default_permissions = [
        # Model permissions
        ('model_create', 'Create models', 'model', 'create'),
        ('model_read', 'Read models', 'model', 'read'),
        ('model_update', 'Update models', 'model', 'update'),
        ('model_delete', 'Delete models', 'model', 'delete'),
        ('model_approve', 'Approve models', 'model', 'approve'),
        
        # Persona permissions
        ('persona_create', 'Create personas', 'persona', 'create'),
        ('persona_read', 'Read personas', 'persona', 'read'),
        ('persona_update', 'Update personas', 'persona', 'update'),
        ('persona_delete', 'Delete personas', 'persona', 'delete'),
        ('persona_approve', 'Approve personas', 'persona', 'approve'),
        
        # Agent permissions
        ('agent_create', 'Create agents', 'agent', 'create'),
        ('agent_read', 'Read agents', 'agent', 'read'),
        ('agent_update', 'Update agents', 'agent', 'update'),
        ('agent_delete', 'Delete agents', 'agent', 'delete'),
        ('agent_execute', 'Execute agents', 'agent', 'execute'),
        ('agent_approve', 'Approve agents', 'agent', 'approve'),
        
        # Workflow permissions
        ('workflow_create', 'Create workflows', 'workflow', 'create'),
        ('workflow_read', 'Read workflows', 'workflow', 'read'),
        ('workflow_update', 'Update workflows', 'workflow', 'update'),
        ('workflow_delete', 'Delete workflows', 'workflow', 'delete'),
        ('workflow_execute', 'Execute workflows', 'workflow', 'execute'),
        ('workflow_approve', 'Approve workflows', 'workflow', 'approve'),
        
        # Tool permissions
        ('tool_create', 'Create tools', 'tool', 'create'),
        ('tool_read', 'Read tools', 'tool', 'read'),
        ('tool_update', 'Update tools', 'tool', 'update'),
        ('tool_delete', 'Delete tools', 'tool', 'delete'),
        ('tool_approve', 'Approve tools', 'tool', 'approve'),
        
        # Admin permissions
        ('user_management', 'Manage users', 'user', 'manage'),
        ('system_administration', 'System administration', 'system', 'admin'),
        ('sql_execution', 'Execute SQL queries', 'database', 'execute'),
        ('audit_access', 'Access audit logs', 'audit', 'read'),
    ]
    
    created_permissions = []
    for name, description, resource, action in default_permissions:
        if not Permission.query.filter_by(name=name).first():
            permission = Permission(
                name=name,
                description=description,
                resource=resource,
                action=action
            )
            db.session.add(permission)
            created_permissions.append(permission)
    
    try:
        db.session.commit()
        return created_permissions
    except Exception as e:
        db.session.rollback()
        raise e

def assign_role_permissions():
    """Assign default permissions to roles"""
    from models.user import Role, Permission
    
    # Get roles
    admin_role = Role.query.filter_by(name='Admin').first()
    developer_role = Role.query.filter_by(name='Developer').first()
    business_role = Role.query.filter_by(name='Business User').first()
    
    if not all([admin_role, developer_role, business_role]):
        return False
    
    # Admin gets all permissions
    all_permissions = Permission.query.all()
    admin_role.permissions = all_permissions
    
    # Developer permissions
    developer_permissions = Permission.query.filter(
        Permission.name.in_([
            'model_create', 'model_read', 'model_update', 'model_delete',
            'persona_create', 'persona_read', 'persona_update', 'persona_delete',
            'agent_create', 'agent_read', 'agent_update', 'agent_delete', 'agent_execute',
            'workflow_create', 'workflow_read', 'workflow_update', 'workflow_delete', 'workflow_execute',
            'tool_create', 'tool_read', 'tool_update', 'tool_delete'
        ])
    ).all()
    developer_role.permissions = developer_permissions
    
    # Business User permissions
    business_permissions = Permission.query.filter(
        Permission.name.in_([
            'model_read', 'persona_read', 'agent_read', 'agent_execute',
            'workflow_read', 'workflow_execute', 'tool_read'
        ])
    ).all()
    business_role.permissions = business_permissions
    
    try:
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False

def rate_limit_check(user_id, action, limit_per_hour=100):
    """Simple rate limiting check"""
    from datetime import datetime, timedelta
    
    # Count actions in the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_actions = AuditLog.query.filter(
        AuditLog.user_id == user_id,
        AuditLog.action == action,
        AuditLog.created_at >= one_hour_ago
    ).count()
    
    return recent_actions < limit_per_hour

def sanitize_user_input(input_string, max_length=1000):
    """Basic input sanitization"""
    if not input_string:
        return ""
    
    # Remove potential XSS characters
    dangerous_chars = ['<', '>', '"', "'", '&', 'javascript:', 'data:', 'vbscript:']
    sanitized = str(input_string)
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Truncate to max length
    return sanitized[:max_length]