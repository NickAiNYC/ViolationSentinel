"""
Risk scoring & confidence logic

Core competitive moat features for violation risk assessment.
"""

from .pre1974_multiplier import (
    pre1974_risk_multiplier,
    get_building_era_risk,
    calculate_portfolio_pre1974_stats,
    is_pre1974_building,
)
from .inspector_patterns import (
    inspector_risk_multiplier,
    get_district_hotspot,
    get_borough_from_bbl,
)
from .seasonal_heat_model import (
    heat_violation_forecast,
    is_heat_season,
    calculate_winter_risk_score,
)
from .peer_benchmark import (
    peer_percentile,
    get_similar_properties,
    calculate_portfolio_peer_ranking,
)

__all__ = [
    # Pre-1974 risk
    "pre1974_risk_multiplier",
    "get_building_era_risk",
    "calculate_portfolio_pre1974_stats",
    "is_pre1974_building",
    # Inspector patterns
    "inspector_risk_multiplier",
    "get_district_hotspot",
    "get_borough_from_bbl",
    # Heat season
    "heat_violation_forecast",
    "is_heat_season",
    "calculate_winter_risk_score",
    # Peer benchmark
    "peer_percentile",
    "get_similar_properties",
    "calculate_portfolio_peer_ranking",
]
