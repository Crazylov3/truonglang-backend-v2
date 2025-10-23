from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import IntEnum
from .base import BaseModel


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


class AuditLog(BaseModel):
    """Comprehensive audit log table for tracking all user operations, API calls, and database changes."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    
    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # NULL for unauthenticated actions
    user_email = Column(String(255), nullable=True)  # Store email for historical reference
    user_role = Column(Integer, nullable=True)  # Store role for historical reference
    
    # Action details
    action = Column(Integer, nullable=False)  # AuditAction enum
    resource_type = Column(Integer, nullable=False)  # AuditResource enum
    resource_id = Column(String(255), nullable=True)  # ID of the affected resource
    resource_name = Column(String(255), nullable=True)  # Human-readable resource name
    
    # Request details (for API calls)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(Text, nullable=True)  # Browser/Client information
    request_method = Column(String(10), nullable=True)  # HTTP method
    request_path = Column(String(500), nullable=True)  # API endpoint path
    request_query = Column(Text, nullable=True)  # Query parameters
    request_body_size = Column(Integer, nullable=True)  # Size in bytes
    
    # Response details (for API calls)
    response_status_code = Column(Integer, nullable=True)  # HTTP status code
    response_size = Column(Integer, nullable=True)  # Response size in bytes
    
    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)  # API execution time in milliseconds
    database_queries = Column(Integer, nullable=True)  # Number of DB queries executed
    database_time_ms = Column(Integer, nullable=True)  # Time spent in database operations
    
    # Operation details
    operation_summary = Column(Text, nullable=False)  # Human-readable summary
    operation_details = Column(JSON, nullable=True)  # Detailed operation data
    old_values = Column(JSON, nullable=True)  # Previous values (for updates)
    new_values = Column(JSON, nullable=True)  # New values (for updates)
    changed_fields = Column(JSON, nullable=True)  # List of changed field names
    
    # Database change details (for database operations)
    table_name = Column(String(255), nullable=True)  # Database table affected
    record_id = Column(String(255), nullable=True)  # Primary key of changed record
    
    # Error information
    error_message = Column(Text, nullable=True)  # Error message if operation failed
    error_traceback = Column(Text, nullable=True)  # Full error traceback
    
    # Metadata
    severity = Column(Integer, nullable=False, default=AuditSeverity.INFO)
    session_id = Column(String(255), nullable=True)  # Session identifier
    correlation_id = Column(String(255), nullable=True)  # For tracking related operations
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    request_started_at = Column(DateTime(timezone=True), nullable=True)  # When request started
    request_completed_at = Column(DateTime(timezone=True), nullable=True)  # When request completed
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, resource={self.resource_type})>"
    
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
