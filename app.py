# app.py
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
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

# Fix trailing slash redirects that cause CORS issues
app.url_map.strict_slashes = False

# Initialize extensions with app
db.init_app(app)
migrate = Migrate(app, db)

# Enhanced CORS configuration to handle preflight requests properly
cors = CORS(app, 
    origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=True
)

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

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Handle preflight OPTIONS requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(models_bp, url_prefix='/api/models')
app.register_blueprint(personas_bp, url_prefix='/api/personas')
app.register_blueprint(agents_bp, url_prefix='/api/agents')
app.register_blueprint(workflows_bp, url_prefix='/api/workflows')
app.register_blueprint(tools_bp, url_prefix='/api/tools')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

# Static file routes for manifest.json and other PWA files
@app.route('/manifest.json')
def serve_manifest():
    """Serve manifest.json for PWA support"""
    try:
        return send_file('manifest.json', mimetype='application/json')
    except FileNotFoundError:
        # Create a basic manifest if file doesn't exist
        manifest = {
            "name": "QueryForge",
            "short_name": "QueryForge",
            "description": "Zero-Code AI Workbench",
            "start_url": "/",
            "display": "standalone",
            "theme_color": "#3b82f6",
            "background_color": "#ffffff",
            "icons": [
                {
                    "src": "/logo192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                }
            ]
        }
        return jsonify(manifest)

@app.route('/robots.txt')
def serve_robots():
    """Serve robots.txt"""
    try:
        return send_file('robots.txt', mimetype='text/plain')
    except FileNotFoundError:
        return "User-agent: *\nDisallow:", 200, {'Content-Type': 'text/plain'}

@app.route('/favicon.ico')
def serve_favicon():
    """Serve favicon.ico"""
    try:
        return send_file('favicon.ico', mimetype='image/x-icon')
    except FileNotFoundError:
        return '', 404

@app.route('/logo192.png')
def serve_logo192():
    """Serve logo192.png for PWA"""
    try:
        return send_file('logo192.png', mimetype='image/png')
    except FileNotFoundError:
        # Return a placeholder response instead of 404
        return '', 204

@app.route('/logo512.png')
def serve_logo512():
    """Serve logo512.png for PWA"""
    try:
        return send_file('logo512.png', mimetype='image/png')
    except FileNotFoundError:
        return '', 204

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Database initialization endpoint
@app.route('/api/init-db', methods=['POST'])
def init_database():
    """Initialize database with tables and default data"""
    try:
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin_user = User.query.filter_by(email='admin@queryforge.com').first()
        if not admin_user:
            # Create default admin role if it doesn't exist
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin', description='System Administrator')
                db.session.add(admin_role)
                db.session.commit()
            
            # Create admin user
            admin_user = User(
                email='admin@queryforge.com',
                first_name='Admin',
                last_name='User',
                password_hash=generate_password_hash('admin123'),
                role_id=admin_role.id,
                is_active=True,
                is_approved=True,
                email_verified=True
            )
            db.session.add(admin_user)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database initialized successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database initialization error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Database initialization failed: {str(e)}'
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Database initialization
def create_tables():
    """Create database tables"""
    try:
        with app.app_context():
            db.create_all()
            app.logger.info("Database tables created successfully")
    except Exception as e:
        app.logger.error(f"Error creating database tables: {str(e)}")

if __name__ == '__main__':
    create_tables()
    
    # Initialize database with default data
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)