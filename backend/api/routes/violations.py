"""
Violation Endpoints
Query and manage violations
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_violations():
    """List violations"""
    return {"message": "Violations endpoint - implementation in progress"}
