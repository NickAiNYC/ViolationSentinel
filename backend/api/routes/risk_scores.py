"""
Risk Score Endpoints
Query risk scores and forecasts
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_risk_scores():
    """List risk scores"""
    return {"message": "Risk scores endpoint - implementation in progress"}
