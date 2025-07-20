# app.py
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, verify_jwt_in_request, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text, inspect
import traceback
import json
from config import get_config, init_app_config
from extensions import db

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Initialize extensions with app
db.init_app(app)
migrate = Migrate(app, db)
cors = CORS(app, origins=["http://localhost:3000"])
jwt = JWTManager(app)

# Initialize app configuration
init_app_config(app)

# Import models after db initialization
from models.user import User, Role, Permission
from models.model import Model, ModelVersion
from models.persona import Persona, PersonaVersion
from models.agent import Agent, AgentExecution
from models.workflow import Workflow, WorkflowExecution
from models.tool import Tool, MCPServer
from models.audit import AuditLog

# Import routes
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.models import models_bp
from routes.personas import personas_bp
from routes.agents import agents_bp
from routes.workflows import workflows_bp
from routes.tools import tools_bp
from routes.dashboard import dashboard_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(models_bp, url_prefix='/api/models')
app.register_blueprint(personas_bp, url_prefix='/api/personas')
app.register_blueprint(agents_bp, url_prefix='/api/agents')
app.register_blueprint(workflows_bp, url_prefix='/api/workflows')
app.register_blueprint(tools_bp, url_prefix='/api/tools')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

def create_app(config_class=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object(get_config())
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    jwt.init_app(app)
    
    return app

def init_database():
    """Initialize database with proper error handling"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Create default roles if they don't exist
            roles_data = [
                {'name': 'Admin', 'description': 'Full system access'},
                {'name': 'Developer', 'description': 'Development and testing access'},
                {'name': 'Business User', 'description': 'Basic user access'}
            ]
            
            for role_data in roles_data:
                role = Role.query.filter_by(name=role_data['name']).first()
                if not role:
                    role = Role(
                        name=role_data['name'],
                        description=role_data['description']
                    )
                    db.session.add(role)
            
            # Create default admin user if it doesn't exist
            admin_user = User.query.filter_by(email='admin@queryforge.com').first()
            if not admin_user:
                admin_role = Role.query.filter_by(name='Admin').first()
                admin_user = User(
                    email='admin@queryforge.com',
                    first_name='System',
                    last_name='Administrator',
                    password_hash=generate_password_hash('admin123'),
                    role_id=admin_role.id,
                    is_active=True,
                    is_approved=True
                )
                db.session.add(admin_user)
            
            db.session.commit()
            app.logger.info("Database initialized successfully")
            
    except Exception as e:
        app.logger.error(f"Error initializing database: {str(e)}")
        db.session.rollback()

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}\n{traceback.format_exc()}")
    return jsonify({'error': 'An unexpected error occurred'}), 500

# Health check endpoint
@app.route('/api/health')
def health_check():
    try:
        # Check database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Initialize database when app starts
with app.app_context():
    init_database()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)