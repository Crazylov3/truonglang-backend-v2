"""Display utilities for admin CLI."""

import click
from typing import List, Dict, Any
from datetime import datetime
from app.models import User, Course, UserRole


def get_user_display_name(user: User) -> str:
    """Get the display name for a user."""
    if user.profile and user.profile.first_name and user.profile.last_name:
        return f"{user.profile.first_name} {user.profile.last_name}"
    return user.email.split("@")[0]  # Fallback to email username


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    if not dt:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: datetime) -> str:
    """Format date for display."""
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d")


def display_user_info(user: User, detailed: bool = False):
    """Display user information."""
    from .common import role_to_string
    
    click.echo(f"🆔 ID: {user.id}")
    click.echo(f"📧 Email: {user.email}")
    click.echo(f"👤 Name: {get_user_display_name(user)}")
    click.echo(f"🎭 Role: {role_to_string(user.role)}")
    
    if detailed:
        click.echo(f"📅 Created: {format_datetime(user.created_at)}")
        if user.last_login_at:
            click.echo(f"🕐 Last Login: {format_datetime(user.last_login_at)}")
        if user.need_change_password:
            click.echo(f"⚠️  Needs password change")
        if user.need_change_email:
            click.echo(f"⚠️  Needs email change")
        
        if user.profile:
            if user.profile.date_of_birth:
                click.echo(f"🎂 Birth Date: {format_date(user.profile.date_of_birth)}")


def display_course_info(course: Course, detailed: bool = False):
    """Display course information."""
    click.echo(f"🆔 ID: {course.id}")
    click.echo(f"📚 Title: {course.title}")
    click.echo(f"👨‍🏫 Creator ID: {course.creator_id}")
    
    if detailed:
        if course.description:
            click.echo(f"📝 Description: {course.description[:100]}...")
        if course.location:
            click.echo(f"📍 Location: {course.location}")
        if course.teacher_name:
            click.echo(f"👩‍🏫 Teacher: {course.teacher_name}")
        if course.start_date:
            click.echo(f"📅 Start Date: {format_date(course.start_date)}")
        if course.price:
            click.echo(f"💰 Price: ${course.price}")
        click.echo(f"📅 Created: {format_datetime(course.created_at)}")


def display_table(headers: List[str], rows: List[List[Any]], title: str = None):
    """Display data in a table format."""
    if title:
        click.echo(f"\n{title}")
        click.echo("=" * 80)
    
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(str(header))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(min(max_width + 2, 30))  # Cap at 30 chars
    
    # Print headers
    header_line = ""
    for i, header in enumerate(headers):
        header_line += str(header).ljust(col_widths[i])
    click.echo(header_line)
    click.echo("-" * sum(col_widths))
    
    # Print rows
    for row in rows:
        row_line = ""
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i] - 2:
                    cell_str = cell_str[:col_widths[i]-5] + "..."
                row_line += cell_str.ljust(col_widths[i])
        click.echo(row_line)


def display_stats(stats: Dict[str, Any], title: str = "Statistics"):
    """Display statistics in a formatted way."""
    click.echo(f"\n📊 {title}")
    click.echo("=" * 50)
    
    for key, value in stats.items():
        formatted_key = key.replace('_', ' ').title()
        click.echo(f"   {formatted_key}: {value}")