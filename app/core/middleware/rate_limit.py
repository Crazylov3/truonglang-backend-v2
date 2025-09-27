"""Rate limiting middleware using Redis."""

import time
import hashlib
import logging
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Dict, Optional
import asyncio
from app.database import redis_client
from app.cfg_manager import Cfg

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    def __init__(
        self, 
        app: ASGIApp,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
        burst_size: Optional[int] = None,
    ):
        super().__init__(app)
        
        # Get rate limit config
        rate_config = Cfg.rate_limit if hasattr(Cfg, 'rate_limit') else {}
        
        # Check if rate limiting is enabled
        self.enabled = rate_config.get('enabled', True)
        
        # Use config values or defaults
        self.requests_per_minute = requests_per_minute or rate_config.get('requests_per_minute', 60)
        self.requests_per_hour = requests_per_hour or rate_config.get('requests_per_hour', 1000)
        self.burst_size = burst_size or rate_config.get('burst_size', 10)
        
        # Build endpoint limits from config
        self.endpoint_limits = {}
        if 'endpoints' in rate_config:
            for endpoint_name, endpoint_config in rate_config['endpoints'].items():
                path = endpoint_config.get('path')
                if path:
                    self.endpoint_limits[path] = {
                        "per_minute": endpoint_config.get('per_minute', self.requests_per_minute),
                        "per_hour": endpoint_config.get('per_hour', self.requests_per_hour)
                    }
        
        # Reset rate limits on startup if configured (useful for development)
        if rate_config.get('reset_on_startup', False):
            asyncio.create_task(self._reset_all_rate_limits())
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limits before processing request."""
        # Skip if rate limiting is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for certain paths
        skip_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        if request.url.path == "/" or any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get client identifier (IP address or authenticated user ID)
        client_id = self._get_client_identifier(request)
        
        # Check rate limits
        allowed = await self._check_rate_limit(client_id, request.url.path)
        
        if not allowed:
            # Return a proper response instead of raising exception
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={
                    "Retry-After": "60",  # Suggest retry after 60 seconds
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        remaining = await self._get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Try to get authenticated user ID from request state
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Hash the IP for privacy
        return f"ip:{hashlib.sha256(client_ip.encode()).hexdigest()[:16]}"
    
    async def _check_rate_limit(self, client_id: str, path: str) -> bool:
        """Check if the client has exceeded rate limits."""
        # Get endpoint-specific limits if available
        limits = self._get_endpoint_limits(path)
        
        # Check per-minute limit
        minute_key = f"rate_limit:minute:{client_id}"
        minute_count = await self._increment_counter(minute_key, 60)
        
        if minute_count > limits["per_minute"]:
            return False
        
        # Check per-hour limit
        hour_key = f"rate_limit:hour:{client_id}"
        hour_count = await self._increment_counter(hour_key, 3600)
        
        if hour_count > limits["per_hour"]:
            return False
        
        # Check burst limit (using sliding window)
        burst_key = f"rate_limit:burst:{client_id}"
        burst_count = await self._check_burst_limit(burst_key, self.burst_size)
        
        if not burst_count:
            return False
        
        return True
    
    def _get_endpoint_limits(self, path: str) -> Dict[str, int]:
        """Get rate limits for specific endpoint."""
        # Check if path matches any specific endpoint limits
        for endpoint, limits in self.endpoint_limits.items():
            if path.startswith(endpoint):
                return {
                    "per_minute": limits["per_minute"],
                    "per_hour": limits["per_hour"]
                }
        
        # Return default limits
        return {
            "per_minute": self.requests_per_minute,
            "per_hour": self.requests_per_hour
        }
    
    async def _increment_counter(self, key: str, expire_seconds: int) -> int:
        """Increment a counter in Redis with expiration."""
        try:
            # Use pipeline for atomic operations
            async with redis_client.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, expire_seconds)
                results = await pipe.execute()
                return results[0]  # Return the incremented value
        except Exception as e:
            # If Redis fails, allow the request (fail open)
            return 0
    
    async def _check_burst_limit(self, key: str, limit: int) -> bool:
        """Check burst limit using sliding window."""
        try:
            current_time = int(time.time() * 1000)  # Milliseconds
            window_start = current_time - 10000  # 10 second window
            
            async with redis_client.pipeline() as pipe:
                # Remove old entries
                pipe.zremrangebyscore(key, 0, window_start)
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                # Count requests in window
                pipe.zcount(key, window_start, current_time)
                # Set expiration
                pipe.expire(key, 10)
                
                results = await pipe.execute()
                count = results[2]  # Get the count result
                
                return count <= limit
        except Exception:
            # If Redis fails, allow the request (fail open)
            return True
    
    async def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for the current minute."""
        try:
            minute_key = f"rate_limit:minute:{client_id}"
            count = await redis_client.get(minute_key)
            if count:
                return max(0, self.requests_per_minute - int(count))
            return self.requests_per_minute
        except Exception:
            return self.requests_per_minute
    
    async def _reset_all_rate_limits(self) -> None:
        """Reset all rate limit keys in Redis (useful for development)."""
        if not self.enabled:
            return
        
        try:
            # Find all rate limit keys
            pattern = "rate_limit:*"
            keys = []
            cursor = 0
            
            # Use scan to avoid blocking Redis on large datasets
            while True:
                cursor, batch_keys = await redis_client.scan(cursor, match=pattern, count=100)
                keys.extend(batch_keys)
                if cursor == 0:
                    break
            
            if keys:
                # Delete all rate limit keys
                await redis_client.delete(*keys)
                logger.info(f"Reset {len(keys)} rate limit keys on startup")
            else:
                logger.info("No rate limit keys to reset on startup")
        
        except Exception as e:
            logger.error(f"Failed to reset rate limits on startup: {e}")