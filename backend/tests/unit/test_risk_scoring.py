"""
Unit tests for risk scoring
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from backend.risk_scoring.risk_engine import RiskScoringEngine
from backend.data_models.violation import Violation, ViolationSeverity, ViolationStatus


def test_risk_engine_initialization():
    """Test risk engine initialization"""
    engine = RiskScoringEngine()
    assert engine.model_version == "v1.1.0"
    assert engine.model_name == "RiskEngine-Deterministic-Hybrid"


def test_time_decay_calculation():
    """Test time decay factor calculation"""
    engine = RiskScoringEngine()
    
    # Today's violation should have decay factor close to 1.0
    today = date.today()
    decay_today = engine._calculate_time_decay_factor(today)
    assert decay_today == 1.0
    
    # 180 days old (half-life) should have decay factor of 0.5
    half_life_date = today - timedelta(days=180)
    decay_half_life = engine._calculate_time_decay_factor(half_life_date)
    assert 0.49 < decay_half_life < 0.51
    
    # 360 days old should have decay factor of ~0.25
    old_date = today - timedelta(days=360)
    decay_old = engine._calculate_time_decay_factor(old_date)
    assert 0.24 < decay_old < 0.26


def test_severity_weights():
    """Test severity weight configuration"""
    engine = RiskScoringEngine()
    
    assert engine.SEVERITY_WEIGHTS[ViolationSeverity.CLASS_C] == 10.0
    assert engine.SEVERITY_WEIGHTS[ViolationSeverity.CLASS_B] == 5.0
    assert engine.SEVERITY_WEIGHTS[ViolationSeverity.CLASS_A] == 2.0
    assert engine.SEVERITY_WEIGHTS[ViolationSeverity.UNKNOWN] == 1.0


def test_violation_categorization():
    """Test violation categorization into safety/legal/financial"""
    engine = RiskScoringEngine()
    
    # Test safety violation
    safety_violation = Violation(
        property_id=uuid4(),
        source="DOB",
        source_id="TEST-001",
        violation_code="FS-001",
        description="Fire safety hazard detected",
        severity=ViolationSeverity.CLASS_C,
        status=ViolationStatus.OPEN,
        issue_date=date.today(),
        data_freshness=datetime.utcnow(),
        hash="test_hash_1"
    )
    is_safety, is_legal, is_financial = engine._categorize_violation(safety_violation)
    assert is_safety is True
    
    # Test legal violation
    legal_violation = Violation(
        property_id=uuid4(),
        source="DOB",
        source_id="TEST-002",
        violation_code="PM-001",
        description="Permit violation for construction work",
        severity=ViolationSeverity.CLASS_B,
        status=ViolationStatus.OPEN,
        issue_date=date.today(),
        data_freshness=datetime.utcnow(),
        hash="test_hash_2"
    )
    is_safety, is_legal, is_financial = engine._categorize_violation(legal_violation)
    assert is_legal is True
    
    # Test financial violation
    financial_violation = Violation(
        property_id=uuid4(),
        source="HPD",
        source_id="TEST-003",
        violation_code="FN-001",
        description="Outstanding penalty payment required",
        severity=ViolationSeverity.CLASS_A,
        status=ViolationStatus.OPEN,
        issue_date=date.today(),
        data_freshness=datetime.utcnow(),
        hash="test_hash_3"
    )
    is_safety, is_legal, is_financial = engine._categorize_violation(financial_violation)
    assert is_financial is True


def test_confidence_score_calculation():
    """Test confidence score calculation"""
    engine = RiskScoringEngine()
    
    # Test with no violations (low confidence)
    confidence_none = engine._calculate_confidence_score([])
    assert 0.0 <= confidence_none <= 0.6
    
    # Test with recent violations (high confidence)
    recent_violations = [
        Violation(
            property_id=uuid4(),
            source="DOB",
            source_id=f"TEST-{i:03d}",
            violation_code="VC-001",
            description="Test violation",
            severity=ViolationSeverity.CLASS_B,
            category="safety",
            status=ViolationStatus.OPEN,
            issue_date=date.today() - timedelta(days=10),
            data_freshness=datetime.utcnow(),
            hash=f"test_hash_{i}"
        )
        for i in range(10)
    ]
    confidence_high = engine._calculate_confidence_score(recent_violations)
    assert 0.7 <= confidence_high <= 1.0


def test_escalation_detection():
    """Test violation escalation detection"""
    engine = RiskScoringEngine()
    
    # Create violations with increasing frequency (escalating)
    escalating_violations = []
    base_date = date.today() - timedelta(days=200)
    
    # Older period: 2 violations over 110 days
    escalating_violations.append(Violation(
        property_id=uuid4(),
        source="DOB",
        source_id="ESC-001",
        violation_code="VC-001",
        description="Old violation 1",
        severity=ViolationSeverity.CLASS_A,
        status=ViolationStatus.OPEN,
        issue_date=base_date,
        data_freshness=datetime.utcnow(),
        hash="esc_hash_1"
    ))
    escalating_violations.append(Violation(
        property_id=uuid4(),
        source="DOB",
        source_id="ESC-002",
        violation_code="VC-002",
        description="Old violation 2",
        severity=ViolationSeverity.CLASS_A,
        status=ViolationStatus.OPEN,
        issue_date=base_date + timedelta(days=50),
        data_freshness=datetime.utcnow(),
        hash="esc_hash_2"
    ))
    
    # Recent period: 6 violations over 90 days (escalating)
    for i in range(6):
        escalating_violations.append(Violation(
            property_id=uuid4(),
            source="DOB",
            source_id=f"ESC-{i+3:03d}",
            violation_code=f"VC-{i+3:03d}",
            description=f"Recent violation {i+1}",
            severity=ViolationSeverity.CLASS_B,
            status=ViolationStatus.OPEN,
            issue_date=date.today() - timedelta(days=15 * i),
            data_freshness=datetime.utcnow(),
            hash=f"esc_hash_{i+3}"
        ))
    
    is_escalating, escalation_rate = engine._detect_escalation(escalating_violations)
    assert is_escalating is True
    assert escalation_rate > 20  # Should detect significant escalation


def test_violation_score_calculation():
    """Test individual violation score calculation"""
    engine = RiskScoringEngine()
    
    # Recent Class C violation should have high score
    recent_class_c = Violation(
        property_id=uuid4(),
        source="DOB",
        source_id="SCORE-001",
        violation_code="VC-001",
        description="Immediate hazard",
        severity=ViolationSeverity.CLASS_C,
        status=ViolationStatus.OPEN,
        issue_date=date.today(),
        data_freshness=datetime.utcnow(),
        hash="score_hash_1"
    )
    score_c = engine._calculate_violation_score(recent_class_c)
    assert score_c == 10.0  # Class C weight * decay factor of 1.0
    
    # Old Class A violation should have lower score
    old_class_a = Violation(
        property_id=uuid4(),
        source="DOB",
        source_id="SCORE-002",
        violation_code="VC-002",
        description="Minor issue",
        severity=ViolationSeverity.CLASS_A,
        status=ViolationStatus.OPEN,
        issue_date=date.today() - timedelta(days=180),
        data_freshness=datetime.utcnow(),
        hash="score_hash_2"
    )
    score_a = engine._calculate_violation_score(old_class_a)
    assert 0.9 < score_a < 1.1  # Class A weight (2.0) * decay factor (~0.5)
