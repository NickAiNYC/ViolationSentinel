"""
User Endpoints
User management and authentication
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_users():
    """List users"""
    return {"message": "Users endpoint - implementation in progress"}
