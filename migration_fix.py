# quick_fix.py
"""
Quick fix script to resolve all database and setup issues
Run this before starting the application
"""

import os
import sys
import subprocess
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        if isinstance(command, list):
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ {description} failed: {str(e)}")
        return False

def check_database_exists():
    """Check if database file exists"""
    return os.path.exists('queryforge.db')

def backup_database():
    """Create backup of existing database"""
    if check_database_exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"queryforge_backup_{timestamp}.db"
        try:
            import shutil
            shutil.copy2('queryforge.db', backup_name)
            print(f"✅ Database backed up as {backup_name}")
            return True
        except Exception as e:
            print(f"❌ Database backup failed: {str(e)}")
            return False
    return True

def fix_database_schema():
    """Fix database schema issues"""
    print("🔧 Fixing database schema...")
    try:
        from app import app, db
        from models.persona import Persona
        from models.user import User, Role
        from models.agent import Agent
        from models.workflow import Workflow
        from models.tool import Tool
        from models.model import Model
        from sqlalchemy import text, inspect
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Check and add missing columns
            inspector = inspect(db.engine)
            
            # Add is_active column to personas if missing
            personas_columns = [col['name'] for col in inspector.get_columns('personas')]
            if 'is_active' not in personas_columns:
                print("  Adding is_active column to personas table...")
                db.session.execute(text("ALTER TABLE personas ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
                db.session.execute(text("UPDATE personas SET is_active = 1 WHERE is_active IS NULL"))
            
            # Check other tables and add is_active if needed
            tables_to_check = ['agents', 'workflows', 'tools', 'models']
            for table_name in tables_to_check:
                try:
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    if 'is_active' not in columns:
                        print(f"  Adding is_active column to {table_name} table...")
                        db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
                        db.session.execute(text(f"UPDATE {table_name} SET is_active = 1 WHERE is_active IS NULL"))
                except Exception as e:
                    print(f"  Warning: Could not update {table_name}: {str(e)}")
            
            # Create default roles
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
            
            # Create default admin user
            admin_user = User.query.filter_by(email='admin@queryforge.com').first()
            if not admin_user:
                admin_role = Role.query.filter_by(name='Admin').first()
                if admin_role:
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
                    print("  ✅ Created default admin user")
            
            db.session.commit()
            print("✅ Database schema fixed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Database schema fix failed: {str(e)}")
        return False

def create_missing_files():
    """Create missing static files"""
    print("🔧 Creating missing static files...")
    
    # Create manifest.json if it doesn't exist
    manifest_content = {
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
    
    try:
        import json
        if not os.path.exists('manifest.json'):
            with open('manifest.json', 'w') as f:
                json.dump(manifest_content, f, indent=2)
            print("  ✅ Created manifest.json")
        
        # Create robots.txt
        if not os.path.exists('robots.txt'):
            with open('robots.txt', 'w') as f:
                f.write("User-agent: *\nDisallow:")
            print("  ✅ Created robots.txt")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create static files: {str(e)}")
        return False

def main():
    """Main fix function"""
    print("🚀 QueryForge Quick Fix Script")
    print("=" * 50)
    
    success = True
    
    # Backup existing database
    if not backup_database():
        print("⚠️  Database backup failed, continuing anyway...")
    
    # Fix database schema
    if not fix_database_schema():
        success = False
    
    # Create missing files
    if not create_missing_files():
        success = False
    
    if success:
        print("\n🎉 Quick fix completed successfully!")
        print("=" * 50)
        print("✅ Database schema updated")
        print("✅ Default admin user created")
        print("✅ Missing files created")
        print("\n📋 Default login credentials:")
        print("   Email: admin@queryforge.com")
        print("   Password: admin123")
        print("\n🚀 Next steps:")
        print("1. Start Flask server: python app.py")
        print("2. Start React frontend: npm start")
        print("3. Login and change default password")
        print("⚠️  Remember to change the default password after first login!")
    else:
        print("\n❌ Quick fix encountered errors!")
        print("Please check the error messages above and fix manually.")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)