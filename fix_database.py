# fix_database.py
"""
Database fix script to add missing columns and resolve schema issues
Run this script to fix the database schema issues
"""

import os
import sys
from datetime import datetime
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.persona import Persona
from models.user import User, Role
from models.agent import Agent
from models.workflow import Workflow
from models.tool import Tool
from models.model import Model

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(db.engine)
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)
    except Exception as e:
        print(f"Error checking column {column_name} in table {table_name}: {str(e)}")
        return False

def add_missing_columns():
    """Add missing columns to tables"""
    print("🔧 Checking and adding missing columns...")
    
    try:
        # Check and add is_active column to personas table
        if not check_column_exists('personas', 'is_active'):
            print("  Adding is_active column to personas table...")
            db.session.execute(text("""
                ALTER TABLE personas 
                ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL
            """))
            
            # Update existing records
            db.session.execute(text("UPDATE personas SET is_active = 1 WHERE is_active IS NULL"))
            print("  ✅ Added is_active column to personas table")
        else:
            print("  ✅ is_active column already exists in personas table")
        
        # Check and add any other missing columns for other tables
        tables_to_check = [
            ('agents', 'is_active'),
            ('workflows', 'is_active'), 
            ('tools', 'is_active'),
            ('models', 'is_active')
        ]
        
        for table_name, column_name in tables_to_check:
            if not check_column_exists(table_name, column_name):
                print(f"  Adding {column_name} column to {table_name} table...")
                db.session.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {column_name} BOOLEAN DEFAULT 1 NOT NULL
                """))
                
                # Update existing records
                db.session.execute(text(f"UPDATE {table_name} SET {column_name} = 1 WHERE {column_name} IS NULL"))
                print(f"  ✅ Added {column_name} column to {table_name} table")
            else:
                print(f"  ✅ {column_name} column already exists in {table_name} table")
        
        db.session.commit()
        print("✅ All missing columns added successfully!")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"❌ Error adding missing columns: {str(e)}")
        raise

def verify_database_schema():
    """Verify that all required tables and columns exist"""
    print("🔍 Verifying database schema...")
    
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = [
            'users', 'roles', 'permissions', 'models', 'personas', 
            'agents', 'workflows', 'tools', 'audit_logs'
        ]
        
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        
        # Check critical columns
        critical_columns = [
            ('personas', 'is_active'),
            ('personas', 'is_approved'),
            ('agents', 'is_active'),
            ('workflows', 'is_active'),
            ('tools', 'is_active'),
            ('models', 'is_active')
        ]
        
        for table_name, column_name in critical_columns:
            if not check_column_exists(table_name, column_name):
                print(f"❌ Missing column {column_name} in table {table_name}")
                return False
        
        print("✅ Database schema verification passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying database schema: {str(e)}")
        return False

def create_default_roles():
    """Create default roles if they don't exist"""
    print("👥 Creating default roles...")
    
    try:
        default_roles = [
            ('Admin', 'System Administrator with full access'),
            ('Developer', 'Developer with access to technical features'),
            ('Business User', 'Business user with limited access'),
            ('Viewer', 'Read-only access user')
        ]
        
        for role_name, description in default_roles:
            existing_role = Role.query.filter_by(name=role_name).first()
            if not existing_role:
                role = Role(name=role_name, description=description)
                db.session.add(role)
                print(f"  ✅ Created role: {role_name}")
            else:
                print(f"  ✅ Role {role_name} already exists")
        
        db.session.commit()
        print("✅ Default roles created successfully!")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"❌ Error creating default roles: {str(e)}")
        raise

def create_default_admin():
    """Create default admin user if it doesn't exist"""
    print("👤 Creating default admin user...")
    
    try:
        admin_user = User.query.filter_by(email='admin@queryforge.com').first()
        if not admin_user:
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                raise Exception("Admin role not found. Create roles first.")
            
            from werkzeug.security import generate_password_hash
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
            print("  ✅ Created default admin user")
            print("     Email: admin@queryforge.com")
            print("     Password: admin123")
        else:
            print("  ✅ Admin user already exists")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        raise

def fix_database():
    """Main function to fix all database issues"""
    print("🚀 Starting database fix process...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Create all tables first
            print("📊 Creating database tables...")
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Add missing columns
            add_missing_columns()
            
            # Create default roles
            create_default_roles()
            
            # Create default admin user
            create_default_admin()
            
            # Verify schema
            if verify_database_schema():
                print("\n🎉 Database fix completed successfully!")
                print("=" * 50)
                print("Next steps:")
                print("1. Restart your Flask application")
                print("2. Clear browser cache and refresh")
                print("3. Login with admin@queryforge.com / admin123")
                print("4. Change the default password after first login")
            else:
                print("\n❌ Database schema verification failed!")
                return False
                
        except Exception as e:
            print(f"\n❌ Database fix failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    success = fix_database()
    sys.exit(0 if success else 1)