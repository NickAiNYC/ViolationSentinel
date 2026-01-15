"""
Alert Models
Alert rules and triggered alerts
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum
from sqlalchemy import String, Text, Float, DateTime, Boolean, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from backend.data_models.base import Base, TimestampMixin


class AlertType(str, Enum):
    """Alert type"""
    NEW_VIOLATION = "NEW_VIOLATION"
    RISK_THRESHOLD = "RISK_THRESHOLD"
    COMPLIANCE_DUE = "COMPLIANCE_DUE"
    TREND_CHANGE = "TREND_CHANGE"
    DATA_ANOMALY = "DATA_ANOMALY"
    CUSTOM = "CUSTOM"


class AlertSeverity(str, Enum):
    """Alert severity"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertChannel(str, Enum):
    """Alert notification channel"""
    EMAIL = "EMAIL"
    SMS = "SMS"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"
    IN_APP = "IN_APP"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AlertRule(Base, TimestampMixin):
    """Alert rule configuration"""
    
    __tablename__ = "alert_rules"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Organization (Multi-tenant)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Rule Configuration
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    alert_type: Mapped[AlertType] = mapped_column(
        SQLEnum(AlertType),
        nullable=False,
        index=True
    )
    
    # Thresholds
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_operator: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # >, <, >=, <=, ==
    
    # Channels
    channels: Mapped[list] = mapped_column(JSONB, nullable=False)  # List of AlertChannel values
    
    # Targets
    target_properties: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # Property IDs
    target_portfolios: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # Portfolio IDs
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Metadata
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="alert_rule",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name={self.name}, type={self.alert_type})>"


class Alert(Base, TimestampMixin):
    """Triggered alert"""
    
    __tablename__ = "alerts"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Foreign Keys
    property_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    alert_rule_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Organization (Multi-tenant)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Alert Details
    alert_type: Mapped[AlertType] = mapped_column(
        SQLEnum(AlertType),
        nullable=False,
        index=True
    )
    
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity),
        nullable=False,
        index=True
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus),
        nullable=False,
        default=AlertStatus.ACTIVE,
        index=True
    )
    
    # Timestamps
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # User Actions
    acknowledged_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True
    )
    resolved_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True
    )
    
    # Notification
    channels_notified: Mapped[list] = mapped_column(JSONB, nullable=False)
    notification_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Context
    context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    property_rel: Mapped[Optional["Property"]] = relationship(
        "Property",
        back_populates="alerts"
    )
    
    alert_rule: Mapped[Optional["AlertRule"]] = relationship(
        "AlertRule",
        back_populates="alerts"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_alerts_org_status", "organization_id", "status"),
        Index("ix_alerts_property_status", "property_id", "status"),
        Index("ix_alerts_triggered_status", "triggered_at", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type}, severity={self.severity}, status={self.status})>"
