"""Request validation middleware for size limits and content validation."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate request size and content."""
    
    def __init__(
        self, 
        app: ASGIApp,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB default
        max_upload_size: int = 50 * 1024 * 1024,   # 50MB for file uploads
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_upload_size = max_upload_size
    
    async def dispatch(self, request: Request, call_next):
        """Validate request size before processing."""
        # Get content length from headers
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                content_length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid content-length header"}
                )
            
            # Check if it's a file upload endpoint
            is_file_upload = (
                request.url.path.endswith("/upload") or
                request.url.path.endswith("/import") or
                request.url.path.endswith("/bulk-csv") or
                "multipart/form-data" in request.headers.get("content-type", "")
            )
            
            # Apply appropriate size limit
            max_size = self.max_upload_size if is_file_upload else self.max_request_size
            
            if content_length > max_size:
                max_size_mb = max_size / (1024 * 1024)
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": f"Request size exceeds maximum allowed size of {max_size_mb}MB"}
                )
        
        # Validate content-type for POST/PUT requests with body
        if request.method in ["POST", "PUT", "PATCH"] and content_length and content_length > 0:
            content_type = request.headers.get("content-type", "").lower()
            
            # Skip validation for certain paths (OAuth2PasswordRequestForm uses form-urlencoded)
            skip_paths = ["/csrf-token", "/health", "/metrics", "/api/v1/auth/login", "/api/v1/auth/logout"]
            if any(path in request.url.path for path in skip_paths):
                # Process the request
                response = await call_next(request)
                return response
            
            # List of allowed content types
            allowed_content_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/csv",
                "application/csv"
            ]
            
            # Check if content-type is present and valid
            if not content_type:
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"detail": "Content-Type header is required for requests with body"}
                )
            
            if not any(ct in content_type for ct in allowed_content_types):
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"detail": f"Unsupported content-type. Allowed types: {', '.join(allowed_content_types)}"}
                )
        
        # Process the request
        response = await call_next(request)
        return response