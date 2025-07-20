# init_db.py
"""
Database initialization script for QueryForge
Run this script to set up the database with initial data
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.user import User, Role, Permission
from models.model import Model
from models.persona import Persona
from models.tool import Tool, MCPServer
from services.auth_service import create_default_permissions, assign_role_permissions

def init_database():
    """Initialize the database with tables and default data"""
    print("🚀 Initializing QueryForge database...")
    
    with app.app_context():
        try:
            # Create all tables
            print("📊 Creating database tables...")
            db.create_all()
            
            # Create default roles
            print("👥 Creating default roles...")
            create_default_roles()
            
            # Create default permissions
            print("🔐 Creating default permissions...")
            create_default_permissions()
            
            # Assign permissions to roles
            print("🎯 Assigning permissions to roles...")
            assign_role_permissions()
            
            # Create default admin user
            print("👤 Creating default admin user...")
            create_default_admin()
            
            # Create sample models
            print("🧠 Creating sample models...")
            create_sample_models()
            
            # Create sample personas
            print("🎭 Creating sample personas...")
            create_sample_personas()
            
            # Create sample tools
            print("🔧 Creating sample tools...")
            create_sample_tools()
            
            print("✅ Database initialization completed successfully!")
            print("\n📋 Default login credentials:")
            print("   Email: admin@queryforge.com")
            print("   Password: admin123")
            print("\n⚠️  Remember to change the default password after first login!")
            
        except Exception as e:
            print(f"❌ Error initializing database: {str(e)}")
            db.session.rollback()
            raise

def create_default_roles():
    """Create default system roles"""
    roles_data = [
        {
            'name': 'Admin',
            'description': 'System administrator with full access to all features and settings'
        },
        {
            'name': 'Developer',
            'description': 'Developer role with access to create and manage models, personas, agents, and workflows'
        },
        {
            'name': 'Business User',
            'description': 'Business user role with access to create agents and workflows using approved models and personas'
        }
    ]
    
    for role_data in roles_data:
        existing_role = Role.query.filter_by(name=role_data['name']).first()
        if not existing_role:
            role = Role(**role_data)
            db.session.add(role)
            print(f"   Created role: {role_data['name']}")
    
    db.session.commit()

def create_default_admin():
    """Create default admin user"""
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@queryforge.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    existing_admin = User.query.filter_by(email=admin_email).first()
    if not existing_admin:
        admin_role = Role.query.filter_by(name='Admin').first()
        
        admin = User(
            email=admin_email,
            first_name='System',
            last_name='Administrator',
            password_hash=generate_password_hash(admin_password),
            role_id=admin_role.id,
            is_active=True,
            is_approved=True,
            is_email_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        print(f"   Created admin user: {admin_email}")
    else:
        print(f"   Admin user already exists: {admin_email}")

def create_sample_models():
    """Create sample AI models"""
    models_data = [
        {
            'name': 'GPT-4 Turbo',
            'provider': 'azure_openai',
            'deployment_id': 'gpt-4-turbo',
            'model_name': 'gpt-4-turbo',
            'context_window': 128000,
            'max_tokens': 4096,
            'temperature': 0.1,
            'input_cost_per_token': 0.00001,
            'output_cost_per_token': 0.00003,
            'description': 'Latest GPT-4 Turbo model with 128K context window for complex tasks',
            'tags': ['gpt-4', 'turbo', 'large-context'],
            'is_approved': True
        },
        {
            'name': 'GPT-3.5 Turbo',
            'provider': 'azure_openai',
            'deployment_id': 'gpt-35-turbo',
            'model_name': 'gpt-3.5-turbo',
            'context_window': 16384,
            'max_tokens': 4096,
            'temperature': 0.1,
            'input_cost_per_token': 0.0000015,
            'output_cost_per_token': 0.000002,
            'description': 'Fast and efficient GPT-3.5 Turbo for general-purpose tasks',
            'tags': ['gpt-3.5', 'turbo', 'efficient'],
            'is_approved': True
        }
    ]
    
    admin_user = User.query.filter_by(email='admin@queryforge.com').first()
    
    for model_data in models_data:
        existing_model = Model.query.filter_by(name=model_data['name']).first()
        if not existing_model:
            model_data['created_by'] = admin_user.id
            model = Model(**model_data)
            db.session.add(model)
            print(f"   Created model: {model_data['name']}")
    
    db.session.commit()

def create_sample_personas():
    """Create sample AI personas"""
    personas_data = [
        {
            'name': 'Helpful Assistant',
            'description': 'A general-purpose AI assistant for answering questions and helping with tasks',
            'system_prompt': 'You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user queries. Be polite, professional, and concise in your communication.',
            'user_prompt_template': 'User question: {{input}}',
            'visibility': 'public',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'The user\'s question or request'
                    }
                },
                'required': ['query']
            },
            'output_schema': {
                'type': 'object',
                'properties': {
                    'response': {
                        'type': 'string',
                        'description': 'The assistant\'s response'
                    }
                },
                'required': ['response']
            },
            'tags': ['general', 'assistant', 'helpful'],
            'is_approved': True
        },
        {
            'name': 'Code Reviewer',
            'description': 'An expert code reviewer that analyzes code for quality, security, and best practices',
            'system_prompt': 'You are an expert code reviewer. Analyze code for quality, security vulnerabilities, performance issues, and adherence to best practices. Provide constructive feedback with specific suggestions for improvement.',
            'user_prompt_template': 'Please review this {{language}} code:\n\n```{{language}}\n{{input}}\n```\n\nProvide detailed feedback on code quality, security, and best practices.',
            'visibility': 'public',
            'variables': {
                'language': 'python'
            },
            'input_schema': {
                'type': 'object',
                'properties': {
                    'code': {
                        'type': 'string',
                        'description': 'The code to review'
                    },
                    'language': {
                        'type': 'string',
                        'description': 'Programming language'
                    }
                },
                'required': ['code']
            },
            'output_schema': {
                'type': 'object',
                'properties': {
                    'overall_rating': {
                        'type': 'string',
                        'enum': ['excellent', 'good', 'fair', 'poor']
                    },
                    'issues': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'type': {'type': 'string'},
                                'severity': {'type': 'string'},
                                'description': {'type': 'string'},
                                'suggestion': {'type': 'string'}
                            }
                        }
                    }
                }
            },
            'tags': ['code', 'review', 'development', 'quality'],
            'is_approved': True
        },
        {
            'name': 'Content Summarizer',
            'description': 'Summarizes long content into concise key points',
            'system_prompt': 'You are a content summarization expert. Create accurate, concise summaries that capture the key points and main ideas. Focus on the most important information while maintaining context.',
            'user_prompt_template': 'Please summarize the following content in {{length}} format:\n\n{{input}}\n\nProvide a clear summary with the main points.',
            'visibility': 'public',
            'variables': {
                'length': 'medium'
            },
            'input_schema': {
                'type': 'object',
                'properties': {
                    'content': {
                        'type': 'string',
                        'description': 'The content to summarize'
                    },
                    'length': {
                        'type': 'string',
                        'enum': ['short', 'medium', 'long'],
                        'description': 'Desired summary length'
                    }
                },
                'required': ['content']
            },
            'output_schema': {
                'type': 'object',
                'properties': {
                    'summary': {
                        'type': 'string',
                        'description': 'The summarized content'
                    },
                    'key_points': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of key points'
                    }
                },
                'required': ['summary', 'key_points']
            },
            'tags': ['summary', 'content', 'analysis'],
            'is_approved': True
        }
    ]
    
    admin_user = User.query.filter_by(email='admin@queryforge.com').first()
    
    for persona_data in personas_data:
        existing_persona = Persona.query.filter_by(name=persona_data['name']).first()
        if not existing_persona:
            persona_data['created_by'] = admin_user.id
            persona = Persona(**persona_data)
            db.session.add(persona)
            print(f"   Created persona: {persona_data['name']}")
    
    db.session.commit()

def create_sample_tools():
    """Create sample tools and MCP servers"""
    # Create sample MCP server
    mcp_servers_data = [
        {
            'name': 'Web Search Server',
            'description': 'MCP server for web search capabilities',
            'server_url': 'http://localhost:8000/mcp/websearch',
            'status': 'online',
            'capabilities': {
                'tools': ['web_search', 'web_fetch'],
                'version': '1.0.0'
            }
        }
    ]
    
    admin_user = User.query.filter_by(email='admin@queryforge.com').first()
    
    for server_data in mcp_servers_data:
        existing_server = MCPServer.query.filter_by(name=server_data['name']).first()
        if not existing_server:
            server_data['created_by'] = admin_user.id
            server = MCPServer(**server_data)
            db.session.add(server)
            db.session.flush()
            print(f"   Created MCP server: {server_data['name']}")
            
            # Create sample tools for this server
            tools_data = [
                {
                    'name': 'Web Search',
                    'description': 'Search the web for information',
                    'tool_type': 'mcp_server',
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
                    'mcp_server_id': server.id,
                    'safety_tags': ['web', 'search'],
                    'rate_limit': 100,
                    'is_approved': True,
                    'health_status': 'healthy'
                },
                {
                    'name': 'Web Fetch',
                    'description': 'Fetch content from a specific URL',
                    'tool_type': 'mcp_server',
                    'function_schema': {
                        'name': 'web_fetch',
                        'description': 'Fetch content from a specific URL',
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'url': {
                                    'type': 'string',
                                    'description': 'URL to fetch content from'
                                }
                            },
                            'required': ['url']
                        }
                    },
                    'mcp_server_id': server.id,
                    'safety_tags': ['web', 'fetch'],
                    'rate_limit': 50,
                    'is_approved': True,
                    'health_status': 'healthy'
                }
            ]
            
            for tool_data in tools_data:
                tool_data['created_by'] = admin_user.id
                tool = Tool(**tool_data)
                db.session.add(tool)
                print(f"     Created tool: {tool_data['name']}")
    
    db.session.commit()

def reset_database():
    """Reset the database (drop all tables and recreate)"""
    print("⚠️  Resetting database - all data will be lost!")
    confirmation = input("Are you sure you want to continue? (yes/no): ")
    
    if confirmation.lower() == 'yes':
        with app.app_context():
            print("🗑️  Dropping all tables...")
            db.drop_all()
            print("📊 Recreating database...")
            init_database()
    else:
        print("❌ Database reset cancelled.")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='QueryForge Database Initialization')
    parser.add_argument('--reset', action='store_true', help='Reset the database (drops all tables)')
    parser.add_argument('--init-only', action='store_true', help='Only create tables, skip sample data')
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    elif args.init_only:
        with app.app_context():
            print("📊 Creating database tables only...")
            db.create_all()
            print("✅ Database tables created successfully!")
    else:
        init_database()