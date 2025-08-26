"""Audit middleware for automatic logging of API calls and operations."""

import time
import json
import traceback
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uuid

from app.core.operations.audit import log_api_call, log_user_action
from app.models.audit import AuditAction, AuditSeverity
from app.models.user import UserRole


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of all API calls."""
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs", "/redoc", "/openapi.json", "/favicon.ico",
            "/health", "/metrics"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and log audit information."""
        start_time = time.time()
        
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate correlation ID for tracking related operations
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Get user information if available
        user_id = None
        user_email = None
        user_role = None
        
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, 'user'):
            user = request.state.user
            user_id = user.id
            user_email = user.email
            user_role = user.role
        
        # Get request details
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        request_method = request.method
        request_path = str(request.url.path)
        request_query = str(request.url.query) if request.url.query else None
        
        # Calculate request body size
        request_body_size = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_body_size = len(body)
            except:
                pass
        
        # Set request start time
        request_started_at = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Get response details
            response_status_code = response.status_code
            response_size = self._get_response_size(response)
            
            # Log successful API call
            await self._log_api_call(
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                request_query=request_query,
                request_body_size=request_body_size,
                response_status_code=response_status_code,
                response_size=response_size,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                request_started_at=request_started_at,
                request_completed_at=time.time(),
                error_message=None,
                error_traceback=None
            )
            
            return response
            
        except Exception as e:
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log failed API call
            await self._log_api_call(
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                request_query=request_query,
                request_body_size=request_body_size,
                response_status_code=500,
                response_size=None,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                request_started_at=request_started_at,
                request_completed_at=time.time(),
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
            
            # Re-raise the exception
            raise
    
    async def _log_api_call(self, **kwargs):
        """Log an API call to the audit system."""
        try:
            # Get database session from request state if available
            db = getattr(kwargs.get('request', {}), 'state', {}).get('db')
            if db:
                await log_api_call(db=db, **kwargs)
        except Exception as e:
            # Don't let audit logging failures break the main request
            print(f"Audit logging failed: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (for proxy/load balancer scenarios)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def _get_response_size(self, response: Response) -> Optional[int]:
        """Calculate response size in bytes."""
        try:
            if hasattr(response, 'body'):
                return len(response.body)
            elif hasattr(response, 'content'):
                return len(response.content)
            return None
        except:
            return None


class DatabaseAuditMiddleware:
    """Context manager for logging database operations."""
    
    def __init__(self, db, user_id: Optional[int] = None, user_email: Optional[str] = None, user_role: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.user_email = user_email
        self.user_role = user_role
        self.operations = []
    
    async def log_operation(
        self,
        action: AuditAction,
        table_name: str,
        record_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[List[str]] = None,
        operation_summary: str = "",
        operation_details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        """Log a database operation."""
        try:
            from app.core.operations.audit import log_database_operation
            
            await log_database_operation(
                db=self.db,
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                user_id=self.user_id,
                user_email=self.user_email,
                user_role=self.user_role,
                operation_summary=operation_summary,
                operation_details=operation_details,
                correlation_id=correlation_id
            )
        except Exception as e:
            # Don't let audit logging failures break the main operation
            print(f"Database audit logging failed: {e}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Utility functions for easy audit logging
async def audit_user_action(
    db,
    action: AuditAction,
    user_id: int,
    user_email: str,
    user_role: int,
    operation_summary: str = "",
    operation_details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """Log a user action (login, logout, password change, etc.)."""
    try:
        from app.core.operations.audit import log_user_action
        
        await log_user_action(
            db=db,
            action=action,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            operation_summary=operation_summary,
            operation_details=operation_details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            severity=severity,
            session_id=session_id,
            correlation_id=correlation_id
        )
    except Exception as e:
        # Don't let audit logging failures break the main operation
        print(f"User action audit logging failed: {e}")


async def audit_database_operation(
    db,
    action: AuditAction,
    table_name: str,
    record_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    changed_fields: Optional[List[str]] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_role: Optional[int] = None,
    operation_summary: str = "",
    operation_details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    execution_time_ms: Optional[int] = None
):
    """Log a database operation."""
    try:
        from app.core.operations.audit import log_database_operation
        
        await log_database_operation(
            db=db,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            operation_summary=operation_summary,
            operation_details=operation_details,
            session_id=session_id,
            correlation_id=correlation_id,
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        # Don't let audit logging failures break the main operation
        print(f"Database operation audit logging failed: {e}")
