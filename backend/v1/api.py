"""
FastAPI V1 - Simple API for ViolationSentinel
"""

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os

from backend.v1.risk_engine import risk_engine

app = FastAPI(
    title="ViolationSentinel API V1",
    description="NYC Property Compliance Risk Intelligence API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory user database (in production, use Supabase)
users_db = {
    "test_free": {"tier": "free", "buildings_limit": 3, "api_key": "sk_test_free_123"},
    "test_pro": {"tier": "pro", "buildings_limit": 999999, "api_key": "sk_test_pro_456"}
}

# Models
class PropertyRiskRequest(BaseModel):
    bbl: str
    class_c_count: int = 0
    heat_complaints_7d: int = 0
    open_violations_90d: int = 0
    complaint_311_spike: int = 0

class PropertyRiskResponse(BaseModel):
    bbl: str
    risk_score: int
    priority: str
    fine_risk_estimate: str
    status_color: str
    breakdown: dict
    recommendations: list
    calculated_at: str

# Helper functions
def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate API key and return user info"""
    for email, user in users_db.items():
        if user["api_key"] == api_key:
            return {"email": email, **user}
    return None

# Routes
@app.get("/")
def home():
    """API home"""
    return {
        "message": "ViolationSentinel API V1",
        "status": "live",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "timestamp": "2026-01-15T18:00:00Z"}

@app.post("/risk/calculate", response_model=PropertyRiskResponse)
def calculate_risk(
    request: PropertyRiskRequest,
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    Calculate risk score for a property
    
    Scoring:
    - Class C violations: 40 pts each
    - Heat complaints (7d): 30 pts each  
    - Open violations >90d: 20 pts each
    - 311 spike: 10 pts
    """
    # Validate API key
    user = validate_api_key(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Calculate risk
    result = risk_engine.calculate_risk(
        class_c_count=request.class_c_count,
        heat_complaints_7d=request.heat_complaints_7d,
        open_violations_90d=request.open_violations_90d,
        complaint_311_spike=request.complaint_311_spike
    )
    
    # Get recommendations
    recommendations = risk_engine.get_recommendations(
        class_c_count=request.class_c_count,
        heat_complaints_7d=request.heat_complaints_7d,
        open_violations_90d=request.open_violations_90d
    )
    
    # Get status color
    status_color = risk_engine.get_status_color(result['risk_score'])
    
    return PropertyRiskResponse(
        bbl=request.bbl,
        risk_score=result['risk_score'],
        priority=result['priority'],
        fine_risk_estimate=result['fine_risk_estimate'],
        status_color=status_color,
        breakdown=result['breakdown'],
        recommendations=recommendations,
        calculated_at=result['calculated_at']
    )

@app.post("/risk/batch")
def calculate_batch_risk(
    properties: List[PropertyRiskRequest],
    api_key: str = Header(..., alias="X-API-Key")
):
    """Calculate risk for multiple properties"""
    user = validate_api_key(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Check tier limits
    if len(properties) > user['buildings_limit']:
        raise HTTPException(
            status_code=403,
            detail=f"Building limit exceeded. Your {user['tier']} plan allows {user['buildings_limit']} buildings."
        )
    
    results = []
    for prop in properties:
        result = risk_engine.calculate_risk(
            class_c_count=prop.class_c_count,
            heat_complaints_7d=prop.heat_complaints_7d,
            open_violations_90d=prop.open_violations_90d,
            complaint_311_spike=prop.complaint_311_spike
        )
        
        results.append({
            "bbl": prop.bbl,
            **result,
            "status_color": risk_engine.get_status_color(result['risk_score'])
        })
    
    return {
        "count": len(results),
        "results": results
    }

@app.get("/account/info")
def get_account_info(api_key: str = Header(..., alias="X-API-Key")):
    """Get account information"""
    user = validate_api_key(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return {
        "email": user['email'],
        "tier": user['tier'],
        "buildings_limit": user['buildings_limit']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
