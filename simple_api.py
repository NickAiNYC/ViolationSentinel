from fastapi import FastAPI, HTTPException, Header
import pandas as pd
from simple_monetization import monetization

app = FastAPI(title="ViolationSentinel API", description="NYC Property Risk Intelligence")

@app.get("/")
def home():
    return {
        "message": "ViolationSentinel API",
        "status": "live",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/properties")
def get_properties(
    bbl: str = None,
    borough: str = None,
    min_risk: float = None,
    max_risk: float = None,
    limit: int = 100,
    api_key: str = Header(..., alias="X-API-Key")
):
    """Get property data"""
    # Check access
    if not monetization.check_access(api_key):
        raise HTTPException(status_code=403, detail="Invalid or expired API key")
    
    # Track usage
    monetization.track_request(api_key)
    
    # Load data
    try:
        df = pd.read_csv("data/nyc_compliance_full_20260114_0336.csv")
    except:
        df = pd.read_csv("data/nyc_compliance_demo_20260114_0336.csv")
    
    # Apply filters
    if bbl:
        df = df[df['bbl'] == bbl]
    if borough:
        df = df[df['borough'] == borough.upper()]
    if min_risk is not None:
        df = df[df['risk_score'] >= min_risk]
    if max_risk is not None:
        df = df[df['risk_score'] <= max_risk]
    
    # Limit results
    df = df.head(limit)
    
    return {
        "count": len(df),
        "data": df.to_dict(orient="records")
    }

@app.get("/property/{bbl}")
def get_property(bbl: str, api_key: str = Header(..., alias="X-API-Key")):
    """Get detailed data for a specific property"""
    if not monetization.check_access(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    monetization.track_request(api_key)
    
    try:
        df = pd.read_csv("data/nyc_compliance_full_20260114_0336.csv")
    except:
        df = pd.read_csv("data/nyc_compliance_demo_20260114_0336.csv")
    
    property_data = df[df['bbl'] == bbl]
    
    if len(property_data) == 0:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return property_data.iloc[0].to_dict()

@app.get("/high-risk")
def get_high_risk(
    limit: int = 20,
    api_key: str = Header(..., alias="X-API-Key")
):
    """Get highest risk properties"""
    if not monetization.check_access(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    monetization.track_request(api_key)
    
    try:
        df = pd.read_csv("data/nyc_compliance_full_20260114_0336.csv")
    except:
        df = pd.read_csv("data/nyc_compliance_demo_20260114_0336.csv")
    
    df = df.sort_values('risk_score', ascending=False).head(limit)
    
    return {
        "count": len(df),
        "data": df.to_dict(orient="records")
    }

@app.get("/usage")
def get_usage(api_key: str = Header(..., alias="X-API-Key")):
    """Get current usage"""
    if api_key not in monetization.api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    email = monetization.api_keys[api_key]
    user = monetization.users.get(email, {})
    
    tier_limits = {
        "free": 10,
        "pro": 1000,
        "enterprise": 10000
    }
    
    return {
        "email": email,
        "tier": user.get("tier", "free"),
        "used": user.get("requests_used", 0),
        "limit": tier_limits.get(user.get("tier", "free"), 10),
        "remaining": tier_limits.get(user.get("tier", "free"), 10) - user.get("requests_used", 0)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
