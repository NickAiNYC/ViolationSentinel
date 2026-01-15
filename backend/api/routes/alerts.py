"""
Alert Endpoints
Manage alerts and alert rules
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_alerts():
    """List alerts"""
    return {"message": "Alerts endpoint - implementation in progress"}
