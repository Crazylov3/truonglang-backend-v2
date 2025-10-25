#!/usr/bin/env python3
"""
Giao Duc Thang Long Admin CLI Tool

This script provides administrative operations that bypass normal permission checks.
Use with caution - this tool has full system access.

Usage:
    python scripts/admin_cli.py --help
    # or from Docker container:
    uv run python scripts/admin_cli.py --help

Examples:
    # User management
    python scripts/admin_cli.py users list
    python scripts/admin_cli.py users create-admin --email admin@example.com --password secretpass
    
    # Course management
    python scripts/admin_cli.py courses list
    python scripts/admin_cli.py courses info --course-id 123
    
    # System management
    python scripts/admin_cli.py system info
    python scripts/admin_cli.py system health-check
    
    # Reports
    python scripts/admin_cli.py reports dashboard
    python scripts/admin_cli.py reports user-growth
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

import click

# Import command groups from our modular structure
from admin_cli.commands.users import users_group
from admin_cli.commands.courses import courses_group
from admin_cli.commands.system import system_group
from admin_cli.commands.audit import audit_group
from admin_cli.commands.attendance import attendance_group
from admin_cli.commands.reports import reports_group


# Add context for Click to enable object passing between commands
class Context:
    """Context object for passing state between commands."""
    def __init__(self):
        self.verbose = False
        self.debug = False


@click.pass_context
def get_context(ctx):
    """Get or create context."""
    if ctx.obj is None:
        ctx.obj = Context()
    return ctx.obj


@click.group()
@click.version_option(version="2.0.0", prog_name="GDTL Admin CLI")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx, verbose: bool, debug: bool):
    """
    🎓 Giao Duc Thang Long Admin CLI Tool
    
    Comprehensive administrative operations for the LMS system.
    
    ⚠️  WARNING: This tool bypasses normal permission checks!
    Use with caution - all operations have full system access.
    
    For help on specific commands:
        admin_cli.py [command] --help
    
    Common workflows:
    - User Management: users create-admin, users list, users reset-password
    - Course Management: courses list, courses create, courses enroll-student
    - System Health: system health-check, system database-info
    - Security: audit logs, audit security-summary
    - Reports: reports dashboard, reports user-growth
    """
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        click.echo("🐛 Debug mode enabled")


# Register command groups
cli.add_command(users_group)
cli.add_command(courses_group)
cli.add_command(system_group)
cli.add_command(audit_group)
cli.add_command(attendance_group)
cli.add_command(reports_group)


# Add some convenience commands at the root level
@cli.command()
def quick_start():
    """
    🚀 Quick start guide for common tasks.
    
    Shows common commands and workflows for administrators.
    """
    click.echo("\n🚀 GDTL Admin CLI Quick Start Guide")
    click.echo("=" * 60)
    
    click.echo("\n👥 User Management:")
    click.echo("   Create admin:       admin_cli.py users create-admin")
    click.echo("   List users:         admin_cli.py users list")
    click.echo("   Reset password:     admin_cli.py users reset-password")
    click.echo("   Change role:        admin_cli.py users change-role")
    click.echo("   Delete all students: admin_cli.py users delete-all-students")
    
    click.echo("\n📚 Course Management:")
    click.echo("   List courses:       admin_cli.py courses list")
    click.echo("   Create course:      admin_cli.py courses create")
    click.echo("   Enroll student:     admin_cli.py courses enroll-student")
    click.echo("   Course info:        admin_cli.py courses info")
    
    click.echo("\n🖥️ System Management:")
    click.echo("   System info:        admin_cli.py system info")
    click.echo("   Health check:       admin_cli.py system health-check")
    click.echo("   Database stats:     admin_cli.py system database-info")
    click.echo("   Clear cache:        admin_cli.py system clear-cache")
    
    click.echo("\n🔍 Security & Audit:")
    click.echo("   View logs:          admin_cli.py audit logs")
    click.echo("   Security summary:   admin_cli.py audit security-summary")
    click.echo("   User activity:      admin_cli.py audit user-activity")
    
    click.echo("\n✅ Attendance:")
    click.echo("   List cards:         admin_cli.py attendance cards")
    click.echo("   Assign card:        admin_cli.py attendance assign-card")
    click.echo("   View records:       admin_cli.py attendance records")
    
    click.echo("\n📊 Reports:")
    click.echo("   Dashboard:          admin_cli.py reports dashboard")
    click.echo("   User growth:        admin_cli.py reports user-growth")
    click.echo("   Popular courses:    admin_cli.py reports popular-courses")
    
    click.echo("\n💡 Tips:")
    click.echo("   - Use --help on any command for more options")
    click.echo("   - Add --force to skip confirmations")
    click.echo("   - Add -v for verbose output")
    click.echo("   - Most list commands support --limit and --format options")


@cli.command()
@click.pass_context
def interactive(ctx):
    """
    🎮 Interactive mode - guided command selection.
    
    Launches an interactive menu for easier navigation.
    """
    click.echo("\n🎮 Interactive Mode")
    click.echo("=" * 60)
    
    while True:
        click.echo("\n📋 Main Menu:")
        click.echo("1. User Management")
        click.echo("2. Course Management")
        click.echo("3. System Management")
        click.echo("4. Security & Audit")
        click.echo("5. Attendance")
        click.echo("6. Reports")
        click.echo("0. Exit")
        
        choice = click.prompt("\nSelect an option", type=int)
        
        if choice == 0:
            click.echo("\n👋 Goodbye!")
            break
        elif choice == 1:
            ctx.invoke(users_group)
        elif choice == 2:
            ctx.invoke(courses_group)
        elif choice == 3:
            ctx.invoke(system_group)
        elif choice == 4:
            ctx.invoke(audit_group)
        elif choice == 5:
            ctx.invoke(attendance_group)
        elif choice == 6:
            ctx.invoke(reports_group)
        else:
            click.echo("❌ Invalid choice. Please try again.")


def main():
    """Main entry point."""
    import warnings
    # Suppress SQLAlchemy warnings in production
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n\n👋 Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}")
        if '--debug' in sys.argv or '-d' in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 