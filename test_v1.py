"""
Test V1 Risk Engine
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


if __name__ == "__main__":
    print("Running ViolationSentinel V1 Tests")
    print("=" * 50)
    
    test_risk_engine_basic()
    test_risk_engine_low_risk()
    test_risk_engine_urgent()
    test_status_colors()
    test_recommendations()
    
    print("=" * 50)
    print("✅ All tests passed!")
