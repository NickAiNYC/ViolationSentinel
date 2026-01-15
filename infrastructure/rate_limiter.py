"""
Token Bucket Rate Limiter for ViolationSentinel API

Implements distributed rate limiting using Redis-backed token bucket algorithm
for protecting API endpoints from abuse and ensuring fair resource allocation.

The token bucket algorithm allows for:
- Steady-state rate limiting
- Burst traffic handling (up to bucket capacity)
- Per-user and per-endpoint limits
- Distributed rate limiting across multiple instances

Author: ViolationSentinel Team
"""

import asyncio
import time
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps

try:
    import redis.asyncio as aioredis
except ImportError:
    import aioredis

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int, limit: int, window: int):
        self.retry_after = retry_after
        self.limit = limit
        self.window = window
        super().__init__(
            f"Rate limit exceeded. {limit} requests per {window} seconds. "
            f"Retry after {retry_after} seconds."
        )


@dataclass
class RateLimitInfo:
    """Information about current rate limit status."""
    limit: int
    remaining: int
    reset_at: int
    retry_after: Optional[int] = None


class RateLimiter:
    """
    Async token bucket rate limiter with Redis backend.
    
    Features:
    - Token bucket algorithm for smooth rate limiting
    - Per-user and per-endpoint limits
    - Burst allowance support
    - Distributed rate limiting via Redis
    - Admin override capability
    - Rate limit headers generation
    
    Example:
        limiter = RateLimiter(redis_url="redis://localhost:6379")
        await limiter.acquire(user_id="user123", endpoint="/api/risk/calculate")
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_rate: int = 100,
        default_window: int = 60,
        admin_users: Optional[set] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL
            default_rate: Default requests per window (tokens)
            default_window: Default time window in seconds
            admin_users: Set of user IDs that bypass rate limits
        """
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.default_rate = default_rate
        self.default_window = default_window
        self.admin_users = admin_users or set()
        
        # Per-endpoint rate limits (can be customized)
        self.endpoint_limits: Dict[str, Tuple[int, int]] = {
            "/api/risk/calculate": (100, 60),      # 100 req/min
            "/api/risk/batch": (20, 60),           # 20 req/min
            "/api/violations/query": (200, 60),    # 200 req/min
            "/api/properties/search": (50, 60),    # 50 req/min
        }
        
        logger.info(f"RateLimiter initialized with default: {default_rate} req/{default_window}s")
    
    async def connect(self):
        """Establish Redis connection."""
        if self.redis is None:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis for rate limiting")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Closed Redis connection")
    
    def _get_key(self, user_id: str, endpoint: str) -> str:
        """Generate Redis key for rate limit tracking."""
        return f"ratelimit:{user_id}:{endpoint}"
    
    def _get_limit_for_endpoint(self, endpoint: str) -> Tuple[int, int]:
        """Get rate limit and window for specific endpoint."""
        # Match exact endpoint or use default
        if endpoint in self.endpoint_limits:
            return self.endpoint_limits[endpoint]
        
        # Check for pattern matches (e.g., /api/risk/*)
        for pattern, limits in self.endpoint_limits.items():
            if endpoint.startswith(pattern.rstrip("*")):
                return limits
        
        return (self.default_rate, self.default_window)
    
    async def acquire(
        self,
        user_id: str,
        endpoint: str,
        cost: int = 1
    ) -> RateLimitInfo:
        """
        Acquire tokens from the bucket (token bucket algorithm).
        
        Args:
            user_id: User identifier (API key, user_id, etc.)
            endpoint: API endpoint path
            cost: Number of tokens to consume (default: 1)
        
        Returns:
            RateLimitInfo with current limit status
        
        Raises:
            RateLimitExceeded: When rate limit is exceeded
        """
        # Admin users bypass rate limits
        if user_id in self.admin_users:
            logger.debug(f"Admin user {user_id} bypassing rate limit")
            limit, window = self._get_limit_for_endpoint(endpoint)
            return RateLimitInfo(
                limit=limit,
                remaining=limit,
                reset_at=int(time.time()) + window
            )
        
        await self.connect()
        
        limit, window = self._get_limit_for_endpoint(endpoint)
        key = self._get_key(user_id, endpoint)
        now = time.time()
        
        # Token bucket algorithm using Redis
        # Key format: {key}:tokens = remaining tokens
        # Key format: {key}:last_refill = last refill timestamp
        
        tokens_key = f"{key}:tokens"
        last_refill_key = f"{key}:last_refill"
        
        # Get current state
        pipe = self.redis.pipeline()
        pipe.get(tokens_key)
        pipe.get(last_refill_key)
        results = await pipe.execute()
        
        current_tokens = float(results[0]) if results[0] else float(limit)
        last_refill = float(results[1]) if results[1] else now
        
        # Refill tokens based on elapsed time (continuous refill)
        elapsed = now - last_refill
        refill_rate = limit / window  # tokens per second
        tokens_to_add = elapsed * refill_rate
        current_tokens = min(limit, current_tokens + tokens_to_add)
        
        # Check if we have enough tokens
        if current_tokens >= cost:
            # Consume tokens
            new_tokens = current_tokens - cost
            
            # Update Redis with new state
            pipe = self.redis.pipeline()
            pipe.set(tokens_key, new_tokens, ex=window * 2)
            pipe.set(last_refill_key, now, ex=window * 2)
            await pipe.execute()
            
            reset_at = int(now + (limit - new_tokens) / refill_rate)
            
            logger.debug(
                f"Rate limit acquired for {user_id} on {endpoint}: "
                f"{int(new_tokens)}/{limit} remaining"
            )
            
            return RateLimitInfo(
                limit=limit,
                remaining=int(new_tokens),
                reset_at=reset_at
            )
        else:
            # Rate limit exceeded
            # Calculate when enough tokens will be available
            tokens_needed = cost - current_tokens
            retry_after = int(tokens_needed / refill_rate) + 1
            reset_at = int(now + retry_after)
            
            logger.warning(
                f"Rate limit exceeded for {user_id} on {endpoint}: "
                f"need {cost}, have {int(current_tokens)}/{limit}"
            )
            
            raise RateLimitExceeded(
                retry_after=retry_after,
                limit=limit,
                window=window
            )
    
    async def check_limit(
        self,
        user_id: str,
        endpoint: str
    ) -> RateLimitInfo:
        """
        Check current rate limit status without consuming tokens.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint path
        
        Returns:
            RateLimitInfo with current status
        """
        # Admin users
        if user_id in self.admin_users:
            limit, window = self._get_limit_for_endpoint(endpoint)
            return RateLimitInfo(
                limit=limit,
                remaining=limit,
                reset_at=int(time.time()) + window
            )
        
        await self.connect()
        
        limit, window = self._get_limit_for_endpoint(endpoint)
        key = self._get_key(user_id, endpoint)
        now = time.time()
        
        tokens_key = f"{key}:tokens"
        last_refill_key = f"{key}:last_refill"
        
        pipe = self.redis.pipeline()
        pipe.get(tokens_key)
        pipe.get(last_refill_key)
        results = await pipe.execute()
        
        current_tokens = float(results[0]) if results[0] else float(limit)
        last_refill = float(results[1]) if results[1] else now
        
        # Calculate refilled tokens
        elapsed = now - last_refill
        refill_rate = limit / window
        tokens_to_add = elapsed * refill_rate
        current_tokens = min(limit, current_tokens + tokens_to_add)
        
        reset_at = int(now + (limit - current_tokens) / refill_rate)
        
        return RateLimitInfo(
            limit=limit,
            remaining=int(current_tokens),
            reset_at=reset_at
        )
    
    async def reset_limit(self, user_id: str, endpoint: str):
        """
        Manually reset rate limit for a user on an endpoint.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint path
        """
        await self.connect()
        
        key = self._get_key(user_id, endpoint)
        tokens_key = f"{key}:tokens"
        last_refill_key = f"{key}:last_refill"
        
        await self.redis.delete(tokens_key, last_refill_key)
        logger.info(f"Reset rate limit for {user_id} on {endpoint}")
    
    def get_headers(self, info: RateLimitInfo) -> Dict[str, str]:
        """
        Generate HTTP headers for rate limit information.
        
        Args:
            info: RateLimitInfo object
        
        Returns:
            Dictionary of headers
        """
        headers = {
            "X-RateLimit-Limit": str(info.limit),
            "X-RateLimit-Remaining": str(info.remaining),
            "X-RateLimit-Reset": str(info.reset_at),
        }
        
        if info.retry_after is not None:
            headers["Retry-After"] = str(info.retry_after)
        
        return headers
    
    def add_admin_user(self, user_id: str):
        """Add user to admin bypass list."""
        self.admin_users.add(user_id)
        logger.info(f"Added {user_id} to admin bypass list")
    
    def remove_admin_user(self, user_id: str):
        """Remove user from admin bypass list."""
        self.admin_users.discard(user_id)
        logger.info(f"Removed {user_id} from admin bypass list")
    
    async def get_metrics(self) -> Dict[str, int]:
        """
        Get rate limiting metrics.
        
        Returns:
            Dictionary with metrics
        """
        await self.connect()
        
        # Count total rate limit keys
        keys = await self.redis.keys("ratelimit:*:tokens")
        
        return {
            "active_limits": len(keys),
            "admin_users": len(self.admin_users),
            "configured_endpoints": len(self.endpoint_limits)
        }


def rate_limit(
    limiter: RateLimiter,
    get_user_id,
    get_endpoint=None,
    cost: int = 1
):
    """
    Decorator for FastAPI endpoints to apply rate limiting.
    
    Args:
        limiter: RateLimiter instance
        get_user_id: Callable to extract user_id from request
        get_endpoint: Callable to extract endpoint path (optional)
        cost: Token cost for this endpoint
    
    Example:
        @app.get("/api/risk/calculate")
        @rate_limit(limiter, lambda req: req.headers.get("X-API-Key"))
        async def calculate_risk(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):
                    request = arg
                    break
            
            if request is None:
                # If no request found, just call function
                return await func(*args, **kwargs)
            
            # Get user_id
            user_id = get_user_id(request)
            if not user_id:
                # No user_id, skip rate limiting
                return await func(*args, **kwargs)
            
            # Get endpoint
            if get_endpoint:
                endpoint = get_endpoint(request)
            else:
                endpoint = request.url.path
            
            # Check rate limit
            try:
                info = await limiter.acquire(user_id, endpoint, cost)
                
                # Add headers to response
                response = await func(*args, **kwargs)
                if hasattr(response, 'headers'):
                    response.headers.update(limiter.get_headers(info))
                
                return response
                
            except RateLimitExceeded as e:
                # Return 429 error
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": str(e),
                        "retry_after": e.retry_after,
                        "limit": e.limit,
                        "window": e.window
                    },
                    headers={"Retry-After": str(e.retry_after)}
                )
        
        return wrapper
    return decorator
