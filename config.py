# config.py
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///queryforge.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'txt', 'pdf'}
    
    # CORS Configuration
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Azure OpenAI Configuration
    LLM_CONFIG = {
        'azure': {
            'api_key': os.environ.get('AZURE_OPENAI_API_KEY') or 'your-azure-openai-api-key',
            'endpoint': os.environ.get('AZURE_OPENAI_ENDPOINT') or 'https://your-resource.openai.azure.com/',
            'api_version': os.environ.get('AZURE_OPENAI_API_VERSION') or '2024-02-01',
            'deployment_name': os.environ.get('AZURE_OPENAI_DEPLOYMENT') or 'gpt-4',
            'model_name': os.environ.get('AZURE_OPENAI_MODEL') or 'gpt-4',
            'max_tokens': int(os.environ.get('AZURE_OPENAI_MAX_TOKENS', 4000)),
            'temperature': float(os.environ.get('AZURE_OPENAI_TEMPERATURE', 0.7))
        }
    }
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'true').lower() == 'true'
    
    # Security Configuration
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application Configuration
    APP_NAME = 'QueryForge'
    APP_VERSION = '1.0.0'
    DEBUG = False
    TESTING = False
    
    # Database Configuration
    SQLALCHEMY_ECHO = False
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Cache Configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # Agent Execution Configuration
    AGENT_EXECUTION_TIMEOUT = int(os.environ.get('AGENT_EXECUTION_TIMEOUT', 300))  # 5 minutes
    MAX_CONCURRENT_EXECUTIONS = int(os.environ.get('MAX_CONCURRENT_EXECUTIONS', 10))
    
    # Workflow Configuration
    WORKFLOW_EXECUTION_TIMEOUT = int(os.environ.get('WORKFLOW_EXECUTION_TIMEOUT', 1800))  # 30 minutes
    MAX_WORKFLOW_NODES = int(os.environ.get('MAX_WORKFLOW_NODES', 50))
    
    # Tool Configuration
    TOOL_EXECUTION_TIMEOUT = int(os.environ.get('TOOL_EXECUTION_TIMEOUT', 60))  # 1 minute
    MAX_TOOL_RETRIES = int(os.environ.get('MAX_TOOL_RETRIES', 3))
    
    # Cost Management
    DEFAULT_COST_LIMIT_PER_USER = float(os.environ.get('DEFAULT_COST_LIMIT_PER_USER', 100.0))
    COST_TRACKING_ENABLED = os.environ.get('COST_TRACKING_ENABLED', 'true').lower() == 'true'
    
    # Audit Configuration
    AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 90))
    DETAILED_AUDIT_LOGGING = os.environ.get('DETAILED_AUDIT_LOGGING', 'true').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True for SQL query logging
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False  # Disable for easier API testing
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Relaxed limits for development
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    AGENT_EXECUTION_TIMEOUT = 600  # 10 minutes
    
    # Development-specific LLM settings
    LLM_CONFIG = Config.LLM_CONFIG.copy()
    LLM_CONFIG['azure']['temperature'] = 0.1  # More deterministic in dev


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Secure settings for production
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Stricter timeouts in production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    AGENT_EXECUTION_TIMEOUT = 300  # 5 minutes
    
    # Production database settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'max_overflow': 30
    }
    
    # Production logging
    LOG_LEVEL = 'INFO'
    LOG_TO_STDOUT = True
    
    # Enhanced security
    RATELIMIT_DEFAULT = "500 per hour"
    
    # Production cost management
    DEFAULT_COST_LIMIT_PER_USER = 50.0


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Fast timeouts for testing
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    AGENT_EXECUTION_TIMEOUT = 10
    WORKFLOW_EXECUTION_TIMEOUT = 30
    TOOL_EXECUTION_TIMEOUT = 5
    
    # Disable external services in testing
    COST_TRACKING_ENABLED = False
    DETAILED_AUDIT_LOGGING = False
    
    # Use mock LLM responses
    LLM_CONFIG = {
        'azure': {
            'api_key': 'test-key',
            'endpoint': 'https://test.openai.azure.com/',
            'api_version': '2024-02-01',
            'deployment_name': 'test-gpt-4',
            'model_name': 'gpt-4',
            'max_tokens': 1000,
            'temperature': 0.0
        }
    }


def get_config():
    """Get configuration class based on environment"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig


def init_app_config(app):
    """Initialize additional app configuration"""
    
    # Create required directories
    directories = [
        app.config['UPLOAD_FOLDER'],
        'logs',
        'data',
        'temp'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Configure logging
    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/queryforge.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('QueryForge startup')
    
    # Validate Azure OpenAI configuration
    azure_config = app.config['LLM_CONFIG']['azure']
    api_key = os.environ.get('AZURE_OPENAI_API_KEY') or azure_config.get('api_key')
    endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT') or azure_config.get('endpoint')
    
    if (api_key == 'your-azure-openai-api-key' or 
        endpoint == 'https://your-resource.openai.azure.com/'):
        app.logger.warning(
            "Azure OpenAI not configured. Chat functionality will be limited. "
            "Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables."
        )
    else:
        app.logger.info("Azure OpenAI configuration detected")
    
    # Configure Flask-JWT-Extended
    from flask_jwt_extended import JWTManager
    jwt = JWTManager(app)
    
    # JWT configuration
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        # TODO: Implement token blacklist checking
        return False
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token'}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'error': 'Authorization token is required'}, 401
    
    return app


def validate_database_config(config):
    """Validate database configuration"""
    try:
        from sqlalchemy import create_engine
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        connection = engine.connect()
        connection.close()
        return True
    except Exception as e:
        print(f"Database validation failed: {str(e)}")
        return False


def validate_environment():
    """Validate environment configuration"""
    errors = []
    warnings = []
    
    # Check required environment variables for production
    if os.environ.get('FLASK_ENV') == 'production':
        required_vars = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'DATABASE_URL'
        ]
        
        for var in required_vars:
            if not os.environ.get(var):
                errors.append(f"Missing required environment variable: {var}")
    
    # Check Azure OpenAI configuration
    azure_key = os.environ.get('AZURE_OPENAI_API_KEY')
    azure_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
    
    if not azure_key or azure_key == 'your-azure-openai-api-key':
        warnings.append("Azure OpenAI API key not configured")
    
    if not azure_endpoint or azure_endpoint == 'https://your-resource.openai.azure.com/':
        warnings.append("Azure OpenAI endpoint not configured")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


# Default configuration for immediate use (fallback)
if __name__ == '__main__':
    validation = validate_environment()
    if validation['warnings']:
        print("⚠️  Configuration warnings:")
        for warning in validation['warnings']:
            print(f"   - {warning}")
    
    if validation['errors']:
        print("❌ Configuration errors:")
        for error in validation['errors']:
            print(f"   - {error}")
    else:
        print("✅ Configuration validation passed")