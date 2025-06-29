import secrets
import hashlib
import time
from typing import Optional
from fastapi import Request


class CSRFManager:
    """Simple CSRF protection using cookie vs header validation (Django style)."""
    
    def __init__(self, redis_client=None):
        # Redis not needed for Django-style CSRF
        self.redis_client = redis_client
    
    def generate_csrf_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        # Generate random token with timestamp for uniqueness
        random_bytes = secrets.token_bytes(32)
        timestamp = str(int(time.time())).encode()
        token_data = random_bytes + timestamp
        
        # Create hash for the token
        token_hash = hashlib.sha256(token_data).hexdigest()
        return token_hash
    
    def validate_csrf_token(self, request: Request) -> bool:
        """
        Validate CSRF token using Django's approach:
        Compare token in cookie with token in header/form.
        """
        # Get token from cookie
        cookie_token = request.cookies.get("csrftoken")
        if not cookie_token:
            return False
        
        # Get token from header (preferred) or form data
        header_token = request.headers.get("X-Csrftoken") or request.headers.get("X-CSRF-Token")
        
        if not header_token:
            # Try to get from form data
            try:
                if hasattr(request, '_form'):
                    form_data = request._form
                else:
                    # This is async, but we'll handle it in the decorator
                    return False
                header_token = form_data.get("csrftoken")
            except:
                return False
        
        if not header_token:
            return False
        
        # Simple comparison - if they match, it's valid
        return cookie_token == header_token
    
    async def validate_csrf_token_async(self, request: Request) -> bool:
        """
        Async version that can handle form data.
        """
        # Get token from cookie  
        cookie_token = request.cookies.get("csrftoken")
        if not cookie_token:
            return False
        
        # Get token from header (preferred)
        header_token = request.headers.get("X-Csrftoken") or request.headers.get("X-CSRF-Token")
        
        if not header_token:
            # Try to get from form data
            try:
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                    form_data = await request.form()
                    header_token = form_data.get("csrftoken")
            except:
                pass
        
        if not header_token:
            return False
        
        # Simple comparison - if they match, it's valid
        return cookie_token == header_token


# Legacy function for backward compatibility
def get_csrf_manager(redis_client=None) -> CSRFManager:
    """Get CSRF manager instance (Redis not needed anymore)."""
    return CSRFManager(redis_client) 