"""
Violations endpoint
Query and manage violation data
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime

from ...db import get_db
from ...models import Violation, Property
from ...schemas import ViolationResponse, ScanRequest, ScanResponse

router = APIRouter()


def get_tenant_id(request: Request) -> str:
    """Extract tenant ID from request state"""
    return getattr(request.state, "tenant_id", None)


@router.get("/", response_model=List[ViolationResponse])
async def list_violations(
    request: Request,
    property_id: Optional[str] = None,
    source: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """
    List violations with filters
    """
    tenant_id = get_tenant_id(request)
    
    query = db.query(Violation).filter(Violation.tenant_id == tenant_id)
    
    if property_id:
        query = query.filter(Violation.property_id == property_id)
    
    if source:
        query = query.filter(Violation.source == source)
    
    if is_resolved is not None:
        query = query.filter(Violation.is_resolved == is_resolved)
    
    violations = query.order_by(Violation.issued_date.desc()).offset(skip).limit(limit).all()
    
    return violations


@router.get("/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get violation by ID
    """
    tenant_id = get_tenant_id(request)
    
    violation = db.query(Violation).filter(
        Violation.id == violation_id,
        Violation.tenant_id == tenant_id
    ).first()
    
    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Violation not found"
        )
    
    return violation


@router.post("/scan", response_model=ScanResponse)
async def scan_violations(
    scan_request: ScanRequest,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Trigger violation scan for properties
    This is typically queued as a background task
    """
    import uuid
    tenant_id = get_tenant_id(request)
    
    # Get properties to scan
    if scan_request.scan_all:
        properties = db.query(Property).filter(
            Property.tenant_id == tenant_id,
            Property.is_monitored == True
        ).all()
    else:
        properties = db.query(Property).filter(
            Property.tenant_id == tenant_id,
            Property.id.in_(scan_request.property_ids or [])
        ).all()
    
    if not properties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No properties to scan"
        )
    
    # TODO: Queue scan task with Celery
    scan_id = str(uuid.uuid4())
    
    return {
        "scan_id": scan_id,
        "status": "queued",
        "properties_scanned": len(properties),
        "violations_found": 0,  # Will be updated by background task
        "started_at": datetime.utcnow()
    }
