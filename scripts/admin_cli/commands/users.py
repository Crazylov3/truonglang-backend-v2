"""User management commands for admin CLI."""

import click
import getpass
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.database import AsyncSessionLocal
from app.models import User, UserRole, UserProfile
from app.core.operations import user as user_ops
from ..utils import (
    role_from_string, role_to_string, async_command,
    display_user_info, display_table, validate_email,
    validate_password, validate_uuid, validate_user_role
)


@click.group(name='users')
def users_group():
    """👥 User management commands."""
    pass


@users_group.command()
@click.option('--email', prompt='Admin email', callback=validate_email, help='Email address for the admin user')
@click.option('--password', help='Password for the admin user (will prompt if not provided)')
@click.option('--first-name', help='First name of the admin user')
@click.option('--last-name', help='Last name of the admin user')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@async_command
async def create_admin(email: str, password: str, first_name: str, last_name: str, force: bool):
    """Create a new admin user."""
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        existing_user = await user_ops.get_user_by_email(db, email)
        if existing_user:
            click.echo(f"❌ User with email '{email}' already exists!")
            if existing_user.role == UserRole.ADMIN:
                click.echo("   User is already an admin.")
            else:
                if force or click.confirm(f"   Promote existing user to admin?"):
                    existing_user.role = UserRole.ADMIN
                    await db.commit()
                    click.echo(f"✅ User '{email}' promoted to admin!")
            return
        
        # Get password if not provided
        if password is None:
            password = getpass.getpass("Admin password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                click.echo("❌ Passwords don't match!")
                return
        
        # Validate password
        is_valid, error = validate_password(password)
        if not is_valid:
            click.echo(f"❌ {error}")
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
            display_user_info(user, detailed=True)
            
        except SQLAlchemyError as e:
            click.echo(f"❌ Failed to create admin user: {e}")


@users_group.command(name='list')
@click.option('--role', type=click.Choice(['all', 'student', 'instructor', 'staff', 'admin'], case_sensitive=False), 
              default='all', help='Filter by role')
@click.option('--limit', type=int, default=50, help='Maximum number of users to display')
@click.option('--offset', type=int, default=0, help='Number of users to skip')
@click.option('--search', help='Search in email and name')
@click.option('--format', type=click.Choice(['detailed', 'table']), default='detailed', help='Output format')
@async_command
async def list_users(role: str, limit: int, offset: int, search: str, format: str):
    """List users in the system."""
    async with AsyncSessionLocal() as db:
        # Build query
        query = select(User).options(selectinload(User.profile))
        
        # Filter by role
        if role != 'all':
            filter_role = role_from_string(role)
            query = query.where(User.role == filter_role)
        
        # Search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.email.ilike(search_pattern),
                    User.profile.has(UserProfile.first_name.ilike(search_pattern)),
                    User.profile.has(UserProfile.last_name.ilike(search_pattern))
                )
            )
        
        # Count total
        count_query = select(func.count()).select_from(User)
        if role != 'all':
            count_query = count_query.where(User.role == role_from_string(role))
        if search:
            count_query = count_query.where(
                or_(
                    User.email.ilike(search_pattern),
                    User.profile.has(UserProfile.first_name.ilike(search_pattern)),
                    User.profile.has(UserProfile.last_name.ilike(search_pattern))
                )
            )
        
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        if not users:
            click.echo("📭 No users found.")
            return
        
        click.echo(f"\n👥 Found {total_count} users (showing {len(users)}):")
        
        if format == 'table':
            rows = []
            for user in users:
                rows.append([
                    str(user.id)[:8] + "...",  # Show first 8 chars of UUID
                    user.email,
                    user.profile.first_name if user.profile else '',
                    user.profile.last_name if user.profile else '',
                    role_to_string(user.role),
                    user.created_at.strftime("%Y-%m-%d"),
                    user.last_login_at.strftime("%Y-%m-%d") if user.last_login_at else 'Never'
                ])
            
            display_table(
                ['ID', 'Email', 'First Name', 'Last Name', 'Role', 'Created', 'Last Login'],
                rows
            )
        else:
            click.echo("=" * 80)
            for user in users:
                display_user_info(user, detailed=True)
                click.echo("-" * 40)


@users_group.command()
@click.option('--email', prompt='User email', callback=validate_email, help='Email of the user')
@click.option('--field', type=click.Choice(['all', 'basic', 'activity', 'profile']), default='all', help='Information to display')
@async_command
async def info(email: str, field: str):
    """Show detailed information about a specific user."""
    async with AsyncSessionLocal() as db:
        user = await user_ops.get_user_by_email(db, email)
        if not user:
            click.echo(f"❌ User with email '{email}' not found!")
            return
        
        click.echo(f"\n📋 User Information for {email}")
        click.echo("=" * 60)
        
        if field in ['all', 'basic']:
            click.echo("\n🔤 Basic Information:")
            display_user_info(user, detailed=True)
        
        if field in ['all', 'activity']:
            click.echo("\n📊 Activity Information:")
            # Get enrollment count
            from app.models import Enrollment
            enrollment_count = await db.scalar(
                select(func.count()).select_from(Enrollment).where(Enrollment.student_id == user.id)
            )
            click.echo(f"   Enrolled Courses: {enrollment_count}")
            
            # Get created courses count if instructor
            if user.role in [UserRole.INSTRUCTOR, UserRole.STAFF, UserRole.ADMIN]:
                from app.models import Course
                course_count = await db.scalar(
                    select(func.count()).select_from(Course).where(Course.creator_id == user.id)
                )
                click.echo(f"   Created Courses: {course_count}")
        
        if field in ['all', 'profile'] and user.profile:
            click.echo("\n👤 Profile Information:")
            profile = user.profile
            click.echo(f"   Name: {profile.full_name}")
            if profile.date_of_birth:
                click.echo(f"   Birth Date: {profile.date_of_birth}")
            if profile.avatar:
                click.echo(f"   Avatar: {profile.avatar}")


@users_group.command()
@click.option('--email', prompt='User email', callback=validate_email, help='Email of the user to delete')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@async_command
async def delete(email: str, force: bool):
    """Delete a user from the system."""
    async with AsyncSessionLocal() as db:
        user = await user_ops.get_user_by_email(db, email)
        if not user:
            click.echo(f"❌ User with email '{email}' not found!")
            return
        
        # Show user info
        click.echo(f"\n⚠️  User to delete:")
        display_user_info(user)
        
        # Check for related data
        from app.models import Enrollment, Course
        enrollment_count = await db.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.student_id == user.id)
        )
        course_count = await db.scalar(
            select(func.count()).select_from(Course).where(Course.creator_id == user.id)
        )
        
        if enrollment_count > 0:
            click.echo(f"\n⚠️  This user has {enrollment_count} course enrollments")
        if course_count > 0:
            click.echo(f"⚠️  This user has created {course_count} courses")
        
        if not force:
            click.echo("\n⚠️  WARNING: This action cannot be undone!")
            if not click.confirm("🗑️  Are you sure you want to delete this user?"):
                click.echo("❌ Operation cancelled.")
                return
        
        try:
            success = await user_ops.delete_user(db, email)
            if success:
                click.echo(f"✅ User '{email}' deleted successfully!")
            else:
                click.echo(f"❌ Failed to delete user '{email}'.")
        except Exception as e:
            click.echo(f"❌ Error deleting user: {e}")


@users_group.command()
@click.option('--from-email', prompt='Current email', callback=validate_email, help='Current email of the user')
@click.option('--to-email', prompt='New email', callback=validate_email, help='New email for the user')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@async_command
async def change_email(from_email: str, to_email: str, force: bool):
    """Change a user's email address."""
    async with AsyncSessionLocal() as db:
        # Check if user exists
        user = await user_ops.get_user_by_email(db, from_email)
        if not user:
            click.echo(f"❌ User with email '{from_email}' not found!")
            return
        
        # Check if new email is already taken
        existing = await user_ops.get_user_by_email(db, to_email)
        if existing:
            click.echo(f"❌ Email '{to_email}' is already taken!")
            return
        
        click.echo(f"\n📧 Email Change Summary:")
        click.echo(f"   User ID: {user.id}")
        click.echo(f"   Current Email: {from_email}")
        click.echo(f"   New Email: {to_email}")
        
        if not force and not click.confirm("\n✅ Change this email?"):
            click.echo("❌ Operation cancelled.")
            return
        
        try:
            user.email = to_email
            user.need_change_email = False
            await db.commit()
            click.echo(f"✅ Email changed successfully!")
        except Exception as e:
            click.echo(f"❌ Error changing email: {e}")


@users_group.command()
@click.option('--email', prompt='User email', callback=validate_email, help='Email of the user')
@click.option('--password', help='New password (will prompt if not provided)')
@click.option('--require-change', is_flag=True, help='Require user to change password on next login')
@async_command
async def reset_password(email: str, password: str, require_change: bool):
    """Reset a user's password."""
    async with AsyncSessionLocal() as db:
        user = await user_ops.get_user_by_email(db, email)
        if not user:
            click.echo(f"❌ User with email '{email}' not found!")
            return
        
        # Get password if not provided
        if password is None:
            password = getpass.getpass("New password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                click.echo("❌ Passwords don't match!")
                return
        
        # Validate password
        is_valid, error = validate_password(password)
        if not is_valid:
            click.echo(f"❌ {error}")
            return
        
        try:
            from app.core.security import get_password_hash
            user.hashed_password = get_password_hash(password)
            user.need_change_password = require_change
            await db.commit()
            
            click.echo(f"✅ Password reset successfully!")
            if require_change:
                click.echo(f"   User will be required to change password on next login.")
                
        except Exception as e:
            click.echo(f"❌ Error resetting password: {e}")


@users_group.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@async_command
async def cleanup_inactive(dry_run: bool):
    """Clean up inactive users who never logged in."""
    async with AsyncSessionLocal() as db:
        # Find users who never logged in and created more than 30 days ago
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        query = select(User).where(
            User.last_login_at.is_(None),
            User.created_at < cutoff_date
        )
        
        result = await db.execute(query)
        inactive_users = result.scalars().all()
        
        if not inactive_users:
            click.echo("✅ No inactive users found.")
            return
        
        click.echo(f"\n🧹 Found {len(inactive_users)} inactive users:")
        click.echo("=" * 60)
        
        for user in inactive_users:
            display_user_info(user)
            click.echo("-" * 40)
        
        if dry_run:
            click.echo("\n⚠️  DRY RUN: No changes made.")
            return
        
        if click.confirm(f"\n🗑️  Delete {len(inactive_users)} inactive users?"):
            try:
                for user in inactive_users:
                    await db.delete(user)
                await db.commit()
                click.echo(f"✅ Deleted {len(inactive_users)} inactive users.")
            except Exception as e:
                click.echo(f"❌ Error during cleanup: {e}")


@users_group.command()
@click.option('--email', prompt='User email', callback=validate_email, help='Email of the user')
@click.option('--role', prompt='New role', type=click.Choice(['student', 'instructor', 'staff', 'admin']), help='New role')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@async_command
async def change_role(email: str, role: str, force: bool):
    """Change a user's role."""
    async with AsyncSessionLocal() as db:
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
            user.role = new_role
            await db.commit()
            click.echo(f"✅ User '{email}' role changed from '{current_role_str}' to '{new_role_str}'!")
        except Exception as e:
            click.echo(f"❌ Error changing user role: {e}")