"""
Property Model
Core property entity with normalized address data
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4, UUID
from sqlalchemy import String, Float, Integer, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from backend.data_models.base import Base, TimestampMixin, SoftDeleteMixin


class Property(Base, TimestampMixin, SoftDeleteMixin):
    """Property entity"""
    
    __tablename__ = "properties"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Identifiers
    bbl: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    bin: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, index=True)
    
    # Address (Normalized)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), default="NY", nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    borough: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Geolocation
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Property Details
    property_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    units_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    square_footage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Portfolio Association
    portfolio_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    
    # Organization (Multi-tenant)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    violations: Mapped[List["Violation"]] = relationship(
        "Violation",
        back_populates="property_rel",
        cascade="all, delete-orphan"
    )
    
    risk_scores: Mapped[List["RiskScore"]] = relationship(
        "RiskScore",
        back_populates="property_rel",
        cascade="all, delete-orphan"
    )
    
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="property_rel",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_properties_location", "latitude", "longitude"),
        Index("ix_properties_org_borough", "organization_id", "borough"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="check_latitude_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="check_longitude_range"),
    )
    
    def __repr__(self) -> str:
        return f"<Property(id={self.id}, bbl={self.bbl}, address={self.address_line1})>"
