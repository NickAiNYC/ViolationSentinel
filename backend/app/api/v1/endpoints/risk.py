"""
Risk Assessment Endpoint - HPD Risk Radar
MVP endpoint for BBL-based risk assessment

Returns fine exposure, risk score, violations, and fix priority.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()


class ViolationDetail(BaseModel):
    """Individual violation detail."""
    type: str
    severity: str
    fine: int


class RiskResponse(BaseModel):
    """Risk assessment response for a building."""
    bbl: str = Field(..., description="Borough-Block-Lot identifier")
    exposure: int = Field(..., description="Total fine exposure in dollars")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score from 0-1")
    violations: list[ViolationDetail] = Field(default_factory=list, description="List of violations")
    violation_count: int = Field(..., description="Total open violations")
    open_class_c: int = Field(0, description="Count of Class C violations")
    open_class_b: int = Field(0, description="Count of Class B violations")
    open_class_a: int = Field(0, description="Count of Class A violations")
    fix_priority: str = Field(..., description="Recommended fix priority")
    estimated_year_built: Optional[int] = Field(None, description="Estimated construction year")
    pre_1974_risk: bool = Field(False, description="Whether building is pre-1974")
    last_inspection: Optional[str] = Field(None, description="Last inspection date")
    next_inspection_risk: str = Field("Unknown", description="Next inspection risk level")


class PortfolioBuilding(BaseModel):
    """Building in a portfolio."""
    bbl: str
    address: Optional[str] = None
    units: int = 0
    year_built: Optional[int] = None
    risk_score: float = 0.0
    exposure: int = 0
    open_violations: int = 0
    class_c: int = 0
    class_b: int = 0
    class_a: int = 0


class PortfolioResponse(BaseModel):
    """Portfolio summary response."""
    user_id: str
    total_buildings: int
    total_units: int
    total_exposure: int
    total_violations: int
    total_class_c: int
    average_risk_score: float
    buildings: list[PortfolioBuilding]
    last_updated: datetime


def calculate_risk_data(bbl: str) -> dict:
    """
    Calculate risk data for a building based on BBL.
    
    In production, this would query HPD/DOB/311 APIs.
    For MVP, returns realistic mock data based on BBL patterns.
    """
    # BBL format: borough(1) + block(5) + lot(4) = 10 digits
    borough = bbl[0] if len(bbl) >= 1 else "1"
    
    # Generate realistic exposure based on borough
    borough_multipliers = {
        "1": 1.2,   # Manhattan - higher costs
        "2": 1.1,   # Bronx - high violation density
        "3": 1.0,   # Brooklyn - baseline
        "4": 0.9,   # Queens
        "5": 0.85   # Staten Island
    }
    
    base_exposure = 27450
    multiplier = borough_multipliers.get(borough, 1.0)
    exposure = int(base_exposure * multiplier)
    
    # Generate risk score (0.0 - 1.0)
    block_num = int(bbl[1:6]) if len(bbl) >= 6 else 5000
    risk_score = min(0.95, max(0.15, 0.5 + (10000 - block_num) / 20000))
    
    # Realistic violation types for NYC
    violations = [
        {"type": "Class C - Inadequate Heat", "severity": "immediately_hazardous", "fine": 5000},
        {"type": "Class B - Smoke Detector Missing", "severity": "hazardous", "fine": 2500},
        {"type": "Class A - Peeling Paint (Non-Lead)", "severity": "non_hazardous", "fine": 500},
    ]
    
    # Year built estimation
    estimated_year = 1960 if block_num < 3000 else (1975 if block_num < 7000 else 1995)
    
    return {
        "bbl": bbl,
        "exposure": exposure,
        "risk_score": round(risk_score, 2),
        "violations": violations,
        "violation_count": len(violations),
        "open_class_c": 1,
        "open_class_b": 1,
        "open_class_a": 1,
        "fix_priority": "Heat system inspection (Class C = $5k+ fine/violation)",
        "estimated_year_built": estimated_year,
        "pre_1974_risk": estimated_year < 1974,
        "last_inspection": "2024-11-15",
        "next_inspection_risk": "HIGH - Heat season active"
    }


@router.get("/{bbl}", response_model=RiskResponse)
async def get_risk(
    bbl: str,
) -> Any:
    """
    Get HPD risk assessment for a building.
    
    Args:
        bbl: 10-digit Borough-Block-Lot identifier
        
    Returns:
        Risk assessment including exposure, risk score, violations, and fix priority.
        
    Example:
        GET /api/v1/risk/3012340056
        
        Response:
        {
            "bbl": "3012340056",
            "exposure": 27450,
            "risk_score": 0.87,
            "violations": [...],
            "fix_priority": "Heat system inspection..."
        }
    """
    # Validate BBL format
    clean_bbl = bbl.strip().replace("-", "").replace(" ", "")
    
    if len(clean_bbl) != 10 or not clean_bbl.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid BBL format. Must be 10 digits (Borough + Block + Lot)."
        )
    
    # Validate borough (must be 1-5)
    borough = int(clean_bbl[0])
    if borough < 1 or borough > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid borough in BBL. Must be 1 (Manhattan), 2 (Bronx), 3 (Brooklyn), 4 (Queens), or 5 (Staten Island)."
        )
    
    risk_data = calculate_risk_data(clean_bbl)
    return risk_data


@router.get("/portfolio/{user_id}", response_model=PortfolioResponse)
async def get_portfolio_risk(
    user_id: str,
    include_details: bool = Query(True, description="Include individual building details"),
) -> Any:
    """
    Get portfolio-wide risk assessment for a user.
    
    Args:
        user_id: User identifier
        include_details: Whether to include individual building details
        
    Returns:
        Portfolio summary with aggregated risk metrics.
        
    Example:
        GET /api/v1/risk/portfolio/user123
        
        Response:
        {
            "user_id": "user123",
            "total_buildings": 4,
            "total_exposure": 68500,
            "average_risk_score": 0.58,
            "buildings": [...]
        }
    """
    # In production, this would query user's buildings from database
    # For MVP, return mock portfolio data
    
    mock_buildings = [
        {
            "bbl": "3012340056",
            "address": "123 Atlantic Ave, Brooklyn",
            "units": 24,
            "year_built": 1962,
            "risk_score": 0.87,
            "exposure": 34500,
            "open_violations": 5,
            "class_c": 2,
            "class_b": 2,
            "class_a": 1,
        },
        {
            "bbl": "3023450067",
            "address": "456 Court St, Brooklyn",
            "units": 18,
            "year_built": 1955,
            "risk_score": 0.72,
            "exposure": 22000,
            "open_violations": 3,
            "class_c": 1,
            "class_b": 1,
            "class_a": 1,
        },
        {
            "bbl": "3034560078",
            "address": "789 Smith St, Brooklyn",
            "units": 32,
            "year_built": 1978,
            "risk_score": 0.45,
            "exposure": 8500,
            "open_violations": 2,
            "class_c": 0,
            "class_b": 1,
            "class_a": 1,
        },
        {
            "bbl": "3045670089",
            "address": "321 Bergen St, Brooklyn",
            "units": 12,
            "year_built": 1985,
            "risk_score": 0.28,
            "exposure": 3500,
            "open_violations": 1,
            "class_c": 0,
            "class_b": 0,
            "class_a": 1,
        },
    ]
    
    total_buildings = len(mock_buildings)
    total_units = sum(b["units"] for b in mock_buildings)
    total_exposure = sum(b["exposure"] for b in mock_buildings)
    total_violations = sum(b["open_violations"] for b in mock_buildings)
    total_class_c = sum(b["class_c"] for b in mock_buildings)
    avg_risk = sum(b["risk_score"] for b in mock_buildings) / total_buildings if total_buildings > 0 else 0.0
    
    return {
        "user_id": user_id,
        "total_buildings": total_buildings,
        "total_units": total_units,
        "total_exposure": total_exposure,
        "total_violations": total_violations,
        "total_class_c": total_class_c,
        "average_risk_score": round(avg_risk, 2),
        "buildings": mock_buildings if include_details else [],
        "last_updated": datetime.utcnow(),
    }
