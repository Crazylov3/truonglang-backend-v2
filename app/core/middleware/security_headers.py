"""Security headers middleware for enhanced security."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app: ASGIApp, enable_hsts: bool = True, csp_policy: str = None):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.csp_policy = csp_policy or "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' data: https://cdn.jsdelivr.net;"
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to the response."""
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp_policy
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HTTP Strict Transport Security (only for HTTPS)
        if self.enable_hsts and request.url.scheme == "https":
            # max-age=31536000 (1 year), includeSubDomains
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response