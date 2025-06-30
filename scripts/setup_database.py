#!/usr/bin/env python3
"""
Database Setup Script for Learnify LMS

This script sets up the database from scratch:
1. Applies all migrations
2. Verifies the setup
3. Optionally creates sample data

Usage:
    python scripts/setup_database.py
    # or from Docker container:
    uv run python scripts/setup_database.py
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import AsyncSessionLocal
from app.config import settings


async def check_database_connection():
    """Check if we can connect to the database."""
    print("🔍 Checking database connection...")
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version}")
            return True
            
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Ensure PostgreSQL is running")
        print("   2. Check your database configuration")
        print("   3. Verify database credentials")
        return False


def run_migrations():
    """Run Alembic migrations to create tables."""
    print("🔄 Running database migrations...")
    
    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Migrations completed successfully!")
        if result.stdout:
            print("Migration output:")
            print(result.stdout)
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Alembic command not found. Try using 'uv run alembic upgrade head'")
        return False


async def verify_setup():
    """Verify that all tables were created correctly."""
    print("🔍 Verifying database setup...")
    
    expected_tables = {
        'users', 'user_avatars', 'courses', 
        'enrollments', 'transactions', 'payments', 
        'alembic_version'
    }
    
    async with AsyncSessionLocal() as session:
        try:
            # Check tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """))
            tables = {row[0] for row in result.fetchall()}
            
            print(f"📋 Found {len(tables)} tables:")
            for table in sorted(tables):
                status = "✅" if table in expected_tables else "⚠️"
                print(f"   {status} {table}")
            
            missing_tables = expected_tables - tables
            if missing_tables:
                print(f"\n❌ Missing expected tables: {', '.join(missing_tables)}")
                return False
            
            # Check enum types
            result = await session.execute(text("""
                SELECT typname 
                FROM pg_type 
                WHERE typtype = 'e' 
                AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                ORDER BY typname;
            """))
            enums = [row[0] for row in result.fetchall()]
            
            expected_enums = {'coursestatus', 'paymentstatus', 'userrole'}
            found_enums = set(enums)
            
            print(f"\n🔢 Found {len(enums)} enum types:")
            for enum in enums:
                status = "✅" if enum in expected_enums else "⚠️"
                print(f"   {status} {enum}")
            
            missing_enums = expected_enums - found_enums
            if missing_enums:
                print(f"\n❌ Missing expected enums: {', '.join(missing_enums)}")
                return False
            
            print("\n✅ Database setup verification completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False


async def create_sample_admin_user():
    """Optionally create a sample admin user."""
    response = input("\n🤔 Would you like to create a sample admin user? (yes/no): ")
    if response.lower() != 'yes':
        return
    
    try:
        from app.models.user import User, UserRole
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        async with AsyncSessionLocal() as session:
            # Check if admin user already exists
            result = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE role = 4")
            )
            admin_count = result.scalar()
            
            if admin_count > 0:
                print(f"ℹ️ Found {admin_count} admin user(s) already in database.")
                return
            
            # Create admin user
            admin_email = input("📧 Enter admin email (default: admin@learnify.com): ").strip()
            if not admin_email:
                admin_email = "admin@learnify.com"
            
            admin_password = input("🔒 Enter admin password (default: admin123): ").strip()
            if not admin_password:
                admin_password = "admin123"
            
            hashed_password = pwd_context.hash(admin_password)
            
            # Insert admin user
            await session.execute(text("""
                INSERT INTO users (email, hashed_password, first_name, last_name, role)
                VALUES (:email, :password, 'Admin', 'User', 4)
            """), {
                "email": admin_email,
                "password": hashed_password
            })
            
            await session.commit()
            
            print(f"✅ Admin user created successfully!")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")
            print("   ⚠️ Remember to change the password after first login!")
            
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")


def show_database_info():
    """Show current database configuration."""
    print("📊 Database Configuration:")
    print(f"   Host: {settings.db_host}")
    print(f"   Port: {settings.db_port}")
    print(f"   Database: {settings.db_name}")
    print(f"   User: {settings.db_user}")
    print()


async def main():
    """Main function to orchestrate the database setup."""
    print("🚀 Learnify Database Setup Tool")
    print("=" * 50)
    
    show_database_info()
    
    # Step 1: Check database connection
    if not await check_database_connection():
        return
    
    # Step 2: Run migrations
    if not run_migrations():
        return
    
    # Step 3: Verify setup
    if not await verify_setup():
        return
    
    # Step 4: Optionally create admin user
    await create_sample_admin_user()
    
    print("\n🎉 Database setup completed successfully!")
    print("\n📝 Your Learnify LMS database is ready to use!")
    print("   • All tables have been created")
    print("   • Database schema is up to date") 
    print("   • You can now start your FastAPI application")


if __name__ == "__main__":
    asyncio.run(main()) 