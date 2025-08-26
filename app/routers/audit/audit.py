"""Audit logging router for viewing and managing audit logs."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime

from app.core.deps import get_db, get_current_user, require_role
from app.core.operations.audit import (
    get_audit_logs, get_api_call_logs, get_database_operation_logs,
    get_audit_statistics, cleanup_old_logs
)
from app.models.user import User, UserRole
from app.schemas.audit import (
    AuditLogResponse, AuditLogFilter, AuditStatisticsResponse,
    AuditLogSummary, AuditExportRequest, AuditCleanupRequest, AuditCleanupResponse
)
from app.models.audit import AuditAction, AuditResource, AuditSeverity

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs_endpoint(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[int] = Query(None, description="Filter by action type"),
    resource_type: Optional[int] = Query(None, description="Filter by resource type"),
    severity: Optional[int] = Query(None, description="Filter by severity level"),
    table_name: Optional[str] = Query(None, description="Filter by database table"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    request_path: Optional[str] = Query(None, description="Filter by request path"),
    response_status_code: Optional[int] = Query(None, description="Filter by response status code"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with comprehensive filtering (Staff/Admin only)."""
    try:
        # Convert enum values if provided
        action_enum = AuditAction(action) if action else None
        resource_type_enum = AuditResource(resource_type) if resource_type else None
        severity_enum = AuditSeverity(severity) if severity else None
        
        logs = await get_audit_logs(
            db=db,
            user_id=user_id,
            action=action_enum,
            resource_type=resource_type_enum,
            severity=severity_enum,
            table_name=table_name,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return logs
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid enum value: {e}"
        )


@router.get("/logs/api-calls", response_model=List[AuditLogResponse])
async def get_api_call_logs_endpoint(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status_code: Optional[int] = Query(None, description="Filter by response status code"),
    path: Optional[str] = Query(None, description="Filter by request path"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get API call logs with filtering (Staff/Admin only)."""
    logs = await get_api_call_logs(
        db=db,
        user_id=user_id,
        status_code=status_code,
        path=path,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return logs


@router.get("/logs/database-operations", response_model=List[AuditLogResponse])
async def get_database_operation_logs_endpoint(
    table_name: Optional[str] = Query(None, description="Filter by database table"),
    action: Optional[int] = Query(None, description="Filter by operation type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get database operation logs with filtering (Staff/Admin only)."""
    try:
        action_enum = AuditAction(action) if action else None
        
        logs = await get_database_operation_logs(
            db=db,
            table_name=table_name,
            action=action_enum,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return logs
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid enum value: {e}"
        )


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics_endpoint(
    start_date: Optional[date] = Query(None, description="Start date for statistics"),
    end_date: Optional[date] = Query(None, description="End date for statistics"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive audit statistics (Staff/Admin only)."""
    stats = await get_audit_statistics(
        db=db,
        start_date=start_date,
        end_date=end_date
    )
    
    # Calculate totals
    total_logs = sum(stats.get("actions", {}).values())
    total_api_calls = sum(
        count for status_data in stats.get("api_calls", {}).values()
        if isinstance(status_data, dict) and "count" in status_data
        for count in [status_data["count"]]
    )
    total_database_operations = sum(
        sum(table_stats.values()) for table_stats in stats.get("database_operations", {}).values()
    )
    total_user_actions = sum(
        count for action, count in stats.get("actions", {}).items()
        if action in [AuditAction.LOGIN, AuditAction.LOGOUT, AuditAction.PASSWORD_CHANGE, AuditAction.ROLE_CHANGE]
    )
    
    return AuditStatisticsResponse(
        actions=stats.get("actions", {}),
        resources=stats.get("resources", {}),
        api_calls=stats.get("api_calls", {}),
        database_operations=stats.get("database_operations", {}),
        period=stats.get("period", {}),
        total_logs=total_logs,
        total_api_calls=total_api_calls,
        total_database_operations=total_database_operations,
        total_user_actions=total_user_actions
    )


@router.get("/summary", response_model=AuditLogSummary)
async def get_audit_summary_endpoint(
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get audit log summary overview (Staff/Admin only)."""
    # This would need to be implemented in attendance_ops
    # For now, returning mock data
    return AuditLogSummary(
        total_logs=0,
        logs_today=0,
        logs_this_week=0,
        logs_this_month=0,
        top_actions=[],
        top_resources=[],
        top_users=[],
        error_rate=0.0,
        avg_response_time=0.0
    )


@router.post("/cleanup", response_model=AuditCleanupResponse)
async def cleanup_audit_logs_endpoint(
    request: AuditCleanupRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Clean up old audit logs (Admin only)."""
    try:
        logs_deleted = await cleanup_old_logs(
            db=db,
            days_to_keep=request.days_to_keep
        )
        
        return AuditCleanupResponse(
            logs_to_delete=logs_deleted,
            logs_deleted=logs_deleted if not request.dry_run else 0,
            backup_created=request.backup_before_cleanup,
            backup_path=None,  # Would need backup implementation
            cleanup_time=datetime.utcnow(),
            dry_run=request.dry_run
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.get("/export")
async def export_audit_logs_endpoint(
    format: str = Query("csv", pattern="^(csv|json|excel)$", description="Export format"),
    start_date: Optional[date] = Query(None, description="Start date for export"),
    end_date: Optional[date] = Query(None, description="End date for export"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Export audit logs in various formats (Staff/Admin only)."""
    # This would need to be implemented with actual export logic
    # For now, returning a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Export functionality not yet implemented"
    )


@router.get("/my-activity", response_model=List[AuditLogResponse])
async def get_my_audit_activity(
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's audit activity (authenticated users only)."""
    logs = await get_audit_logs(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    return logs
