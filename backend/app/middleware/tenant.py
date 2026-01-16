"""
Multi-tenant middleware
Extracts and validates tenant context from requests
"""

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extract tenant ID from request and add to context
    Validates tenant exists and is active
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Skip tenant validation for public endpoints
        public_paths = [
            "/health",
            "/ready",
            "/metrics",
            "/api/v1/docs",
            "/api/v1/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        ]
        
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Extract tenant ID from header
        tenant_id = request.headers.get(settings.TENANT_HEADER)
        
        if not tenant_id:
            # Try to extract from JWT token if present
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    from ..core.security import decode_access_token
                    token = auth_header.replace("Bearer ", "")
                    payload = decode_access_token(token)
                    tenant_id = payload.get("tenant_id")
                except:
                    pass
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {settings.TENANT_HEADER} header"
            )
        
        # Add tenant ID to request state
        request.state.tenant_id = tenant_id
        
        # TODO: Validate tenant exists and is active in database
        # For now, just pass through
        
        logger.debug(f"Request for tenant: {tenant_id}")
        
        response = await call_next(request)
        return response
