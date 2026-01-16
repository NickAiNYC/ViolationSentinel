"""
API v1 Router
"""

from fastapi import APIRouter

from .endpoints import (
    auth, properties, violations, reports, webhooks, analytics, admin
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(properties.router, prefix="/properties", tags=["Properties"])
api_router.include_router(violations.router, prefix="/violations", tags=["Violations"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
