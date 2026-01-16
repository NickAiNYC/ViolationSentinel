"""
Properties endpoint
CRUD operations for property management
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import uuid

from ...db import get_db
from ...models import Property
from ...schemas import PropertyCreate, PropertyUpdate, PropertyResponse

router = APIRouter()


def get_tenant_id(request: Request) -> str:
    """Extract tenant ID from request state"""
    return getattr(request.state, "tenant_id", None)


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_in: PropertyCreate,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create new property
    """
    tenant_id = get_tenant_id(request)
    
    # Check if property already exists for this tenant
    existing = db.query(Property).filter(
        Property.tenant_id == tenant_id,
        Property.bbl == property_in.bbl
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property with this BBL already exists"
        )
    
    property_obj = Property(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        **property_in.model_dump()
    )
    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)
    
    return property_obj


@router.get("/", response_model=List[PropertyResponse])
async def list_properties(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """
    List all properties for tenant
    """
    tenant_id = get_tenant_id(request)
    
    properties = db.query(Property).filter(
        Property.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()
    
    return properties


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get property by ID
    """
    tenant_id = get_tenant_id(request)
    
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.tenant_id == tenant_id
    ).first()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    return property_obj


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: str,
    property_in: PropertyUpdate,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Update property
    """
    tenant_id = get_tenant_id(request)
    
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.tenant_id == tenant_id
    ).first()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    # Update fields
    update_data = property_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property_obj, field, value)
    
    db.commit()
    db.refresh(property_obj)
    
    return property_obj


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete property
    """
    tenant_id = get_tenant_id(request)
    
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.tenant_id == tenant_id
    ).first()
    
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    db.delete(property_obj)
    db.commit()
    
    return None
