# routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import re
from functools import wraps

from extensions import db                       # ← pull db from the shared extensions module
from models.user import User, Role, UserSession
from models.audit import AuditLog
from services.auth_service import log_activity, validate_password_strength

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        email = data['email'].lower().strip()
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        password = data['password']
        
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
            return jsonify({'error': 'User with this email already exists'}), 400
        
        # Get default role (Business User)
        default_role = Role.query.filter_by(name='Business User').first()
        if not default_role:
            # Create default role if it doesn't exist
            default_role = Role(name='Business User', description='Default business user role')
            db.session.add(default_role)
            db.session.flush()
        
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=generate_password_hash(password),
            role_id=default_role.id,
            is_active=True,
            is_approved=False  # Requires admin approval
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration
        log_activity(None, 'user_registered', {
            'user_id': user.id,
            'user_email': user.email,
            'ip_address': request.remote_addr
        })
        
        return jsonify({
            'message': 'Registration successful. Please wait for admin approval.',
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
            identity=user.id,
            expires_delta=timedelta(hours=24)
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Create user session
        session = UserSession(
            user_id=user.id,
            session_token=access_token[:50],  # Store partial token for reference
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
        user_id = get_jwt_identity()
        
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

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()})
        
    except Exception as e:
        current_app.logger.error(f"Get current user error: {str(e)}")
        return jsonify({'error': 'Failed to get user information'}), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        user = User.query.get(user_id)
        if not user or not user.is_active or not user.is_approved:
            return jsonify({'error': 'Invalid user'}), 401
        
        # Create new access token
        new_token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({'access_token': new_token})
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Token refresh failed'}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        data = request.get_json()
        if not data.get('old_password') or not data.get('new_password'):
            return jsonify({'error': 'Old and new passwords are required'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify old password
        if not check_password_hash(user.password_hash, data['old_password']):
            log_activity(user_id, 'password_change_failed', {
                'reason': 'invalid_old_password',
                'ip_address': request.remote_addr
            })
            return jsonify({'error': 'Invalid old password'}), 400
        
        # Validate new password strength
        password_validation = validate_password_strength(data['new_password'])
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Update password
        user.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        
        # Log password change
        log_activity(user_id, 'password_changed', {
            'ip_address': request.remote_addr
        })
        
        return jsonify({'message': 'Password changed successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password change error: {str(e)}")
        return jsonify({'error': 'Password change failed'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        data = request.get_json()
        if not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        email = data['email'].lower().strip()
        user = User.query.filter_by(email=email).first()
        
        # Always return success to prevent email enumeration
        message = 'If the email exists, a password reset link has been sent.'
        
        if user:
            # TODO: Implement password reset token generation and email sending
            # For now, just log the request
            log_activity(user.id, 'password_reset_requested', {
                'ip_address': request.remote_addr
            })
        
        return jsonify({'message': message})
        
    except Exception as e:
        current_app.logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'Request failed'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = request.get_json()
        if not data.get('token') or not data.get('new_password'):
            return jsonify({'error': 'Token and new password are required'}), 400
        
        # TODO: Implement token validation
        # For now, return not implemented
        return jsonify({'error': 'Password reset not implemented yet'}), 501
        
    except Exception as e:
        current_app.logger.error(f"Password reset error: {str(e)}")
        return jsonify({'error': 'Password reset failed'}), 500

@auth_bp.route('/sessions', methods=['GET'])
def get_user_sessions():
    """Get user's active sessions"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
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
        user_id = get_jwt_identity()
        
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

def detect_device_type(user_agent):
    """Detect device type from user agent"""
    user_agent = user_agent.lower()
    
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'