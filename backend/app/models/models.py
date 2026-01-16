"""
Database models
Multi-tenant aware with audit trails
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Float, Text,
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from ..db.session import Base


class TenantMixin:
    """Mixin for multi-tenant models"""
    tenant_id = Column(String(36), nullable=False, index=True)


class TimestampMixin:
    """Mixin for timestamp tracking"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Tenant(Base, TimestampMixin):
    """Tenant/Organization model"""
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Subscription
    plan = Column(String(50), default="free")  # free, pro, enterprise
    is_active = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime, nullable=True)
    
    # Limits
    api_calls_limit = Column(Integer, default=1000)
    users_limit = Column(Integer, default=5)
    properties_limit = Column(Integer, default=100)
    
    # Settings
    settings_json = Column(JSON, default={})
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    properties = relationship("Property", back_populates="tenant")
    
    __table_args__ = (
        Index("ix_tenants_active", "is_active"),
    )


class User(Base, TenantMixin, TimestampMixin):
    """User model with RBAC"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # RBAC
    role = Column(String(50), default="viewer")  # admin, manager, analyst, viewer
    scopes = Column(JSON, default=[])
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    
    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email"),
    )


class Property(Base, TenantMixin, TimestampMixin):
    """Property/Building model"""
    __tablename__ = "properties"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    
    # NYC identifiers
    bbl = Column(String(10), nullable=False, index=True)
    bin = Column(String(7), nullable=True)
    address = Column(String(500))
    
    # Building info
    year_built = Column(Integer, nullable=True)
    units = Column(Integer, nullable=True)
    building_class = Column(String(10), nullable=True)
    
    # Status
    is_monitored = Column(Boolean, default=True)
    
    # Metadata
    metadata_json = Column(JSON, default={})
    
    # Relationships
    tenant = relationship("Tenant", back_populates="properties")
    violations = relationship("Violation", back_populates="property")
    
    __table_args__ = (
        Index("ix_properties_tenant_bbl", "tenant_id", "bbl"),
    )


class ViolationClass(str, enum.Enum):
    """DOB Violation Classes"""
    CLASS_A = "A"  # Non-hazardous
    CLASS_B = "B"  # Hazardous
    CLASS_C = "C"  # Immediately hazardous


class ViolationSource(str, enum.Enum):
    """Violation data sources"""
    DOB = "DOB"
    HPD = "HPD"
    NYC_311 = "311"
    FDNY = "FDNY"
    DOH = "DOH"


class Violation(Base, TenantMixin, TimestampMixin):
    """Violation records with TimescaleDB support"""
    __tablename__ = "violations"
    
    id = Column(String(36), primary_key=True)
    property_id = Column(String(36), ForeignKey("properties.id"), nullable=False)
    
    # Source information
    source = Column(SQLEnum(ViolationSource), nullable=False)
    external_id = Column(String(50), nullable=False)
    
    # Violation details
    violation_class = Column(SQLEnum(ViolationClass), nullable=True)
    description = Column(Text)
    disposition = Column(String(100))
    
    # Dates
    issued_date = Column(DateTime, nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    
    # Risk scoring
    risk_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    
    # AI/ML metadata
    ml_metadata = Column(JSON, default={})
    
    # Relationships
    property = relationship("Property", back_populates="violations")
    
    __table_args__ = (
        Index("ix_violations_property_source", "property_id", "source"),
        Index("ix_violations_tenant_issued", "tenant_id", "issued_date"),
        Index("ix_violations_risk_score", "risk_score"),
    )


class AuditLog(Base, TenantMixin, TimestampMixin):
    """Audit trail for compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(36), nullable=True)
    
    # Changes
    changes = Column(JSON, default={})
    
    # Request metadata
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    __table_args__ = (
        Index("ix_audit_logs_tenant_action", "tenant_id", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )


class APIKey(Base, TenantMixin, TimestampMixin):
    """API key management"""
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    
    # Permissions
    scopes = Column(JSON, default=[])
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash"),
    )
