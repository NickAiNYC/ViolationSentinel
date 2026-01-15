"""
Unit tests for risk scoring
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from backend.risk_scoring.risk_engine import RiskScoringEngine, EngineType
from backend.data_models.violation import Violation, ViolationSeverity, ViolationStatus


def test_risk_engine_initialization():
    """Test risk engine initialization"""
    engine = RiskScoringEngine()
    assert engine.model_version == "v1.2.0"
    assert engine.model_name == "RiskEngine-Deterministic-Hybrid"
    assert engine.engine_type == EngineType.DETERMINISTIC
    
    # Test with different engine type
    ml_engine = RiskScoringEngine(engine_type=EngineType.ML)
    assert ml_engine.engine_type == EngineType.ML


def test_configurable_severity_weights():
    """Test that severity weights are loaded from configuration"""
    engine = RiskScoringEngine()
    
    # Weights should be loaded from settings
    assert ViolationSeverity.CLASS_C in engine.severity_weights
    assert ViolationSeverity.CLASS_B in engine.severity_weights
    assert ViolationSeverity.CLASS_A in engine.severity_weights
    assert ViolationSeverity.UNKNOWN in engine.severity_weights
    
    # Verify values match config defaults
    assert engine.severity_weights[ViolationSeverity.CLASS_C] == 10.0
    assert engine.severity_weights[ViolationSeverity.CLASS_B] == 5.0
    assert engine.severity_weights[ViolationSeverity.CLASS_A] == 2.0


def test_time_decay_calculation():
    """Test time decay factor calculation"""
    engine = RiskScoringEngine()
    
    # Today's violation should have decay factor close to 1.0
    today = date.today()
    decay_today = engine._calculate_time_decay_factor(today)
    assert decay_today == 1.0
    
    # Half-life should have decay factor of 0.5
    half_life_date = today - timedelta(days=engine.time_decay_half_life_days)
    decay_half_life = engine._calculate_time_decay_factor(half_life_date)
    assert 0.49 < decay_half_life < 0.51
    
    # Double half-life should have decay factor of ~0.25
    old_date = today - timedelta(days=engine.time_decay_half_life_days * 2)
    decay_old = engine._calculate_time_decay_factor(old_date)
    assert 0.24 < decay_old < 0.26


def test_severity_weights():
    """Test severity weight configuration"""
    engine = RiskScoringEngine()
    
    # Weights should be loaded from config
    assert engine.severity_weights[ViolationSeverity.CLASS_C] == 10.0
    assert engine.severity_weights[ViolationSeverity.CLASS_B] == 5.0
    assert engine.severity_weights[ViolationSeverity.CLASS_A] == 2.0
    assert engine.severity_weights[ViolationSeverity.UNKNOWN] == 1.0


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
    """Test confidence score calculation with breakdown"""
    engine = RiskScoringEngine()
    
    # Test with no violations (low confidence)
    confidence, breakdown = engine._calculate_confidence_score([])
    assert 0.0 <= confidence <= 0.6
    assert 'volume_factor' in breakdown
    assert 'recency_factor' in breakdown
    assert 'completeness_factor' in breakdown
    
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
    confidence_high, breakdown_high = engine._calculate_confidence_score(recent_violations)
    assert 0.7 <= confidence_high <= 1.0
    assert all(0 <= v <= 1 for v in breakdown_high.values())


def test_escalation_detection():
    """Test violation escalation detection with minimum sample size guard"""
    engine = RiskScoringEngine()
    
    # Test with insufficient data (should not trigger escalation)
    few_violations = [
        Violation(
            property_id=uuid4(),
            source="DOB",
            source_id="ESC-001",
            violation_code="VC-001",
            description="Old violation 1",
            severity=ViolationSeverity.CLASS_A,
            status=ViolationStatus.OPEN,
            issue_date=date.today() - timedelta(days=200),
            data_freshness=datetime.utcnow(),
            hash="esc_hash_1"
        )
    ]
    is_escalating, escalation_rate, reason = engine._detect_escalation(few_violations)
    assert is_escalating is False
    # Reason may be None when not escalating, which is acceptable
    
    # Create violations with increasing frequency (escalating)
    escalating_violations = []
    base_date = date.today() - timedelta(days=200)
    
    # Older period: 3 violations over 110 days
    for i in range(3):
        escalating_violations.append(Violation(
            property_id=uuid4(),
            source="DOB",
            source_id=f"ESC-{i:03d}",
            violation_code=f"VC-{i:03d}",
            description=f"Old violation {i+1}",
            severity=ViolationSeverity.CLASS_A,
            status=ViolationStatus.OPEN,
            issue_date=base_date + timedelta(days=i * 30),
            data_freshness=datetime.utcnow(),
            hash=f"esc_hash_{i}"
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
    
    is_escalating, escalation_rate, reason = engine._detect_escalation(escalating_violations)
    assert is_escalating is True
    assert escalation_rate > engine.escalation_threshold_pct
    assert reason is not None and "increased" in reason.lower()


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


# Integration Tests
@pytest.mark.asyncio
async def test_high_risk_property_scoring():
    """
    Integration test: Score a high-risk property with multiple recent Class C violations
    Validates end-to-end behavior for critical risk scenarios
    """
    from backend.data_models.property import Property
    from backend.database import get_db
    
    engine = RiskScoringEngine()
    
    async with get_db() as db:
        # Create a test property
        property_id = uuid4()
        test_property = Property(
            id=property_id,
            bbl="1000000001",
            address_line1="123 High Risk Ave",
            city="New York",
            state="NY",
            zip_code="10001",
            borough="MANHATTAN",
            organization_id=uuid4()
        )
        db.add(test_property)
        
        # Add multiple recent Class C violations
        for i in range(5):
            violation = Violation(
                property_id=property_id,
                source="DOB",
                source_id=f"HIGH-RISK-{i:03d}",
                violation_code=f"CLASSC-{i:03d}",
                description=f"Immediately hazardous condition {i+1}",
                severity=ViolationSeverity.CLASS_C,
                category="safety",
                status=ViolationStatus.OPEN,
                issue_date=date.today() - timedelta(days=i * 5),
                data_freshness=datetime.utcnow(),
                hash=f"high_risk_hash_{i}"
            )
            db.add(violation)
        
        await db.commit()
        
        # Score the property
        result = await engine.calculate_property_risk_async(property_id)
        
        # Assertions
        assert result['overall_score'] >= 60, "High-risk property should have score >= 60"
        assert result['safety_score'] > 0, "Should have safety score"
        assert result['confidence'] > 0.7, "Should have high confidence with 5 violations"
        assert 'explanations' in result, "Should include explanations"
        assert 'top_contributing_violations' in result['explanations']
        assert len(result['explanations']['top_contributing_violations']) <= 5
        assert result['engine_type'] == EngineType.DETERMINISTIC.value
        assert 'confidence_breakdown' in result
        assert result['risk_level'] in ['HIGH', 'CRITICAL', 'MEDIUM']


@pytest.mark.asyncio
async def test_low_risk_property_scoring():
    """
    Integration test: Score a low-risk property with old, decayed violations
    Validates time decay impact and low-risk classification
    """
    from backend.data_models.property import Property
    from backend.database import get_db
    
    engine = RiskScoringEngine()
    
    async with get_db() as db:
        # Create a test property
        property_id = uuid4()
        test_property = Property(
            id=property_id,
            bbl="1000000002",
            address_line1="456 Low Risk Blvd",
            city="New York",
            state="NY",
            zip_code="10002",
            borough="BROOKLYN",
            organization_id=uuid4()
        )
        db.add(test_property)
        
        # Add old Class A violations (heavily decayed)
        for i in range(3):
            violation = Violation(
                property_id=property_id,
                source="HPD",
                source_id=f"LOW-RISK-{i:03d}",
                violation_code=f"CLASSA-{i:03d}",
                description=f"Minor violation {i+1}",
                severity=ViolationSeverity.CLASS_A,
                category="legal",
                status=ViolationStatus.OPEN,
                issue_date=date.today() - timedelta(days=365 + i * 30),
                data_freshness=datetime.utcnow(),
                hash=f"low_risk_hash_{i}"
            )
            db.add(violation)
        
        await db.commit()
        
        # Score the property
        result = await engine.calculate_property_risk_async(property_id)
        
        # Assertions
        assert result['overall_score'] < 40, "Low-risk property should have score < 40"
        assert result['legal_score'] > 0, "Should have legal score"
        assert 'explanations' in result, "Should include explanations"
        assert 'decay_impact' in result['explanations']
        assert result['engine_type'] == EngineType.DETERMINISTIC.value
        assert 'confidence_breakdown' in result
        assert result['risk_level'] in ['LOW', 'MINIMAL', 'MEDIUM']
        
        # Verify decay impact
        assert 'half-life' in result['explanations']['decay_impact']
