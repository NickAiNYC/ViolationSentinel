"""
Test V1 Risk Engine with Confidence Scoring and ML Features
"""

from backend.v1.risk_engine import risk_engine


def test_risk_engine_basic():
    """Test basic risk scoring"""
    result = risk_engine.calculate_risk(
        class_c_count=2,
        heat_complaints_7d=1,
        open_violations_90d=3,
        complaint_311_spike=1
    )
    
    # Expected: 2*40 + 1*30 + 3*20 + 1*10 = 80 + 30 + 60 + 10 = 180, capped at 100
    assert result['risk_score'] == 100
    assert result['priority'] == 'IMMEDIATE'
    assert '$' in result['fine_risk_estimate']
    assert 'confidence' in result
    assert 'ml_features' in result
    
    print("✅ Basic risk calculation test passed")


def test_risk_engine_low_risk():
    """Test low risk scenario"""
    result = risk_engine.calculate_risk(
        class_c_count=0,
        heat_complaints_7d=0,
        open_violations_90d=1,
        complaint_311_spike=0
    )
    
    # Expected: 1*20 = 20
    assert result['risk_score'] == 20
    assert result['priority'] == 'NORMAL'
    
    print("✅ Low risk test passed")


def test_risk_engine_urgent():
    """Test urgent priority threshold"""
    result = risk_engine.calculate_risk(
        class_c_count=1,
        heat_complaints_7d=0,
        open_violations_90d=1,
        complaint_311_spike=1
    )
    
    # Expected: 1*40 + 1*20 + 1*10 = 70
    assert result['risk_score'] == 70
    assert result['priority'] == 'URGENT'
    
    print("✅ Urgent priority test passed")


def test_status_colors():
    """Test status color assignment"""
    assert risk_engine.get_status_color(85) == 'RED'
    assert risk_engine.get_status_color(65) == 'YELLOW'
    assert risk_engine.get_status_color(40) == 'GREEN'
    
    print("✅ Status color test passed")


def test_recommendations():
    """Test recommendation generation"""
    recs = risk_engine.get_recommendations(
        class_c_count=2,
        heat_complaints_7d=1,
        open_violations_90d=4
    )
    
    assert len(recs) == 3
    assert recs[0]['priority'] == 'CRITICAL'
    assert 'Class C' in recs[0]['action']
    
    print("✅ Recommendations test passed")


def test_confidence_scoring():
    """Test confidence score calculation"""
    # High confidence: lots of violations, recent data
    result = risk_engine.calculate_risk(
        class_c_count=2,
        heat_complaints_7d=1,
        open_violations_90d=3,
        total_violations=10,
        days_since_last_inspection=5
    )
    
    assert 'confidence' in result
    assert 'confidence_breakdown' in result
    assert 0 <= result['confidence'] <= 1
    assert 'volume_factor' in result['confidence_breakdown']
    assert 'recency_factor' in result['confidence_breakdown']
    assert 'completeness_factor' in result['confidence_breakdown']
    
    # High recency + volume should give high confidence
    assert result['confidence'] > 0.6
    
    print("✅ Confidence scoring test passed")


def test_ml_features():
    """Test ML feature extraction"""
    result = risk_engine.calculate_risk(
        class_c_count=3,
        heat_complaints_7d=2,
        open_violations_90d=5,
        complaint_311_spike=1,
        total_violations=15,
        days_since_last_inspection=30,
        litigation_flag=True,
        building_age=75
    )
    
    assert 'ml_features' in result
    ml_features = result['ml_features']
    
    # Check all expected features exist
    expected_features = [
        'class_c_normalized',
        'heat_complaints_normalized',
        'old_violations_normalized',
        'complaint_spike',
        'violation_rate',
        'inspection_staleness',
        'litigation_risk',
        'class_c_x_heat',
        'old_x_total',
        'building_age_normalized',
        'critical_ratio'
    ]
    
    for feature in expected_features:
        assert feature in ml_features, f"Missing feature: {feature}"
        assert 0 <= ml_features[feature] <= 1.5, f"Feature {feature} out of range"
    
    # Litigation should be flagged
    assert ml_features['litigation_risk'] == 1.0
    
    print("✅ ML feature extraction test passed")


def test_litigation_flag():
    """Test litigation flag impact on fine estimates"""
    result_no_lit = risk_engine.calculate_risk(
        class_c_count=1,
        heat_complaints_7d=0,
        open_violations_90d=0,
        litigation_flag=False
    )
    
    result_with_lit = risk_engine.calculate_risk(
        class_c_count=1,
        heat_complaints_7d=0,
        open_violations_90d=0,
        litigation_flag=True
    )
    
    # Extract numeric values from fine estimates
    fine_no_lit = int(result_no_lit['fine_risk_estimate'].replace('$', '').replace(',', ''))
    fine_with_lit = int(result_with_lit['fine_risk_estimate'].replace('$', '').replace(',', ''))
    
    # Litigation should add $10,000
    assert fine_with_lit == fine_no_lit + 10000
    
    print("✅ Litigation flag test passed")


def test_recommendations_with_litigation():
    """Test that litigation appears in recommendations"""
    recs = risk_engine.get_recommendations(
        class_c_count=0,
        heat_complaints_7d=0,
        open_violations_90d=0,
        litigation_flag=True
    )
    
    # Should have litigation recommendation
    litigation_rec = [r for r in recs if 'litigation' in r['action'].lower()]
    assert len(litigation_rec) > 0
    assert litigation_rec[0]['priority'] == 'HIGH'
    
    print("✅ Litigation recommendation test passed")


if __name__ == "__main__":
    print("Running ViolationSentinel V1 Enhanced Tests")
    print("=" * 50)
    
    test_risk_engine_basic()
    test_risk_engine_low_risk()
    test_risk_engine_urgent()
    test_status_colors()
    test_recommendations()
    test_confidence_scoring()
    test_ml_features()
    test_litigation_flag()
    test_recommendations_with_litigation()
    
    print("=" * 50)
    print("✅ All 9 tests passed!")
    print("\n📊 Test Coverage:")
    print("  - Basic risk scoring ✓")
    print("  - Priority thresholds ✓")
    print("  - Confidence scoring ✓")
    print("  - ML feature extraction ✓")
    print("  - Litigation handling ✓")
    print("  - Recommendations ✓")
