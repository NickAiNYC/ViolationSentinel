"""
ViolationSentinel - NYC Property Violation Monitoring & Risk Assessment

Production-ready violation monitoring for landlords, property managers, and PropTech platforms.
"""

__version__ = "0.1.0"
__author__ = "ViolationSentinel Team"

# Core exports for easy imports
from .scoring import (
    pre1974_risk_multiplier,
    inspector_risk_multiplier,
    heat_violation_forecast,
    peer_percentile,
)

__all__ = [
    "pre1974_risk_multiplier",
    "inspector_risk_multiplier", 
    "heat_violation_forecast",
    "peer_percentile",
]
