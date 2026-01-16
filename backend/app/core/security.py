"""
Core security utilities
JWT, OAuth2, RBAC, encryption
"""

from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access",
        "tenant:manage": "Manage tenant",
        "users:manage": "Manage users",
        "reports:generate": "Generate reports",
        "integrations:manage": "Manage integrations",
    }
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    scopes: List[str] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "scopes": scopes or []
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class SecurityMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if settings.SECURITY_HEADERS_ENABLED:
            # OWASP recommended security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline';"
            )
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = (
                "geolocation=(), microphone=(), camera=()"
            )
        
        return response


def check_permissions(required_scopes: List[str], user_scopes: List[str]) -> bool:
    """Check if user has required permissions"""
    if "admin" in user_scopes:
        return True
    
    for scope in required_scopes:
        if scope not in user_scopes:
            return False
    
    return True


class RBACManager:
    """Role-Based Access Control Manager"""
    
    ROLES = {
        "admin": ["read", "write", "admin", "tenant:manage", "users:manage", 
                  "reports:generate", "integrations:manage"],
        "manager": ["read", "write", "reports:generate", "integrations:manage"],
        "analyst": ["read", "reports:generate"],
        "viewer": ["read"],
    }
    
    @classmethod
    def get_role_scopes(cls, role: str) -> List[str]:
        """Get scopes for a given role"""
        return cls.ROLES.get(role, [])
    
    @classmethod
    def validate_role(cls, role: str) -> bool:
        """Check if role exists"""
        return role in cls.ROLES
