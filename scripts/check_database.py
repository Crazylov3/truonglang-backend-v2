#!/usr/bin/env python3
"""
Database Status Checker for Learnify LMS

This script checks the current status of the database:
1. Connection status
2. Migration status
3. Table and data summary
4. Health checks

Usage:
    python scripts/check_database.py
    # or from Docker container:
    uv run python scripts/check_database.py
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


async def check_connection():
    """Check database connection and basic info."""
    print("🔍 Database Connection Status")
    print("-" * 30)
    
    try:
        async with AsyncSessionLocal() as session:
            # Get PostgreSQL version
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()
            
            # Get database size
            result = await session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()));
            """))
            db_size = result.scalar()
            
            # Get current user and database
            result = await session.execute(text("SELECT current_user, current_database();"))
            user, database = result.fetchone()
            
            print(f"✅ Connection: Successful")
            print(f"📊 Database: {database}")
            print(f"👤 User: {user}")
            print(f"📦 Size: {db_size}")
            print(f"🔧 Version: {version.split(',')[0]}")
            return True
            
    except Exception as e:
        print(f"❌ Connection: Failed")
        print(f"   Error: {e}")
        return False


def check_migrations():
    """Check Alembic migration status."""
    print("\n🔄 Migration Status")
    print("-" * 20)
    
    try:
        # Check current migration
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            check=True
        )
        
        current_output = result.stdout.strip()
        if "None" in current_output or not current_output:
            print("❌ No migrations applied")
            return False
        else:
            print(f"✅ Current: {current_output}")
        
        # Check if migrations are up to date
        result = subprocess.run(
            ["alembic", "heads"],
            capture_output=True,
            text=True,
            check=True
        )
        
        heads_output = result.stdout.strip()
        print(f"📋 Latest: {heads_output}")
        
        if current_output.split()[0] == heads_output.split()[0]:
            print("✅ Status: Up to date")
            return True
        else:
            print("⚠️ Status: Needs migration")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration check failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ Alembic command not found")
        return False


async def check_tables():
    """Check database tables and their row counts."""
    print("\n📋 Database Tables")
    print("-" * 18)
    
    async with AsyncSessionLocal() as session:
        try:
            # Get all tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if not tables:
                print("❌ No tables found")
                return
            
            total_rows = 0
            for table in tables:
                try:
                    # Get row count for each table
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table};"))
                    count = result.scalar()
                    total_rows += count
                    
                    emoji = "📝" if count > 0 else "📄"
                    print(f"   {emoji} {table:15} {count:>6} rows")
                    
                except Exception as e:
                    print(f"   ❌ {table:15} Error: {e}")
            
            print(f"\n📊 Total: {len(tables)} tables, {total_rows} rows")
            
        except Exception as e:
            print(f"❌ Failed to check tables: {e}")


async def check_enums():
    """Check enum types in the database."""
    print("\n🔢 Enum Types")
    print("-" * 12)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("""
                SELECT 
                    t.typname as enum_name,
                    array_to_string(array_agg(e.enumlabel ORDER BY e.enumsortorder), ', ') as values
                FROM pg_type t 
                JOIN pg_enum e ON t.oid = e.enumtypid  
                WHERE t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                GROUP BY t.typname
                ORDER BY t.typname;
            """))
            enums = result.fetchall()
            
            if not enums:
                print("   No enum types found")
                return
            
            for enum_name, values in enums:
                print(f"   ✅ {enum_name}: {values}")
                
        except Exception as e:
            print(f"❌ Failed to check enums: {e}")


async def check_indexes():
    """Check database indexes."""
    print("\n🗂️ Database Indexes")
    print("-" * 18)
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
            """))
            indexes = result.fetchall()
            
            if not indexes:
                print("   No indexes found")
                return
            
            current_table = None
            for schema, table, index, definition in indexes:
                if table != current_table:
                    if current_table is not None:
                        print()
                    print(f"   📋 {table}:")
                    current_table = table
                
                index_type = "🔑" if "PRIMARY KEY" in definition else "📇"
                print(f"      {index_type} {index}")
                
        except Exception as e:
            print(f"❌ Failed to check indexes: {e}")


async def check_sample_data():
    """Check for sample data in key tables."""
    print("\n👥 Sample Data Summary")
    print("-" * 23)
    
    async with AsyncSessionLocal() as session:
        try:
            # Check users by role
            result = await session.execute(text("""
                SELECT 
                    CASE role
                        WHEN 1 THEN 'Students'
                        WHEN 2 THEN 'Instructors'
                        WHEN 3 THEN 'Staff'
                        WHEN 4 THEN 'Admins'
                        ELSE 'Unknown'
                    END as user_type,
                    COUNT(*) as count
                FROM users 
                GROUP BY role
                ORDER BY role;
            """))
            users = result.fetchall()
            
            if users:
                print("   👤 Users:")
                for user_type, count in users:
                    print(f"      • {user_type}: {count}")
            else:
                print("   👤 Users: None")
            
            # Check courses by status
            result = await session.execute(text("""
                SELECT status, COUNT(*) as count
                FROM courses 
                GROUP BY status
                ORDER BY status;
            """))
            courses = result.fetchall()
            
            if courses:
                print("   📚 Courses:")
                for status, count in courses:
                    print(f"      • {status.title()}: {count}")
            else:
                print("   📚 Courses: None")
            
            # Check enrollments
            result = await session.execute(text("SELECT COUNT(*) FROM enrollments;"))
            enrollment_count = result.scalar()
            print(f"   🎓 Enrollments: {enrollment_count}")
            
        except Exception as e:
            print(f"❌ Failed to check sample data: {e}")


def show_database_config():
    """Show current database configuration."""
    print("⚙️ Database Configuration")
    print("-" * 26)
    print(f"   Host: {settings.db_host}")
    print(f"   Port: {settings.db_port}")
    print(f"   Database: {settings.db_name}")
    print(f"   User: {settings.db_user}")


async def main():
    """Main function to run all database checks."""
    print("🚀 Learnify Database Status Checker")
    print("=" * 50)
    
    show_database_config()
    
    # Run all checks
    connection_ok = await check_connection()
    
    if connection_ok:
        migration_ok = check_migrations()
        await check_tables()
        await check_enums()
        await check_indexes()
        await check_sample_data()
        
        print("\n" + "=" * 50)
        if migration_ok:
            print("🎉 Database status: Healthy")
        else:
            print("⚠️ Database status: Needs attention")
            print("💡 Consider running: alembic upgrade head")
    else:
        print("\n" + "=" * 50)
        print("❌ Database status: Unavailable")
        print("💡 Check your database connection and configuration")


if __name__ == "__main__":
    asyncio.run(main()) 