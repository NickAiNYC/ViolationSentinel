"""
Property Endpoints
CRUD operations for properties
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_properties():
    """List properties"""
    return {"message": "Properties endpoint - implementation in progress"}


@router.get("/{property_id}")
async def get_property(property_id: str):
    """Get property by ID"""
    return {"message": f"Get property {property_id} - implementation in progress"}
