# routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import re
import uuid
import hashlib
from functools import wraps

from extensions import db
from models.user import User, Role, UserSession
from models.audit import AuditLog
from services.auth_service import log_activity, validate_password_strength

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

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

def generate_unique_session_token(user_id, access_token):
    """Generate a unique session token to avoid UNIQUE constraint failures"""
    # Create a unique identifier using user_id, timestamp, and partial token
    timestamp = datetime.utcnow().timestamp()
    unique_string = f"{user_id}_{timestamp}_{access_token[:20]}"
    
    # Hash it to create a consistent length token
    session_token = hashlib.sha256(unique_string.encode()).hexdigest()[:50]
    
    return session_token

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role.name != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        
        # Validate email format
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        password_validation = validate_password_strength(password)
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User already exists with this email'}), 409
        
        # Get default role (Business User)
        default_role = Role.query.filter_by(name='Business User').first()
        if not default_role:
            return jsonify({'error': 'Default role not found'}), 500
        
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=generate_password_hash(password),
            role_id=default_role.id,
            is_active=True,
            is_approved=False,  # Requires admin approval
            is_email_verified=False
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration
        log_activity(user.id, 'user_registered', {
            'email': email,
            'ip_address': request.remote_addr
        })
        
        return jsonify({
            'message': 'Registration successful! Please wait for admin approval.',
            'user_id': user.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            log_activity(None, 'login_failed', {
                'email': email,
                'ip_address': request.remote_addr,
                'reason': 'invalid_credentials'
            })
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check if user is active
        if not user.is_active:
            log_activity(user.id, 'login_failed', {
                'reason': 'account_inactive',
                'ip_address': request.remote_addr
            })
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Check if user is approved
        if not user.is_approved:
            log_activity(user.id, 'login_failed', {
                'reason': 'account_not_approved',
                'ip_address': request.remote_addr
            })
            return jsonify({'error': 'Account is pending approval'}), 401
        
        # Create access token
        access_token = create_access_token(
            identity=str(user.id),  # Convert to string for JWT
            expires_delta=timedelta(hours=24)
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Deactivate any existing sessions for this user (optional: comment out if you want multiple sessions)
        UserSession.query.filter_by(user_id=user.id, is_active=True).update({
            'is_active': False
        })
        
        # Create unique session token
        session_token = generate_unique_session_token(user.id, access_token)
        
        # Create user session
        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500],
            device_type=detect_device_type(request.headers.get('User-Agent', ''))
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Log successful login
        log_activity(user.id, 'login_success', {
            'ip_address': request.remote_addr,
            'device_type': session.device_type
        })
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        # Deactivate user sessions
        UserSession.query.filter_by(user_id=user_id, is_active=True).update({
            'is_active': False
        })
        
        db.session.commit()
        
        # Log logout
        log_activity(user_id, 'logout', {
            'ip_address': request.remote_addr
        })
        
        return jsonify({'message': 'Logged out successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()})
        
    except Exception as e:
        current_app.logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile'}), 500

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update user profile"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log profile update
        log_activity(user_id, 'profile_updated', {
            'ip_address': request.remote_addr
        })
        
        return jsonify({'user': user.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update profile error: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Both current and new passwords are required'}), 400
        
        # Verify current password
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password strength
        password_validation = validate_password_strength(new_password)
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Deactivate all other sessions
        UserSession.query.filter_by(user_id=user_id, is_active=True).update({
            'is_active': False
        })
        
        db.session.commit()
        
        # Log password change
        log_activity(user_id, 'password_changed', {
            'ip_address': request.remote_addr
        })
        
        return jsonify({'message': 'Password changed successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500

@auth_bp.route('/sessions', methods=['GET'])
def get_user_sessions():
    """Get user's active sessions"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        sessions = UserSession.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).order_by(UserSession.last_accessed.desc()).all()
        
        return jsonify({
            'sessions': [session.to_dict() for session in sessions]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get sessions error: {str(e)}")
        return jsonify({'error': 'Failed to get sessions'}), 500

@auth_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
def revoke_session(session_id):
    """Revoke a specific session"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        session = UserSession.query.filter_by(
            id=session_id, 
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        session.is_active = False
        db.session.commit()
        
        log_activity(user_id, 'session_revoked', {
            'session_id': session_id,
            'ip_address': request.remote_addr
        })
        
        return jsonify({'message': 'Session revoked successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Session revocation error: {str(e)}")
        return jsonify({'error': 'Failed to revoke session'}), 500

@auth_bp.route('/verify', methods=['GET'])
def verify_token():
    """Verify JWT token and return user info"""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert back to int
        
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid or inactive user'}), 401
        
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Token verification error: {str(e)}")
        return jsonify({'valid': False, 'error': 'Invalid token'}), 401