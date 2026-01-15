"""
Risk Score Model
Property risk assessment and forecasting
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum
from sqlalchemy import String, Float, DateTime, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from backend.data_models.base import Base, TimestampMixin


class TrendDirection(str, Enum):
    """Risk trend direction"""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    WORSENING = "WORSENING"
    UNKNOWN = "UNKNOWN"


class RiskScore(Base, TimestampMixin):
    """Property risk score"""
    
    __tablename__ = "risk_scores"
    
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
    
    # Overall Score (0-100)
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True
    )
    
    # Sub-scores (0-100)
    safety_score: Mapped[float] = mapped_column(Float, nullable=False)
    legal_score: Mapped[float] = mapped_column(Float, nullable=False)
    financial_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Trend
    trend_direction: Mapped[TrendDirection] = mapped_column(
        SQLEnum(TrendDirection),
        nullable=False,
        default=TrendDirection.UNKNOWN
    )
    trend_change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Confidence & Model Info
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Calculation Details
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    calculation_duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Features used
    features: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Forecast (optional)
    forecast_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forecast_90d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forecast_180d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    property: Mapped["Property"] = relationship(
        "Property",
        back_populates="risk_scores"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_risk_scores_property_calculated", "property_id", "calculated_at"),
        Index("ix_risk_scores_overall_score", "overall_score"),
    )
    
    def __repr__(self) -> str:
        return f"<RiskScore(id={self.id}, property_id={self.property_id}, overall={self.overall_score:.2f}, trend={self.trend_direction})>"
    
    @property
    def risk_level(self) -> str:
        """Categorize risk level"""
        if self.overall_score >= 80:
            return "CRITICAL"
        elif self.overall_score >= 60:
            return "HIGH"
        elif self.overall_score >= 40:
            return "MEDIUM"
        elif self.overall_score >= 20:
            return "LOW"
        else:
            return "MINIMAL"
