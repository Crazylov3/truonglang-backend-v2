#!/usr/bin/env python3
"""
Database Reset Script for Learnify LMS

This script completely clears the database and resets it to a clean state.
Use this when you want to start fresh or resolve migration conflicts.

Usage:
    python scripts/clear_database.py
    # or from Docker container:
    uv run python scripts/clear_database.py
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import AsyncSessionLocal, sync_engine
from app.config import settings


async def clear_database():
    """Clear all tables and types from the database."""
    print("🔄 Starting database reset process...")
    
    # Step 1: Drop and recreate schema (this handles most cleanup)
    async with AsyncSessionLocal() as session:
        try:
            print("📋 Dropping all tables and schema...")
            await session.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
            await session.commit()
            print("✅ Schema dropped!")
        except SQLAlchemyError as e:
            await session.rollback()
            print(f"❌ Error dropping schema: {e}")
            return False

    # Step 2: Recreate schema
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("CREATE SCHEMA public;"))
            await session.commit()
            print("✅ Schema recreated!")
        except SQLAlchemyError as e:
            await session.rollback()
            print(f"❌ Error creating schema: {e}")
            return False

    # Step 3: Grant permissions to public
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            print(f"❌ Error granting permissions to public: {e}")
            return False

    # Step 4: Try to grant to postgres role (optional)
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            print("ℹ️ Note: postgres role not found (this is normal in some setups)")

    print("✅ Database cleared successfully!")
    return True


def clear_alembic_version():
    """Clear Alembic version tracking."""
    print("🔄 Clearing Alembic version history...")
    
    try:
        with sync_engine.connect() as conn:
            # Drop alembic_version table if it exists
            conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
            conn.commit()
            print("✅ Alembic version history cleared!")
            
    except SQLAlchemyError as e:
        print(f"⚠️ Warning: Could not clear Alembic version: {e}")


def show_database_info():
    """Show current database configuration."""
    print("📊 Database Configuration:")
    print(f"   Host: {settings.db_host}")
    print(f"   Port: {settings.db_port}")
    print(f"   Database: {settings.db_name}")
    print(f"   User: {settings.db_user}")
    print()


async def verify_empty_database():
    """Verify that the database is empty."""
    print("🔍 Verifying database is empty...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Check for any remaining tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE';
            """))
            tables = result.fetchall()
            
            if tables:
                print(f"⚠️ Warning: Found {len(tables)} remaining tables:")
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("✅ Database is completely empty!")
                
            # Check for enum types
            result = await session.execute(text("""
                SELECT typname 
                FROM pg_type 
                WHERE typtype = 'e' 
                AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');
            """))
            enums = result.fetchall()
            
            if enums:
                print(f"⚠️ Warning: Found {len(enums)} remaining enum types:")
                for enum in enums:
                    print(f"   - {enum[0]}")
            else:
                print("✅ No enum types found!")
                
        except SQLAlchemyError as e:
            print(f"❌ Error verifying database: {e}")


async def main():
    """Main function to orchestrate the database reset."""
    print("🚀 Learnify Database Reset Tool")
    print("=" * 50)
    
    show_database_info()
    
    # Ask for confirmation
    response = input("⚠️ This will PERMANENTLY DELETE all data. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled.")
        return
    
    print("\n🔄 Starting reset process...\n")
    
    # Step 1: Clear the database
    if not await clear_database():
        print("❌ Failed to clear database. Exiting.")
        return
    
    # Step 2: Clear Alembic version tracking
    clear_alembic_version()
    
    # Step 3: Verify the database is empty
    await verify_empty_database()
    
    print("\n🎉 Database reset completed successfully!")
    print("\n📝 Next steps:")
    print("   1. Run: alembic upgrade head")
    print("   2. Start your application")
    print("   3. Create your first admin user")


if __name__ == "__main__":
    asyncio.run(main()) 