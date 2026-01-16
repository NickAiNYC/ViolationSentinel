"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator


# Tenant Schemas
class TenantBase(BaseModel):
    name: str
    slug: str


class TenantCreate(TenantBase):
    plan: str = "free"


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    id: str
    plan: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: str = "viewer"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    role: str
    is_active: bool
    is_verified: bool
    tenant_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[str] = None
    scopes: List[str] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Property Schemas
class PropertyBase(BaseModel):
    name: str
    bbl: str = Field(..., min_length=10, max_length=10)
    address: Optional[str] = None
    year_built: Optional[int] = None
    units: Optional[int] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    year_built: Optional[int] = None
    units: Optional[int] = None
    is_monitored: Optional[bool] = None


class PropertyResponse(PropertyBase):
    id: str
    is_monitored: bool
    tenant_id: str
    created_at: datetime
    violation_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


# Violation Schemas
class ViolationBase(BaseModel):
    source: str
    description: Optional[str] = None
    violation_class: Optional[str] = None


class ViolationResponse(ViolationBase):
    id: str
    property_id: str
    external_id: str
    issued_date: Optional[datetime] = None
    resolved_date: Optional[datetime] = None
    is_resolved: bool
    risk_score: float
    confidence_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# Compliance Report Schemas
class ComplianceReportRequest(BaseModel):
    property_ids: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_resolved: bool = False
    format: str = "json"  # json, pdf, excel


class ComplianceReportResponse(BaseModel):
    report_id: str
    status: str
    download_url: Optional[str] = None
    generated_at: datetime


# Scan Request Schema
class ScanRequest(BaseModel):
    property_ids: Optional[List[str]] = None
    scan_all: bool = False
    sources: List[str] = ["DOB", "HPD", "311"]


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    properties_scanned: int
    violations_found: int
    started_at: datetime


# Webhook Configuration
class WebhookCreate(BaseModel):
    url: str
    events: List[str]
    is_active: bool = True


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Analytics Schemas
class ViolationStats(BaseModel):
    total: int
    by_class: dict
    by_source: dict
    resolved: int
    pending: int
    high_risk: int


class PropertyRiskScore(BaseModel):
    property_id: str
    property_name: str
    risk_score: float
    violation_count: int
    last_violation: Optional[datetime] = None


class DashboardMetrics(BaseModel):
    total_properties: int
    monitored_properties: int
    total_violations: int
    high_risk_properties: int
    violations_last_30_days: int
    avg_risk_score: float
