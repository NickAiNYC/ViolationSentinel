"""
Rate limiting middleware
Redis-backed distributed rate limiting
"""

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import redis
import time
import hashlib

from ..core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiting using Redis
    Implements sliding window algorithm
    """
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            self.redis_available = True
        except:
            self.redis_available = False
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        if not self.redis_available:
            # Fall back to no rate limiting if Redis is unavailable
            return await call_next(request)
        
        # Get client identifier (IP or API key)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return hashlib.sha256(api_key.encode()).hexdigest()
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host
        
        return f"ip:{client_ip}"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit"""
        key = f"ratelimit:{client_id}"
        current_time = time.time()
        
        try:
            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(
                key,
                0,
                current_time - self.window_size
            )
            
            # Count requests in current window
            request_count = self.redis_client.zcard(key)
            
            if request_count >= self.requests_per_minute:
                return False
            
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            
            # Set expiry on the key
            self.redis_client.expire(key, self.window_size)
            
            return True
        except:
            # If Redis fails, allow the request
            return True
    
    def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client"""
        key = f"ratelimit:{client_id}"
        current_time = time.time()
        
        try:
            # Remove old entries
            self.redis_client.zremrangebyscore(
                key,
                0,
                current_time - self.window_size
            )
            
            request_count = self.redis_client.zcard(key)
            return max(0, self.requests_per_minute - request_count)
        except:
            return self.requests_per_minute
