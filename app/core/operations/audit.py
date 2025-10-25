"""Audit logging operations for consolidated audit system."""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date, timedelta
import json
import uuid

from app.models.audit import (
    AuditLog, AuditAction, AuditResource, AuditSeverity
)
from app.models.user import User


async def create_audit_log(
    db: AsyncSession,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    action: AuditAction = AuditAction.SYSTEM_ACTION,
    resource_type: AuditResource = AuditResource.SYSTEM,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    request_query: Optional[str] = None,
    request_body_size: Optional[int] = None,
    response_status_code: Optional[int] = None,
    response_size: Optional[int] = None,
    execution_time_ms: Optional[int] = None,
    database_queries: Optional[int] = None,
    database_time_ms: Optional[int] = None,
    operation_summary: str = "",
    operation_details: Optional[Dict[str, Any]] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    changed_fields: Optional[List[str]] = None,
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    request_started_at: Optional[datetime] = None,
    request_completed_at: Optional[datetime] = None
) -> Optional[AuditLog]:
    """Create a comprehensive audit log entry."""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            request_query=request_query,
            request_body_size=request_body_size,
            response_status_code=response_status_code,
            response_size=response_size,
            execution_time_ms=execution_time_ms,
            database_queries=database_queries,
            database_time_ms=database_time_ms,
            operation_summary=operation_summary,
            operation_details=operation_details,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            table_name=table_name,
            record_id=record_id,
            error_message=error_message,
            error_traceback=error_traceback,
            severity=severity,
            session_id=session_id,
            correlation_id=correlation_id,
            request_started_at=request_started_at,
            request_completed_at=request_completed_at
        )
        
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        
        return audit_log
        
    except SQLAlchemyError as e:
        await db.rollback()
        print(f"ERROR creating audit log: {e}")
        import traceback
        traceback.print_exc()
        return None


async def log_api_call(
    db: AsyncSession,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    ip_address: str = "",
    user_agent: Optional[str] = None,
    request_method: str = "",
    request_path: str = "",
    request_query: Optional[str] = None,
    request_body_size: Optional[int] = None,
    response_status_code: int = 200,
    response_size: Optional[int] = None,
    execution_time_ms: int = 0,
    database_queries: Optional[int] = None,
    database_time_ms: Optional[int] = None,
    operation_summary: str = "",
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    request_started_at: Optional[datetime] = None,
    request_completed_at: Optional[datetime] = None
) -> Optional[AuditLog]:
    """Log an API call with comprehensive details."""
    return await create_audit_log(
        db=db,
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        action=AuditAction.API_CALL,
        resource_type=AuditResource.API_ENDPOINT,
        resource_name=f"{request_method} {request_path}",
        ip_address=ip_address,
        user_agent=user_agent,
        request_method=request_method,
        request_path=request_path,
        request_query=request_query,
        request_body_size=request_body_size,
        response_status_code=response_status_code,
        response_size=response_size,
        execution_time_ms=execution_time_ms,
        database_queries=database_queries,
        database_time_ms=database_time_ms,
        operation_summary=operation_summary,
        error_message=error_message,
        error_traceback=error_traceback,
        session_id=session_id,
        correlation_id=correlation_id,
        request_started_at=request_started_at,
        request_completed_at=request_completed_at
    )


async def log_database_operation(
    db: AsyncSession,
    action: AuditAction,
    table_name: str,
    record_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    changed_fields: Optional[List[str]] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    operation_summary: str = "",
    operation_details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    execution_time_ms: Optional[int] = None
) -> Optional[AuditLog]:
    """Log a database operation with change details."""
    return await create_audit_log(
        db=db,
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        action=action,
        resource_type=AuditResource.DATABASE_TABLE,
        resource_id=record_id,
        resource_name=table_name,
        table_name=table_name,
        record_id=record_id,
        old_values=old_values,
        new_values=new_values,
        changed_fields=changed_fields,
        operation_summary=operation_summary,
        operation_details=operation_details,
        session_id=session_id,
        correlation_id=correlation_id,
        execution_time_ms=execution_time_ms
    )


async def log_user_action(
    db: AsyncSession,
    action: AuditAction,
    user_id: int,
    user_email: str,
    user_role: str,
    operation_summary: str = "",
    operation_details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Optional[AuditLog]:
    """Log a user action (login, logout, password change, etc.)."""
    return await create_audit_log(
        db=db,
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        action=action,
        resource_type=AuditResource.USER,
        resource_id=str(user_id),
        resource_name=user_email,
        ip_address=ip_address,
        user_agent=user_agent,
        request_method=request_method,
        request_path=request_path,
        operation_summary=operation_summary,
        operation_details=operation_details,
        severity=severity,
        session_id=session_id,
        correlation_id=correlation_id
    )


async def get_audit_logs(
    db: AsyncSession,
    user_id: Optional[int] = None,
    action: Optional[AuditAction] = None,
    resource_type: Optional[AuditResource] = None,
    severity: Optional[AuditSeverity] = None,
    table_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """Get audit logs with comprehensive filtering."""
    try:
        query = select(AuditLog).order_by(desc(AuditLog.created_at))
        
        # Apply filters
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if action:
            query = query.where(AuditLog.action == action)
        
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        
        if severity:
            query = query.where(AuditLog.severity == severity)
        
        if table_name:
            query = query.where(AuditLog.table_name == table_name)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
        
    except SQLAlchemyError:
        return []


async def get_api_call_logs(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status_code: Optional[int] = None,
    path: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """Get API call logs with filtering."""
    try:
        query = select(AuditLog).where(AuditLog.action == AuditAction.API_CALL).order_by(desc(AuditLog.created_at))
        
        # Apply filters
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if status_code:
            query = query.where(AuditLog.response_status_code == status_code)
        
        if path:
            query = query.where(AuditLog.request_path.ilike(f"%{path}%"))
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
        
    except SQLAlchemyError:
        return []


async def get_database_operation_logs(
    db: AsyncSession,
    table_name: Optional[str] = None,
    action: Optional[AuditAction] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """Get database operation logs with filtering."""
    try:
        # Filter for database operations
        db_actions = [AuditAction.CREATE, AuditAction.READ, AuditAction.UPDATE, AuditAction.DELETE]
        query = select(AuditLog).where(AuditLog.action.in_(db_actions)).order_by(desc(AuditLog.created_at))
        
        # Apply additional filters
        if table_name:
            query = query.where(AuditLog.table_name == table_name)
        
        if action:
            query = query.where(AuditLog.action == action)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
        
    except SQLAlchemyError:
        return []


async def get_audit_statistics(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """Get comprehensive audit statistics for reporting."""
    try:
        # Base query for date filtering
        date_filter = ""
        if start_date and end_date:
            date_filter = f"WHERE created_at >= '{start_date}' AND created_at <= '{end_date}'"
        elif start_date:
            date_filter = f"WHERE created_at >= '{start_date}'"
        elif end_date:
            date_filter = f"WHERE created_at <= '{end_date}'"
        
        # Action statistics
        action_stats_query = f"""
            SELECT 
                action,
                COUNT(*) as count
            FROM audit_logs
            {date_filter}
            GROUP BY action
        """
        
        # Resource type statistics
        resource_stats_query = f"""
            SELECT 
                resource_type,
                COUNT(*) as count
            FROM audit_logs
            {date_filter}
            GROUP BY resource_type
        """
        
        # API call statistics
        api_stats_query = f"""
            SELECT 
                response_status_code,
                COUNT(*) as count,
                AVG(execution_time_ms) as avg_execution_time,
                AVG(database_queries) as avg_database_queries
            FROM audit_logs
            WHERE action = {AuditAction.API_CALL}
            {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            GROUP BY response_status_code
        """
        
        # Database operation statistics
        db_stats_query = f"""
            SELECT 
                table_name,
                action,
                COUNT(*) as count
            FROM audit_logs
            WHERE action IN ({AuditAction.CREATE}, {AuditAction.UPDATE}, {AuditAction.DELETE})
            {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            GROUP BY table_name, action
        """
        
        # Execute queries
        action_result = await db.execute(action_stats_query)
        resource_result = await db.execute(resource_stats_query)
        api_result = await db.execute(api_stats_query)
        db_result = await db.execute(db_stats_query)
        
        return {
            "actions": dict(action_result.fetchall()),
            "resources": dict(resource_result.fetchall()),
            "api_calls": dict(api_result.fetchall()),
            "database_operations": dict(db_result.fetchall()),
            "period": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except SQLAlchemyError:
        return {}


async def cleanup_old_logs(
    db: AsyncSession,
    days_to_keep: int = 90
) -> int:
    """Clean up old audit logs to prevent database bloat."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count old logs
        result = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.created_at < cutoff_date)
        )
        old_log_count = result.scalar() or 0
        
        # Delete old logs
        await db.execute(
            AuditLog.__table__.delete().where(AuditLog.created_at < cutoff_date)
        )
        
        await db.commit()
        return old_log_count
        
    except SQLAlchemyError:
        await db.rollback()
        return 0
