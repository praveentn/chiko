# routes/admin.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import text, inspect, MetaData
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta  # ← Added missing timedelta import
import traceback
import re
import math
from functools import wraps

from extensions import db
from models.user import User, Role, Permission
from models.audit import AuditLog
from services.auth_service import require_role, log_activity

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.has_role('Admin'):
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/sql/execute', methods=['POST'])
@admin_required
def execute_sql():
    """Execute raw SQL queries with pagination and safety checks"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'SQL query is required'}), 400
        
        sql_query = data['query'].strip()
        page = data.get('page', 1)
        per_page = min(data.get('per_page', 50), 1000)  # Max 1000 rows per page
        
        # Safety checks
        dangerous_patterns = [
            r'\bDROP\s+TABLE\b',
            r'\bDROP\s+DATABASE\b',
            r'\bTRUNCATE\b',
            r'\bDELETE\s+FROM\s+\w+(?!\s+WHERE)\b'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_query, re.IGNORECASE):
                return jsonify({'error': 'Potentially dangerous query detected'}), 400
        
        # Execute query with pagination for SELECT statements
        if sql_query.upper().strip().startswith('SELECT'):
            offset = (page - 1) * per_page
            paginated_query = f"{sql_query} LIMIT {per_page} OFFSET {offset}"
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({sql_query}) as count_table"
            count_result = db.session.execute(text(count_query))
            total_count = count_result.scalar()
            
            # Execute paginated query
            result = db.session.execute(text(paginated_query))
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result]
            
            total_pages = math.ceil(total_count / per_page)
            
            return jsonify({
                'success': True,
                'columns': columns,
                'rows': rows,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_rows': total_count,
                    'total_pages': total_pages
                },
                'execution_time': '< 1ms'
            })
        else:
            # Execute non-SELECT queries
            result = db.session.execute(text(sql_query))
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Query executed successfully. Rows affected: {result.rowcount}',
                'rows_affected': result.rowcount
            })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'SQL Error: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.error(f"SQL execution error: {str(e)}")
        return jsonify({'error': 'Query execution failed'}), 500

@admin_bp.route('/sql/history', methods=['GET'])
@admin_required
def get_sql_history():
    """Get SQL query execution history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Get audit logs for SQL queries
        query = AuditLog.query.filter(
            AuditLog.action == 'sql_executed'
        ).order_by(AuditLog.created_at.desc())
        
        history = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        history_data = []
        for log in history.items:
            history_data.append({
                'id': log.id,
                'query': log.details.get('query', 'N/A') if log.details else 'N/A',
                'user_email': log.user.email if log.user else 'Unknown',
                'status': log.details.get('status', 'unknown') if log.details else 'unknown',
                'execution_time': log.details.get('execution_time', 'N/A') if log.details else 'N/A',
                'created_at': log.created_at.isoformat() if log.created_at else None
            })
        
        return jsonify({
            'success': True,
            'history': history_data,
            'pagination': {
                'page': page,
                'pages': history.pages,
                'per_page': per_page,
                'total': history.total,
                'has_prev': history.has_prev,
                'has_next': history.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"SQL history error: {str(e)}")
        return jsonify({'error': 'Failed to fetch SQL history'}), 500

@admin_bp.route('/activity', methods=['GET'])
@admin_required
def get_activity_logs():
    """Get system activity logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        action_filter = request.args.get('action', '').strip()
        user_filter = request.args.get('user', '').strip()
        
        query = AuditLog.query
        
        # Apply filters
        if action_filter:
            query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
        
        if user_filter:
            query = query.join(User).filter(User.email.ilike(f'%{user_filter}%'))
        
        # Get paginated results
        activity = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        activity_data = []
        for log in activity.items:
            activity_data.append({
                'id': log.id,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'user_email': log.user.email if log.user else 'System',
                'user_id': log.user_id,
                'details': log.details,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'created_at': log.created_at.isoformat() if log.created_at else None
            })
        
        return jsonify({
            'success': True,
            'activity': activity_data,
            'pagination': {
                'page': page,
                'pages': activity.pages,
                'per_page': per_page,
                'total': activity.total,
                'has_prev': activity.has_prev,
                'has_next': activity.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Activity logs error: {str(e)}")
        return jsonify({'error': 'Failed to fetch activity logs'}), 500

@admin_bp.route('/database/schema', methods=['GET'])
@admin_required
def get_database_schema():
    """Get database schema information"""
    try:
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        schema_info = {}
        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            schema_info[table_name] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                        'default': col['default'],
                        'primary_key': col.get('primary_key', False)
                    }
                    for col in columns
                ],
                'foreign_keys': [
                    {
                        'constrained_columns': fk['constrained_columns'],
                        'referred_table': fk['referred_table'],
                        'referred_columns': fk['referred_columns']
                    }
                    for fk in foreign_keys
                ],
                'indexes': [
                    {
                        'name': idx['name'],
                        'column_names': idx['column_names'],
                        'unique': idx['unique']
                    }
                    for idx in indexes
                ]
            }
        
        return jsonify({
            'success': True,
            'schema': schema_info,
            'table_count': len(table_names)
        })
        
    except Exception as e:
        current_app.logger.error(f"Schema fetch error: {str(e)}")
        return jsonify({'error': 'Failed to fetch schema information'}), 500

@admin_bp.route('/sql/templates', methods=['GET'])
@admin_required
def get_sql_templates():
    """Get common SQL query templates"""
    templates = {
        'basic_queries': [
            {
                'name': 'Select All Users',
                'query': 'SELECT * FROM users LIMIT 10;',
                'description': 'Retrieve first 10 users'
            },
            {
                'name': 'User Count by Role',
                'query': '''SELECT r.name as role_name, COUNT(u.id) as user_count
FROM roles r
LEFT JOIN users u ON r.id = u.role_id
GROUP BY r.id, r.name
ORDER BY user_count DESC;''',
                'description': 'Count users by role'
            },
            {
                'name': 'Recent Activity',
                'query': '''SELECT al.action, al.resource_type, u.email, al.created_at
FROM audit_logs al
JOIN users u ON al.user_id = u.id
ORDER BY al.created_at DESC
LIMIT 20;''',
                'description': 'Show recent user activity'
            }
        ],
        'model_queries': [
            {
                'name': 'Model Usage Stats',
                'query': '''SELECT m.name, m.provider, COUNT(ae.id) as execution_count,
AVG(ae.tokens_used) as avg_tokens,
SUM(ae.cost) as total_cost
FROM models m
LEFT JOIN agent_executions ae ON m.id = ae.model_id
GROUP BY m.id, m.name, m.provider
ORDER BY execution_count DESC;''',
                'description': 'Model usage statistics'
            }
        ],
        'maintenance_queries': [
            {
                'name': 'Database Size',
                'query': "SELECT name, COUNT(*) as row_count FROM sqlite_master WHERE type='table' GROUP BY name;",
                'description': 'Table row counts'
            },
            {
                'name': 'Cleanup Old Logs',
                'query': "DELETE FROM audit_logs WHERE created_at < datetime('now', '-30 days');",
                'description': 'Delete audit logs older than 30 days'
            }
        ]
    }
    
    return jsonify({
        'success': True,
        'templates': templates
    })

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        role_filter = request.args.get('role', '').strip()
        
        query = User.query
        
        # Apply search filter
        if search:
            query = query.filter(
                (User.email.ilike(f'%{search}%')) |
                (User.first_name.ilike(f'%{search}%')) |
                (User.last_name.ilike(f'%{search}%'))
            )
        
        # Apply role filter
        if role_filter:
            query = query.join(Role).filter(Role.name == role_filter)
        
        # Get paginated results
        users = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        users_data = []
        for user in users.items:
            users_data.append({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'role': user.role.name if user.role else None,
                'is_active': user.is_active,
                'is_approved': user.is_approved,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify({
            'success': True,
            'users': users_data,
            'pagination': {
                'page': page,
                'pages': users.pages,
                'per_page': per_page,
                'total': users.total,
                'has_prev': users.has_prev,
                'has_next': users.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get users error: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    """Update user role"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if not data or 'role_name' not in data:
            return jsonify({'error': 'Role name is required'}), 400
        
        role = Role.query.filter_by(name=data['role_name']).first()
        if not role:
            return jsonify({'error': 'Invalid role'}), 400
        
        old_role = user.role.name if user.role else None
        user.role_id = role.id
        db.session.commit()
        
        log_activity(get_jwt_identity(), 'user_role_updated', {
            'target_user_id': user_id,
            'target_user_email': user.email,
            'old_role': old_role,
            'new_role': role.name
        })
        
        return jsonify({
            'success': True,
            'message': f'User role updated to {role.name}'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Role update error: {str(e)}")
        return jsonify({'error': 'Failed to update user role'}), 500

@admin_bp.route('/system/stats', methods=['GET'])
@admin_required
def get_system_stats():
    """Get system statistics"""
    try:
        stats = {
            'users': {
                'total': User.query.count(),
                'active': User.query.filter_by(is_active=True).count(),
                'pending_approval': User.query.filter_by(is_approved=False).count()
            },
            'recent_activity': {
                'last_24h': AuditLog.query.filter(
                    AuditLog.created_at >= datetime.utcnow() - timedelta(days=1)
                ).count(),
                'last_7d': AuditLog.query.filter(
                    AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count()
            }
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"System stats error: {str(e)}")
        return jsonify({'error': 'Failed to fetch system statistics'}), 500