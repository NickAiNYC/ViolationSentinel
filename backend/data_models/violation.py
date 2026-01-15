"""
Violation Model
Building violations from DOB, HPD, and 311 sources
"""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum
from sqlalchemy import String, Text, Date, DateTime, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from backend.data_models.base import Base, TimestampMixin


class ViolationSource(str, Enum):
    """Violation data source"""
    DOB = "DOB"  # Department of Buildings
    HPD = "HPD"  # Housing Preservation & Development
    COMPLAINT_311 = "311"  # 311 Complaints
    ECB = "ECB"  # Environmental Control Board


class ViolationSeverity(str, Enum):
    """Violation severity classification"""
    CLASS_A = "A"  # Non-hazardous
    CLASS_B = "B"  # Hazardous
    CLASS_C = "C"  # Immediately hazardous
    UNKNOWN = "UNKNOWN"


class ViolationStatus(str, Enum):
    """Violation status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class Violation(Base, TimestampMixin):
    """Violation record"""
    
    __tablename__ = "violations"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Foreign Key
    property_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Source System
    source: Mapped[ViolationSource] = mapped_column(
        SQLEnum(ViolationSource),
        nullable=False,
        index=True
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Violation Details
    violation_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    violation_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Classification
    severity: Mapped[ViolationSeverity] = mapped_column(
        SQLEnum(ViolationSeverity),
        nullable=False,
        index=True
    )
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Status & Dates
    status: Mapped[ViolationStatus] = mapped_column(
        SQLEnum(ViolationStatus),
        nullable=False,
        index=True,
        default=ViolationStatus.OPEN
    )
    
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Financial
    penalty_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Location within property
    location_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Raw Data
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Data Quality
    data_freshness: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Deduplication hash
    hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Relationships
    property_rel: Mapped["Property"] = relationship(
        "Property",
        back_populates="violations"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_violations_property_status", "property_id", "status"),
        Index("ix_violations_source_status", "source", "status"),
        Index("ix_violations_severity_status", "severity", "status"),
        Index("ix_violations_issue_date_status", "issue_date", "status"),
        # Unique constraint for deduplication
        Index("ix_violations_unique_source", "source", "source_id", "property_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Violation(id={self.id}, code={self.violation_code}, severity={self.severity}, status={self.status})>"
