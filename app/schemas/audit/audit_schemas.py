"""Audit logging schemas."""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import IntEnum
from uuid import UUID
from app.schemas.common import BaseUUIDModel


class AuditAction(IntEnum):
    """Types of actions that can be audited."""
    CREATE = 1
    READ = 2
    UPDATE = 3
    DELETE = 4
    LOGIN = 5
    LOGOUT = 6
    PASSWORD_CHANGE = 7
    ROLE_CHANGE = 8
    BULK_OPERATION = 9
    IMPORT = 10
    EXPORT = 11
    SYSTEM_ACTION = 12
    API_CALL = 13
    DATABASE_QUERY = 14


class AuditResource(IntEnum):
    """Types of resources being audited."""
    USER = 1
    COURSE = 2
    ENROLLMENT = 3
    PAYMENT = 4
    ATTENDANCE_CARD = 5
    ATTENDANCE_RECORD = 6
    CARD_ASSIGNMENT = 7
    INVOICE = 8
    SYSTEM = 9
    AUTH = 10
    API_ENDPOINT = 11
    DATABASE_TABLE = 12


class AuditSeverity(IntEnum):
    """Severity levels for audit events."""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    SECURITY = 5


class AuditLogResponse(BaseUUIDModel):
    """Response model for audit log entries."""
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    action: int  # AuditAction enum value
    resource_type: int  # AuditResource enum value
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    # Request details
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    request_query: Optional[str] = None
    request_body_size: Optional[int] = None
    
    # Response details
    response_status_code: Optional[int] = None
    response_size: Optional[int] = None
    
    # Performance metrics
    execution_time_ms: Optional[int] = None
    database_queries: Optional[int] = None
    database_time_ms: Optional[int] = None
    
    # Operation details
    operation_summary: str
    operation_details: Optional[Dict[str, Any]] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None
    
    # Database change details
    table_name: Optional[str] = None
    record_id: Optional[str] = None
    
    # Error information
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Metadata
    severity: int  # AuditSeverity enum value
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    request_started_at: Optional[datetime] = None
    request_completed_at: Optional[datetime] = None
    
    # Computed properties
    @property
    def is_api_call(self) -> bool:
        """Check if this log entry represents an API call."""
        return self.action == AuditAction.API_CALL or (
            self.request_method is not None and 
            self.request_path is not None
        )
    
    @property
    def is_database_operation(self) -> bool:
        """Check if this log entry represents a database operation."""
        return self.action in [AuditAction.CREATE, AuditAction.READ, AuditAction.UPDATE, AuditAction.DELETE] or (
            self.table_name is not None
        )
    
    @property
    def is_user_action(self) -> bool:
        """Check if this log entry represents a user action."""
        return self.action in [AuditAction.LOGIN, AuditAction.LOGOUT, AuditAction.PASSWORD_CHANGE, AuditAction.ROLE_CHANGE]
    
    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    """Filter model for querying audit logs."""
    user_id: Optional[UUID] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[AuditResource] = None
    severity: Optional[AuditSeverity] = None
    table_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    ip_address: Optional[str] = None
    request_path: Optional[str] = None
    response_status_code: Optional[int] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditStatisticsResponse(BaseModel):
    """Response model for audit statistics."""
    actions: Dict[str, int]  # action -> count
    resources: Dict[str, int]  # resource_type -> count
    api_calls: Dict[str, Dict[str, Any]]  # status_code -> {count, avg_execution_time, avg_database_queries}
    database_operations: Dict[str, Dict[str, int]]  # table_name -> {action -> count}
    period: Dict[str, Optional[date]]  # start_date, end_date
    total_logs: int
    total_api_calls: int
    total_database_operations: int
    total_user_actions: int


class AuditLogSummary(BaseModel):
    """Summary model for audit log overview."""
    total_logs: int
    logs_today: int
    logs_this_week: int
    logs_this_month: int
    top_actions: List[Dict[str, Any]]  # Top 5 actions by count
    top_resources: List[Dict[str, Any]]  # Top 5 resources by count
    top_users: List[Dict[str, Any]]  # Top 5 users by activity
    error_rate: float  # Percentage of errors
    avg_response_time: float  # Average API response time in ms


class AuditExportRequest(BaseModel):
    """Request model for exporting audit logs."""
    format: str = Field(default="csv", pattern="^(csv|json|excel)$")
    filters: AuditLogFilter
    include_details: bool = Field(default=True, description="Include full operation details")
    include_sensitive: bool = Field(default=False, description="Include potentially sensitive data")


class AuditCleanupRequest(BaseModel):
    """Request model for cleaning up old audit logs."""
    days_to_keep: int = Field(default=90, ge=30, le=365, description="Number of days to keep logs")
    dry_run: bool = Field(default=True, description="Show what would be deleted without actually deleting")
    backup_before_cleanup: bool = Field(default=True, description="Create backup before cleanup")


class AuditCleanupResponse(BaseModel):
    """Response model for audit cleanup operation."""
    logs_to_delete: int
    logs_deleted: int
    backup_created: bool
    backup_path: Optional[str] = None
    cleanup_time: datetime
    dry_run: bool
