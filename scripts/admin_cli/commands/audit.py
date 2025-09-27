"""Audit and security commands for admin CLI."""

import click
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.database import AsyncSessionLocal
from app.models import AuditLog, User, AuditAction, AuditResource, AuditSeverity
from ..utils import (
    async_command, display_table, validate_email, parse_date,
    format_datetime, display_stats
)


@click.group(name='audit')
def audit_group():
    """🔍 Audit and security commands."""
    pass


@audit_group.command(name='logs')
@click.option('--limit', type=int, default=50, help='Number of logs to display')
@click.option('--user-email', callback=validate_email, help='Filter by user email')
@click.option('--action', type=click.Choice(['login', 'logout', 'create', 'update', 'delete', 'api_call']), help='Filter by action')
@click.option('--severity', type=click.Choice(['info', 'warning', 'error', 'critical', 'security']), help='Filter by severity')
@click.option('--since', callback=parse_date, help='Show logs since date (YYYY-MM-DD)')
@click.option('--format', type=click.Choice(['detailed', 'table']), default='table', help='Output format')
@async_command
async def list_logs(limit: int, user_email: str, action: str, severity: str, since, format: str):
    """View audit logs."""
    async with AsyncSessionLocal() as db:
        # Build query
        query = select(AuditLog).options(selectinload(AuditLog.user))
        
        # Apply filters
        if user_email:
            user = await db.scalar(select(User).where(User.email == user_email))
            if not user:
                click.echo(f"❌ User '{user_email}' not found!")
                return
            query = query.where(AuditLog.user_id == user.id)
        
        if action:
            action_map = {
                'login': AuditAction.LOGIN,
                'logout': AuditAction.LOGOUT,
                'create': AuditAction.CREATE,
                'update': AuditAction.UPDATE,
                'delete': AuditAction.DELETE,
                'api_call': AuditAction.API_CALL
            }
            query = query.where(AuditLog.action == action_map[action])
        
        if severity:
            severity_map = {
                'info': AuditSeverity.INFO,
                'warning': AuditSeverity.WARNING,
                'error': AuditSeverity.ERROR,
                'critical': AuditSeverity.CRITICAL,
                'security': AuditSeverity.SECURITY
            }
            query = query.where(AuditLog.severity == severity_map[severity])
        
        if since:
            query = query.where(AuditLog.created_at >= since)
        
        # Order and limit
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        if not logs:
            click.echo("📭 No audit logs found.")
            return
        
        click.echo(f"\n🔍 Audit Logs (showing {len(logs)}):")
        
        if format == 'table':
            rows = []
            for log in logs:
                action_name = AuditAction(log.action).name if log.action else 'UNKNOWN'
                severity_name = AuditSeverity(log.severity).name if log.severity else 'INFO'
                user_email = log.user.email if log.user else log.user_email or 'System'
                
                rows.append([
                    log.id,
                    format_datetime(log.created_at),
                    user_email,
                    action_name,
                    severity_name,
                    log.operation_summary[:50]
                ])
            
            display_table(
                ['ID', 'Timestamp', 'User', 'Action', 'Severity', 'Summary'],
                rows
            )
        else:
            click.echo("=" * 80)
            for log in logs:
                display_audit_log(log, detailed=True)
                click.echo("-" * 40)


@audit_group.command()
@click.option('--log-id', type=int, prompt='Audit log ID', help='ID of the audit log')
@async_command
async def log_detail(log_id: int):
    """Show detailed information about a specific audit log."""
    async with AsyncSessionLocal() as db:
        log = await db.get(AuditLog, log_id)
        if not log:
            click.echo(f"❌ Audit log with ID '{log_id}' not found!")
            return
        
        await db.refresh(log, ['user'])
        
        click.echo(f"\n📋 Audit Log Details (ID: {log_id})")
        click.echo("=" * 60)
        
        display_audit_log(log, detailed=True, show_all=True)


@audit_group.command()
@click.option('--period', type=click.Choice(['day', 'week', 'month']), default='week', help='Time period')
@async_command
async def security_summary(period: str):
    """Show security summary and suspicious activity."""
    async with AsyncSessionLocal() as db:
        # Calculate date range
        now = datetime.utcnow()
        if period == 'day':
            since_date = now - timedelta(days=1)
        elif period == 'week':
            since_date = now - timedelta(weeks=1)
        else:
            since_date = now - timedelta(days=30)
        
        click.echo(f"\n🛡️ Security Summary (Last {period})")
        click.echo("=" * 60)
        
        # Failed login attempts
        failed_logins = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == AuditAction.LOGIN,
                AuditLog.operation_summary.like('%Failed%'),
                AuditLog.created_at >= since_date
            )
        )
        
        # Successful logins
        successful_logins = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == AuditAction.LOGIN,
                AuditLog.operation_summary.like('%success%'),
                AuditLog.created_at >= since_date
            )
        )
        
        # Security events
        security_events = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.severity >= AuditSeverity.ERROR,
                AuditLog.created_at >= since_date
            )
        )
        
        # Role changes
        role_changes = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == AuditAction.ROLE_CHANGE,
                AuditLog.created_at >= since_date
            )
        )
        
        stats = {
            'Successful Logins': successful_logins,
            'Failed Login Attempts': failed_logins,
            'Security Events': security_events,
            'Role Changes': role_changes
        }
        
        display_stats(stats, "Security Statistics")
        
        # Show top IPs with failed logins
        failed_ip_query = await db.execute(
            select(
                AuditLog.ip_address,
                func.count().label('count')
            )
            .where(
                AuditLog.action == AuditAction.LOGIN,
                AuditLog.operation_summary.like('%Failed%'),
                AuditLog.created_at >= since_date,
                AuditLog.ip_address.isnot(None)
            )
            .group_by(AuditLog.ip_address)
            .order_by(func.count().desc())
            .limit(5)
        )
        failed_ips = failed_ip_query.all()
        
        if failed_ips:
            click.echo("\n🚫 Top IPs with Failed Login Attempts:")
            for ip, count in failed_ips:
                click.echo(f"   {ip}: {count} attempts")


@audit_group.command()
@click.option('--user-email', prompt='User email', callback=validate_email, help='Email of the user')
@click.option('--days', type=int, default=30, help='Number of days to look back')
@async_command
async def user_activity(user_email: str, days: int):
    """Show activity history for a specific user."""
    async with AsyncSessionLocal() as db:
        # Find user
        user = await db.scalar(select(User).where(User.email == user_email))
        if not user:
            click.echo(f"❌ User '{user_email}' not found!")
            return
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get activity logs
        logs = await db.execute(
            select(AuditLog)
            .where(
                AuditLog.user_id == user.id,
                AuditLog.created_at >= since_date
            )
            .order_by(AuditLog.created_at.desc())
        )
        logs = logs.scalars().all()
        
        if not logs:
            click.echo(f"📭 No activity found for user '{user_email}' in the last {days} days.")
            return
        
        click.echo(f"\n📊 User Activity: {user_email} (Last {days} days)")
        click.echo("=" * 60)
        
        # Group by action
        action_counts = {}
        for log in logs:
            action_name = AuditAction(log.action).name if log.action else 'UNKNOWN'
            action_counts[action_name] = action_counts.get(action_name, 0) + 1
        
        click.echo("\n📈 Activity Summary:")
        for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"   {action}: {count}")
        
        # Recent activity
        click.echo(f"\n🕐 Recent Activity (Last 10):")
        for log in logs[:10]:
            action_name = AuditAction(log.action).name if log.action else 'UNKNOWN'
            click.echo(f"   {format_datetime(log.created_at)} - {action_name}: {log.operation_summary}")


@audit_group.command()
@click.option('--days', type=int, default=7, help='Number of days to analyze')
@async_command
async def api_performance(days: int):
    """Analyze API performance from audit logs."""
    async with AsyncSessionLocal() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get API call logs
        api_logs = await db.execute(
            select(AuditLog)
            .where(
                AuditLog.action == AuditAction.API_CALL,
                AuditLog.created_at >= since_date,
                AuditLog.execution_time_ms.isnot(None)
            )
        )
        api_logs = api_logs.scalars().all()
        
        if not api_logs:
            click.echo("📭 No API call logs found.")
            return
        
        click.echo(f"\n📊 API Performance Analysis (Last {days} days)")
        click.echo("=" * 60)
        
        # Calculate statistics
        total_calls = len(api_logs)
        total_time = sum(log.execution_time_ms for log in api_logs if log.execution_time_ms)
        avg_time = total_time / total_calls if total_calls > 0 else 0
        
        # Group by endpoint
        endpoint_stats = {}
        for log in api_logs:
            endpoint = f"{log.request_method} {log.request_path}"
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    'count': 0,
                    'total_time': 0,
                    'errors': 0
                }
            
            endpoint_stats[endpoint]['count'] += 1
            if log.execution_time_ms:
                endpoint_stats[endpoint]['total_time'] += log.execution_time_ms
            if log.response_status_code >= 400:
                endpoint_stats[endpoint]['errors'] += 1
        
        # Overall stats
        click.echo("\n📈 Overall Statistics:")
        click.echo(f"   Total API Calls: {total_calls:,}")
        click.echo(f"   Average Response Time: {avg_time:.2f}ms")
        
        # Slowest endpoints
        click.echo("\n🐌 Slowest Endpoints (by average time):")
        sorted_endpoints = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1]['total_time'] / x[1]['count'] if x[1]['count'] > 0 else 0,
            reverse=True
        )
        
        for endpoint, stats in sorted_endpoints[:10]:
            avg_endpoint_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            click.echo(f"   {endpoint}: {avg_endpoint_time:.2f}ms (calls: {stats['count']})")
        
        # Most called endpoints
        click.echo("\n🔥 Most Called Endpoints:")
        sorted_by_calls = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        for endpoint, stats in sorted_by_calls[:10]:
            error_rate = (stats['errors'] / stats['count'] * 100) if stats['count'] > 0 else 0
            click.echo(f"   {endpoint}: {stats['count']} calls (errors: {error_rate:.1f}%)")


@audit_group.command()
@click.option('--older-than', type=int, default=90, help='Delete logs older than X days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
@async_command
async def cleanup_logs(older_than: int, dry_run: bool):
    """Clean up old audit logs."""
    async with AsyncSessionLocal() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than)
        
        # Count logs to delete
        count = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.created_at < cutoff_date)
        )
        
        if count == 0:
            click.echo(f"✅ No audit logs older than {older_than} days found.")
            return
        
        click.echo(f"\n🧹 Found {count:,} audit logs older than {older_than} days.")
        
        if dry_run:
            click.echo("⚠️  DRY RUN: No logs will be deleted.")
            return
        
        if click.confirm(f"Delete {count:,} old audit logs?"):
            try:
                await db.execute(
                    select(AuditLog).where(AuditLog.created_at < cutoff_date).delete()
                )
                await db.commit()
                click.echo(f"✅ Deleted {count:,} old audit logs.")
            except Exception as e:
                click.echo(f"❌ Error during cleanup: {e}")


def display_audit_log(log: AuditLog, detailed: bool = False, show_all: bool = False):
    """Display audit log information."""
    # Basic info
    click.echo(f"🆔 ID: {log.id}")
    click.echo(f"⏰ Timestamp: {format_datetime(log.created_at)}")
    
    # User info
    if log.user:
        click.echo(f"👤 User: {log.user.email} (ID: {log.user_id})")
    elif log.user_email:
        click.echo(f"👤 User: {log.user_email}")
    else:
        click.echo(f"👤 User: System")
    
    # Action and resource
    action_name = AuditAction(log.action).name if log.action else 'UNKNOWN'
    resource_name = AuditResource(log.resource_type).name if log.resource_type else 'UNKNOWN'
    severity_name = AuditSeverity(log.severity).name if log.severity else 'INFO'
    
    click.echo(f"🎬 Action: {action_name}")
    click.echo(f"📦 Resource: {resource_name}")
    click.echo(f"⚠️  Severity: {severity_name}")
    click.echo(f"📝 Summary: {log.operation_summary}")
    
    if detailed:
        # Request info
        if log.ip_address:
            click.echo(f"🌐 IP Address: {log.ip_address}")
        if log.request_path:
            click.echo(f"🔗 Request: {log.request_method} {log.request_path}")
        if log.response_status_code:
            click.echo(f"📊 Response: {log.response_status_code}")
        if log.execution_time_ms:
            click.echo(f"⏱️  Execution Time: {log.execution_time_ms}ms")
        
        # Error info
        if log.error_message:
            click.echo(f"❌ Error: {log.error_message}")
    
    if show_all:
        # Additional details
        if log.operation_details:
            click.echo(f"\n📋 Operation Details:")
            for key, value in log.operation_details.items():
                click.echo(f"   {key}: {value}")
        
        if log.old_values:
            click.echo(f"\n📤 Old Values:")
            for key, value in log.old_values.items():
                click.echo(f"   {key}: {value}")
        
        if log.new_values:
            click.echo(f"\n📥 New Values:")
            for key, value in log.new_values.items():
                click.echo(f"   {key}: {value}")