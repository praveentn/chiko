# routes/admin.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import text, inspect, MetaData
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import traceback
import re
import math
from functools import wraps

from extensions import db                       # ← pull db from the shared extensions module
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
        
        if not sql_query:
            return jsonify({'error': 'SQL query cannot be empty'}), 400
        
        # Basic SQL injection protection
        dangerous_keywords = [
            'DROP DATABASE', 'DROP SCHEMA', 'TRUNCATE', 'DELETE FROM users',
            'UPDATE users SET', 'ALTER USER', 'CREATE USER', 'DROP USER'
        ]
        
        query_upper = sql_query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                log_activity(get_jwt_identity(), 'sql_execution_blocked', {
                    'query': sql_query[:100],
                    'reason': f'Blocked dangerous keyword: {keyword}'
                })
                return jsonify({'error': f'Query blocked: contains dangerous keyword "{keyword}"'}), 400
        
        # Determine query type
        query_type = 'SELECT'
        first_word = sql_query.split()[0].upper()
        if first_word in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE']:
            query_type = first_word
        
        # Execute query
        start_time = datetime.utcnow()
        
        if query_type == 'SELECT':
            # For SELECT queries, implement pagination
            result = execute_select_query(sql_query, page, per_page)
        else:
            # For other queries, execute directly
            result = execute_non_select_query(sql_query)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log the activity
        log_activity(get_jwt_identity(), 'sql_execution', {
            'query_type': query_type,
            'query': sql_query[:500],  # Log first 500 chars
            'execution_time_seconds': round(execution_time, 3),
            'rows_affected': result.get('rows_affected', 0),
            'page': page if query_type == 'SELECT' else None
        })
        
        result['execution_time'] = round(execution_time, 3)
        result['query_type'] = query_type
        
        return jsonify(result)
        
    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        log_activity(get_jwt_identity(), 'sql_execution_error', {
            'query': sql_query[:500],
            'error': error_msg
        })
        
        return jsonify({
            'error': 'SQL execution error',
            'details': error_msg,
            'query_type': query_type if 'query_type' in locals() else 'unknown'
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"SQL execution error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

def execute_select_query(sql_query, page, per_page):
    """Execute SELECT query with pagination"""
    # First, get total count
    count_query = f"SELECT COUNT(*) as total FROM ({sql_query}) as subquery"
    
    try:
        count_result = db.session.execute(text(count_query))
        total_rows = count_result.fetchone()[0]
    except:
        # If count fails, execute without pagination
        total_rows = None
    
    # Calculate pagination
    offset = (page - 1) * per_page
    
    # Add LIMIT and OFFSET to original query
    paginated_query = f"{sql_query} LIMIT {per_page} OFFSET {offset}"
    
    # Execute paginated query
    result = db.session.execute(text(paginated_query))
    
    # Get column names
    columns = list(result.keys()) if hasattr(result, 'keys') else []
    
    # Fetch data
    rows = []
    for row in result:
        row_data = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Round decimal values
            if isinstance(value, (float, int)) and isinstance(value, float):
                row_data[col] = round(value, 3)
            else:
                row_data[col] = value
        rows.append(row_data)
    
    # Calculate pagination info
    pagination = None
    if total_rows is not None:
        total_pages = math.ceil(total_rows / per_page) if total_rows > 0 else 1
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_rows': total_rows,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    
    return {
        'success': True,
        'columns': columns,
        'data': rows,
        'rows_returned': len(rows),
        'pagination': pagination
    }

def execute_non_select_query(sql_query):
    """Execute non-SELECT query (INSERT, UPDATE, DELETE, etc.)"""
    result = db.session.execute(text(sql_query))
    db.session.commit()
    
    rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
    
    return {
        'success': True,
        'message': 'Query executed successfully',
        'rows_affected': rows_affected
    }

@admin_bp.route('/sql/schema', methods=['GET'])
@admin_required
def get_database_schema():
    """Get database schema information"""
    try:
        inspector = inspect(db.engine)
        
        # Get all table names
        table_names = inspector.get_table_names()
        
        schema_info = {}
        for table_name in table_names:
            # Get columns for each table
            columns = inspector.get_columns(table_name)
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            
            schema_info[table_name] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                        'primary_key': col.get('primary_key', False),
                        'default': str(col['default']) if col['default'] is not None else None
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
        
        return jsonify({
            'success': True,
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': users.total,
                'total_pages': users.pages,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get users error: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    """Approve a user account"""
    try:
        user = User.query.get_or_404(user_id)
        user.is_approved = True
        db.session.commit()
        
        log_activity(get_jwt_identity(), 'user_approved', {
            'target_user_id': user_id,
            'target_user_email': user.email
        })
        
        return jsonify({
            'success': True,
            'message': f'User {user.email} has been approved'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"User approval error: {str(e)}")
        return jsonify({'error': 'Failed to approve user'}), 500

@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    """Update user role"""
    try:
        data = request.get_json()
        if not data or 'role_name' not in data:
            return jsonify({'error': 'Role name is required'}), 400
        
        user = User.query.get_or_404(user_id)
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