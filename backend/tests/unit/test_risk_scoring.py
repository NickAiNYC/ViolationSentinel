"""
Unit tests for risk scoring
"""

import pytest
from backend.risk_scoring.risk_engine import RiskScoringEngine


def test_risk_engine_initialization():
    """Test risk engine initialization"""
    engine = RiskScoringEngine()
    assert engine.model_version == "v1.0.0"


def test_calculate_risk_score():
    """Test risk score calculation"""
    engine = RiskScoringEngine()
    result = engine.calculate_property_risk("test-property-id")
    
    assert "property_id" in result
    assert "overall_score" in result
    assert "safety_score" in result
    assert "legal_score" in result
    assert "financial_score" in result
    assert result["model_version"] == "v1.0.0"
    assert 0 <= result["overall_score"] <= 100
