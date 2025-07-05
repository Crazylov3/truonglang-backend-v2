#!/usr/bin/env python3
"""
Admin CLI Tool for Learnify LMS

This script provides administrative operations that bypass normal permission checks.
Use with caution - this tool has full system access.

Usage:
    python scripts/admin_cli.py --help
    # or from Docker container:
    uv run python scripts/admin_cli.py --help

Examples:
    # Create admin user
    python scripts/admin_cli.py create-admin --email admin@example.com --password secretpass

    # List all users
    python scripts/admin_cli.py list-users

    # Delete user
    python scripts/admin_cli.py delete-user --email user@example.com

    # Promote user to admin
    python scripts/admin_cli.py promote-user --email user@example.com --role admin
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional
import getpass

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

import click
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import AsyncSessionLocal
from app.models import User, UserRole, UserProfile
from app.config import settings
from app.core.operations import user as user_ops


def role_from_string(role_str: str) -> UserRole:
    """Convert string to UserRole enum."""
    role_map = {
        'student': UserRole.STUDENT,
        'instructor': UserRole.INSTRUCTOR,
        'staff': UserRole.STAFF,
        'admin': UserRole.ADMIN,
        '1': UserRole.STUDENT,
        '2': UserRole.INSTRUCTOR,
        '3': UserRole.STAFF,
        '4': UserRole.ADMIN,
    }
    return role_map.get(role_str.lower(), UserRole.STUDENT)


def role_to_string(role: UserRole) -> str:
    """Convert UserRole enum to string."""
    role_map = {
        UserRole.STUDENT: 'Student',
        UserRole.INSTRUCTOR: 'Instructor',
        UserRole.STAFF: 'Staff',
        UserRole.ADMIN: 'Admin',
    }
    return role_map.get(role, 'Unknown')


def get_user_display_name(user: User) -> str:
    """Get the display name for a user."""
    if user.profile and user.profile.first_name and user.profile.last_name:
        return f"{user.profile.first_name} {user.profile.last_name}"
    return user.email.split("@")[0]  # Fallback to email username


@click.group()
@click.version_option(version="1.0.0", prog_name="Learnify Admin CLI")
def cli():
    """
    🚀 Learnify Admin CLI Tool
    
    Administrative operations for the Learnify LMS system.
    ⚠️  WARNING: This tool bypasses normal permission checks!
    """
    pass


@cli.command()
@click.option('--email', prompt='Admin email', help='Email address for the admin user')
@click.option('--password', help='Password for the admin user (will prompt if not provided)')
@click.option('--first-name', help='First name of the admin user')
@click.option('--last-name', help='Last name of the admin user')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
def create_admin(email: str, password: str, first_name: str, last_name: str, force: bool):
    """Create a new admin user."""
    
    async def _create_admin():
        nonlocal password
        
        async with AsyncSessionLocal() as db:
            # Check if user already exists
            existing_user = await user_ops.get_user_by_email(db, email)
            if existing_user:
                click.echo(f"❌ User with email '{email}' already exists!")
                if existing_user.role == UserRole.ADMIN:
                    click.echo("   User is already an admin.")
                else:
                    if force or click.confirm(f"   Promote existing user to admin?"):
                        if await user_ops.update_user_role(db, email, UserRole.ADMIN):
                            click.echo(f"✅ User '{email}' promoted to admin!")
                        else:
                            click.echo(f"❌ Failed to promote user '{email}'")
                return
            
            # Get password if not provided
            if password is None:
                password = getpass.getpass("Admin password: ")
                password_confirm = getpass.getpass("Confirm password: ")
                if password != password_confirm:
                    click.echo("❌ Passwords don't match!")
                    return
            
            if not password or len(password) < 6:
                click.echo("❌ Password must be at least 6 characters long!")
                return
            
            # Show summary
            click.echo("\n📋 Admin User Summary:")
            click.echo(f"   Email: {email}")
            click.echo(f"   First Name: {first_name or 'Not provided'}")
            click.echo(f"   Last Name: {last_name or 'Not provided'}")
            click.echo(f"   Role: Admin")
            
            if not force and not click.confirm("\n✅ Create this admin user?"):
                click.echo("❌ Operation cancelled.")
                return
            
            try:
                # Create the admin user
                user = await user_ops.create_user(
                    db=db,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=UserRole.ADMIN
                )
                
                click.echo(f"\n🎉 Admin user created successfully!")
                click.echo(f"   ID: {user.id}")
                click.echo(f"   Email: {user.email}")
                click.echo(f"   Name: {get_user_display_name(user)}")
                click.echo(f"   Role: {role_to_string(user.role)}")
                click.echo(f"   Created: {user.created_at}")
                
            except SQLAlchemyError as e:
                click.echo(f"❌ Failed to create admin user: {e}")
    
    asyncio.run(_create_admin())


@cli.command()
@click.option('--role', type=click.Choice(['all', 'student', 'instructor', 'staff', 'admin'], case_sensitive=False), 
              default='all', help='Filter by role')
@click.option('--limit', type=int, default=50, help='Maximum number of users to display')
def list_users(role: str, limit: int):
    """List all users in the system."""
    
    async def _list_users():
        async with AsyncSessionLocal() as db:
            # Filter by role if specified
            filter_role = None if role == 'all' else role_from_string(role)
            
            users = await user_ops.list_users(db, role=filter_role, limit=limit)
            
            if not users:
                click.echo("📭 No users found in the system.")
                return
            
            click.echo(f"\n👥 Found {len(users)} users:")
            click.echo("=" * 80)
            
            for user in users:
                click.echo(f"🆔 ID: {user.id}")
                click.echo(f"📧 Email: {user.email}")
                click.echo(f"👤 Name: {get_user_display_name(user)}")
                click.echo(f"🎭 Role: {role_to_string(user.role)}")
                click.echo(f"📅 Created: {user.created_at}")
                if user.last_login_at:
                    click.echo(f"🕐 Last Login: {user.last_login_at}")
                click.echo("-" * 40)
    
    asyncio.run(_list_users())


@cli.command()
@click.option('--email', prompt='User email', help='Email of the user to delete')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
def delete_user(email: str, force: bool):
    """Delete a user from the system."""
    
    async def _delete_user():
        async with AsyncSessionLocal() as db:
            # Check if user exists
            user = await user_ops.get_user_by_email(db, email)
            if not user:
                click.echo(f"❌ User with email '{email}' not found!")
                return
            
            # Show user info
            click.echo(f"\n⚠️  User to delete:")
            click.echo(f"   ID: {user.id}")
            click.echo(f"   Email: {user.email}")
            click.echo(f"   Name: {get_user_display_name(user)}")
            click.echo(f"   Role: {role_to_string(user.role)}")
            click.echo(f"   Created: {user.created_at}")
            
            if not force:
                click.echo("\n⚠️  WARNING: This action cannot be undone!")
                if not click.confirm("🗑️  Are you sure you want to delete this user?"):
                    click.echo("❌ Operation cancelled.")
                    return
            
            try:
                if await user_ops.delete_user(db, email):
                    click.echo(f"✅ User '{email}' deleted successfully!")
                else:
                    click.echo(f"❌ Failed to delete user '{email}'")
            except Exception as e:
                click.echo(f"❌ Error deleting user: {e}")
    
    asyncio.run(_delete_user())


@cli.command()
@click.option('--email', prompt='User email', help='Email of the user to promote/demote')
@click.option('--role', prompt='New role', type=click.Choice(['student', 'instructor', 'staff', 'admin'], case_sensitive=False),
              help='New role for the user')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
def change_role(email: str, role: str, force: bool):
    """Change a user's role."""
    
    async def _change_role():
        async with AsyncSessionLocal() as db:
            # Check if user exists
            user = await user_ops.get_user_by_email(db, email)
            if not user:
                click.echo(f"❌ User with email '{email}' not found!")
                return
            
            new_role = role_from_string(role)
            current_role_str = role_to_string(user.role)
            new_role_str = role_to_string(new_role)
            
            if user.role == new_role:
                click.echo(f"ℹ️  User '{email}' already has role '{new_role_str}'")
                return
            
            # Show change summary
            click.echo(f"\n🔄 Role Change Summary:")
            click.echo(f"   User: {email}")
            click.echo(f"   Current Role: {current_role_str}")
            click.echo(f"   New Role: {new_role_str}")
            
            if not force and not click.confirm("\n✅ Apply this role change?"):
                click.echo("❌ Operation cancelled.")
                return
            
            try:
                if await user_ops.update_user_role(db, email, new_role):
                    click.echo(f"✅ User '{email}' role changed from '{current_role_str}' to '{new_role_str}'!")
                else:
                    click.echo(f"❌ Failed to change user role")
            except Exception as e:
                click.echo(f"❌ Error changing user role: {e}")
    
    asyncio.run(_change_role())


@cli.command()
def database_info():
    """Show database information and statistics."""
    
    async def _database_info():
        click.echo("🚀 Learnify Database Information")
        click.echo("=" * 50)
        
        async with AsyncSessionLocal() as session:
            try:
                # Database version
                result = await session.execute(text("SELECT version();"))
                version = result.scalar()
                click.echo(f"🗄️  Database: {version}")
                
                # Database size
                result = await session.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));"))
                size = result.scalar()
                click.echo(f"📦 Size: {size}")
                
                # User statistics
                result = await session.execute(text("""
                    SELECT 
                        CASE role::text
                            WHEN '1' THEN 'Students'
                            WHEN '2' THEN 'Instructors' 
                            WHEN '3' THEN 'Staff'
                            WHEN '4' THEN 'Admins'
                            ELSE 'Unknown'
                        END as user_type,
                        COUNT(*) as count
                    FROM users 
                    GROUP BY role
                    ORDER BY role::text;
                """))
                user_stats = result.fetchall()
                
                click.echo("\n👥 User Statistics:")
                total_users = 0
                for user_type, count in user_stats:
                    click.echo(f"   {user_type}: {count}")
                    total_users += count
                click.echo(f"   Total: {total_users}")
                
                # Table row counts
                tables = ['users', 'user_profiles', 'courses', 'enrollments', 'payments']
                click.echo("\n📊 Table Statistics:")
                for table in tables:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table};"))
                        count = result.scalar()
                        click.echo(f"   {table}: {count} rows")
                    except Exception as e:
                        click.echo(f"   {table}: Error reading ({str(e)[:50]}...)")
                        
            except SQLAlchemyError as e:
                click.echo(f"❌ Database error: {e}")
    
    asyncio.run(_database_info())


@cli.command()
@click.option('--email', help='Email to search for')
@click.option('--name', help='Name to search for (partial match)')
@click.option('--role', type=click.Choice(['student', 'instructor', 'staff', 'admin'], case_sensitive=False),
              help='Role to filter by')
def search_users(email: str, name: str, role: str):
    """Search for users by various criteria."""
    
    async def _search_users():
        async with AsyncSessionLocal() as db:
            try:
                role_enum = role_from_string(role) if role else None
                users = await user_ops.search_users(
                    db=db,
                    email=email,
                    name=name,
                    role=role_enum
                )
                
                if not users:
                    click.echo("📭 No users found matching your criteria.")
                    return
                
                click.echo(f"\n🔍 Found {len(users)} matching users:")
                click.echo("=" * 60)
                
                for user in users:
                    click.echo(f"🆔 ID: {user.id}")
                    click.echo(f"📧 Email: {user.email}")
                    click.echo(f"👤 Name: {get_user_display_name(user)}")
                    click.echo(f"🎭 Role: {role_to_string(user.role)}")
                    click.echo(f"📅 Created: {user.created_at}")
                    click.echo("-" * 40)
                    
            except SQLAlchemyError as e:
                click.echo(f"❌ Search error: {e}")
    
    asyncio.run(_search_users())


@cli.command()
@click.option('--email', prompt='User email', help='Email address for the user')
@click.option('--password', help='Password for the user (will prompt if not provided)')
@click.option('--first-name', help='First name of the user')
@click.option('--last-name', help='Last name of the user')
@click.option('--role', type=click.Choice(['student', 'instructor', 'staff', 'admin'], case_sensitive=False),
              default='student', help='Role for the user')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
def create_user(email: str, password: str, first_name: str, last_name: str, role: str, force: bool):
    """Create a new user with specified role."""
    
    async def _create_user():
        nonlocal password
        
        async with AsyncSessionLocal() as db:
            # Check if user already exists
            existing_user = await user_ops.get_user_by_email(db, email)
            if existing_user:
                click.echo(f"❌ User with email '{email}' already exists!")
                return
            
            # Get password if not provided
            if password is None:
                password = getpass.getpass("User password: ")
                password_confirm = getpass.getpass("Confirm password: ")
                if password != password_confirm:
                    click.echo("❌ Passwords don't match!")
                    return
            
            if not password or len(password) < 6:
                click.echo("❌ Password must be at least 6 characters long!")
                return
            
            user_role = role_from_string(role)
            
            # Show summary
            click.echo("\n📋 User Summary:")
            click.echo(f"   Email: {email}")
            click.echo(f"   First Name: {first_name or 'Not provided'}")
            click.echo(f"   Last Name: {last_name or 'Not provided'}")
            click.echo(f"   Role: {role_to_string(user_role)}")
            
            if not force and not click.confirm("\n✅ Create this user?"):
                click.echo("❌ Operation cancelled.")
                return
            
            try:
                # Create the user
                user = await user_ops.create_user(
                    db=db,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=user_role
                )
                
                click.echo(f"\n🎉 User created successfully!")
                click.echo(f"   ID: {user.id}")
                click.echo(f"   Email: {user.email}")
                click.echo(f"   Name: {get_user_display_name(user)}")
                click.echo(f"   Role: {role_to_string(user.role)}")
                click.echo(f"   Created: {user.created_at}")
                
            except SQLAlchemyError as e:
                click.echo(f"❌ Failed to create user: {e}")
    
    asyncio.run(_create_user())


@cli.command()
@click.option('--email', prompt='User email', help='Email of the user to update')
@click.option('--first-name', help='New first name')
@click.option('--last-name', help='New last name')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
def update_profile(email: str, first_name: str, last_name: str, force: bool):
    """Update a user's profile information."""
    
    async def _update_profile():
        async with AsyncSessionLocal() as db:
            # Check if user exists
            user = await user_ops.get_user_by_email(db, email)
            if not user:
                click.echo(f"❌ User with email '{email}' not found!")
                return
            
            # Check what's being updated
            updates = {}
            if first_name:
                updates['first_name'] = first_name
            if last_name:
                updates['last_name'] = last_name
            
            if not updates:
                click.echo("❌ No updates specified!")
                return
            
            # Show current info and proposed changes
            click.echo(f"\n👤 Current User Info:")
            click.echo(f"   Email: {user.email}")
            click.echo(f"   Current Name: {get_user_display_name(user)}")
            
            click.echo(f"\n🔄 Proposed Changes:")
            for field, value in updates.items():
                current_value = getattr(user.profile, field, 'Not set') if user.profile else 'Not set'
                click.echo(f"   {field.replace('_', ' ').title()}: {current_value} → {value}")
            
            if not force and not click.confirm("\n✅ Apply these changes?"):
                click.echo("❌ Operation cancelled.")
                return
            
            try:
                if await user_ops.update_user_profile(
                    db=db,
                    user_id=user.id,
                    first_name=first_name,
                    last_name=last_name
                ):
                    click.echo(f"✅ Profile updated successfully!")
                else:
                    click.echo(f"❌ Failed to update profile")
                
            except SQLAlchemyError as e:
                click.echo(f"❌ Failed to update profile: {e}")
    
    asyncio.run(_update_profile())


if __name__ == "__main__":
    cli() 