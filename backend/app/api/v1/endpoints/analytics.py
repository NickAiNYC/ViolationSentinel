"""
Analytics endpoint
Dashboard metrics and violation analytics
"""

from typing import Any
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from ...db import get_db
from ...models import Property, Violation
from ...schemas import DashboardMetrics, ViolationStats

router = APIRouter()


def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", None)


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get dashboard metrics for tenant
    """
    tenant_id = get_tenant_id(request)
    
    # Count properties
    total_properties = db.query(func.count(Property.id)).filter(
        Property.tenant_id == tenant_id
    ).scalar()
    
    monitored_properties = db.query(func.count(Property.id)).filter(
        Property.tenant_id == tenant_id,
        Property.is_monitored == True
    ).scalar()
    
    # Count violations
    total_violations = db.query(func.count(Violation.id)).filter(
        Violation.tenant_id == tenant_id
    ).scalar()
    
    high_risk_count = db.query(func.count(Property.id.distinct())).join(
        Violation, Property.id == Violation.property_id
    ).filter(
        Property.tenant_id == tenant_id,
        Violation.risk_score >= 7.0
    ).scalar()
    
    # Average risk score
    avg_risk = db.query(func.avg(Violation.risk_score)).filter(
        Violation.tenant_id == tenant_id,
        Violation.is_resolved == False
    ).scalar() or 0.0
    
    return {
        "total_properties": total_properties or 0,
        "monitored_properties": monitored_properties or 0,
        "total_violations": total_violations or 0,
        "high_risk_properties": high_risk_count or 0,
        "violations_last_30_days": 0,  # TODO: Implement date filter
        "avg_risk_score": float(avg_risk)
    }


@router.get("/violations/stats", response_model=ViolationStats)
async def get_violation_stats(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get violation statistics
    """
    tenant_id = get_tenant_id(request)
    
    # TODO: Implement detailed stats with grouping
    
    total = db.query(func.count(Violation.id)).filter(
        Violation.tenant_id == tenant_id
    ).scalar() or 0
    
    resolved = db.query(func.count(Violation.id)).filter(
        Violation.tenant_id == tenant_id,
        Violation.is_resolved == True
    ).scalar() or 0
    
    high_risk = db.query(func.count(Violation.id)).filter(
        Violation.tenant_id == tenant_id,
        Violation.risk_score >= 7.0
    ).scalar() or 0
    
    return {
        "total": total,
        "by_class": {},
        "by_source": {},
        "resolved": resolved,
        "pending": total - resolved,
        "high_risk": high_risk
    }
