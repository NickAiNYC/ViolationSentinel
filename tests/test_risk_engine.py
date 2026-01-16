"""
Integration tests for the complete risk engine.

Tests all competitive moat features working together.
"""

import pytest
from datetime import datetime

# Support both old and new package structure
try:
    from src.violationsentinel.scoring import (
        pre1974_risk_multiplier,
        inspector_risk_multiplier,
        get_borough_from_bbl,
        heat_violation_forecast,
        is_heat_season,
        peer_percentile,
    )
except ImportError:
    from risk_engine.pre1974_multiplier import pre1974_risk_multiplier
    from risk_engine.inspector_patterns import inspector_risk_multiplier, get_borough_from_bbl
    from risk_engine.seasonal_heat_model import heat_violation_forecast, is_heat_season
    from risk_engine.peer_benchmark import peer_percentile


class TestInspectorPatterns:
    """Test inspector beat pattern analysis."""
    
    def test_hotspot_districts(self):
        """Test known hotspot districts."""
        # Brooklyn Council 36 (Clinton Hill) is a known hotspot
        multiplier = inspector_risk_multiplier('3012650001', 'brooklyn_council_36')
        assert multiplier == 2.3
        
        # Bronx Council 15 is a hotspot
        multiplier = inspector_risk_multiplier('2012650001', 'bronx_council_15')
        assert multiplier == 2.2
    
    def test_borough_baseline(self):
        """Test borough baseline multipliers."""
        # Brooklyn BBL without district
        multiplier = inspector_risk_multiplier('3012650001')
        assert multiplier == 1.2  # Brooklyn baseline
        
        # Manhattan BBL without district
        multiplier = inspector_risk_multiplier('1012650001')
        assert multiplier == 1.3  # Manhattan baseline
        
        # Queens BBL without district
        multiplier = inspector_risk_multiplier('4012650001')
        assert multiplier == 1.1  # Queens baseline
    
    def test_borough_extraction_from_bbl(self):
        """Test BBL borough extraction."""
        assert get_borough_from_bbl('1012650001') == 'manhattan'
        assert get_borough_from_bbl('2012650001') == 'bronx'
        assert get_borough_from_bbl('3012650001') == 'brooklyn'
        assert get_borough_from_bbl('4012650001') == 'queens'
        assert get_borough_from_bbl('5012650001') == 'staten_island'
    
    def test_invalid_bbl(self):
        """Test invalid BBL handling."""
        multiplier = inspector_risk_multiplier('invalid')
        assert multiplier == 1.0  # Default


class TestSeasonalHeatModel:
    """Test winter heat season forecasting."""
    
    def test_heat_season_detection(self):
        """Test heat season date detection."""
        # October through May is heat season
        assert is_heat_season(datetime(2024, 10, 1)) == True
        assert is_heat_season(datetime(2024, 11, 15)) == True
        assert is_heat_season(datetime(2024, 12, 31)) == True
        assert is_heat_season(datetime(2024, 1, 15)) == True
        assert is_heat_season(datetime(2024, 3, 15)) == True
        assert is_heat_season(datetime(2024, 5, 31)) == True
        
        # June through September is off-season
        assert is_heat_season(datetime(2024, 6, 1)) == False
        assert is_heat_season(datetime(2024, 7, 15)) == False
        assert is_heat_season(datetime(2024, 8, 31)) == False
        assert is_heat_season(datetime(2024, 9, 30)) == False
    
    def test_critical_heat_risk(self):
        """Test critical heat violation risk forecast."""
        # Peak winter with high complaints
        forecast = heat_violation_forecast(
            heat_complaints_30d=5,
            avg_temp=50,
            current_date=datetime(2024, 2, 1)  # Peak season
        )
        
        assert forecast['urgency'] == 'CRITICAL'
        assert forecast['risk_multiplier'] >= 4.0
        assert forecast['days_to_violation'] <= 14
        assert 'Class C' in forecast['fine_range']
    
    def test_moderate_heat_risk(self):
        """Test moderate heat risk."""
        forecast = heat_violation_forecast(
            heat_complaints_30d=2,
            avg_temp=65,
            current_date=datetime(2024, 4, 1)
        )
        
        assert forecast['urgency'] in ['MODERATE', 'LOW']
        assert forecast['risk_multiplier'] < 4.0
    
    def test_low_heat_risk_off_season(self):
        """Test low risk during off-season."""
        forecast = heat_violation_forecast(
            heat_complaints_30d=1,
            avg_temp=75,
            current_date=datetime(2024, 7, 1)  # Off-season
        )
        
        # With 1 complaint, it's moderate (1.5x complaint_risk * 1.0x seasonal = 1.5x)
        assert forecast['urgency'] in ['LOW', 'MODERATE']
        assert forecast['risk_multiplier'] < 2.0


class TestPeerBenchmarking:
    """Test peer benchmarking functionality."""
    
    def test_peer_percentile_high_risk(self):
        """Test high-risk building percentile."""
        result = peer_percentile(
            address="123 Main St",
            risk_score=85.0,
            building_data={'units': 24, 'year_built': 1965}
        )
        
        assert result['risk_score'] == 85.0
        assert result['percentile'] is not None
        assert result['similar_count'] > 0
        assert 'Top' in result['vs_peers']  # High score = top % riskiest
        assert result['urgency'] in ['CRITICAL', 'HIGH']
    
    def test_peer_percentile_low_risk(self):
        """Test low-risk building percentile."""
        result = peer_percentile(
            address="456 Oak Ave",
            risk_score=25.0,
            building_data={'units': 24, 'year_built': 2000}
        )
        
        assert result['risk_score'] == 25.0
        assert result['percentile'] is not None
        assert result['urgency'] == 'LOW'
    
    def test_insufficient_peer_data(self):
        """Test with no similar buildings."""
        result = peer_percentile(
            address="Test St",
            risk_score=50.0,
            similar_buildings=[]
        )
        
        assert result['vs_peers'] == 'Insufficient peer data'
        assert result['percentile'] is None


class TestIntegratedRiskScoring:
    """Test multiple risk factors working together."""
    
    def test_worst_case_building(self):
        """Test building with all worst-case risk factors."""
        # Pre-1960, Brooklyn hotspot, winter with heat complaints
        
        # Building era risk
        era_mult, _ = pre1974_risk_multiplier({'year_built': 1950})
        assert era_mult == 3.8
        
        # Inspector pattern risk
        inspector_mult = inspector_risk_multiplier('3012650001', 'brooklyn_council_36')
        assert inspector_mult == 2.3
        
        # Heat season risk
        heat_forecast = heat_violation_forecast(
            heat_complaints_30d=5,
            avg_temp=50,
            current_date=datetime(2024, 2, 1)
        )
        assert heat_forecast['urgency'] == 'CRITICAL'
        
        # Combined risk
        combined_risk = era_mult * inspector_mult * heat_forecast['risk_multiplier']
        assert combined_risk > 30.0  # Extremely high risk
    
    def test_best_case_building(self):
        """Test building with all best-case factors."""
        # Modern, low enforcement area, off-season, no complaints
        
        # Building era risk
        era_mult, _ = pre1974_risk_multiplier({'year_built': 2010})
        assert era_mult == 1.0
        
        # Inspector pattern (Staten Island baseline)
        inspector_mult = inspector_risk_multiplier('5012650001')
        assert inspector_mult == 0.9
        
        # Off-season, no complaints
        heat_forecast = heat_violation_forecast(
            heat_complaints_30d=0,
            avg_temp=75,
            current_date=datetime(2024, 7, 1)
        )
        assert heat_forecast['urgency'] == 'LOW'
        
        # Combined risk should be low
        combined_risk = era_mult * inspector_mult * heat_forecast['risk_multiplier']
        assert combined_risk < 2.0


class TestRiskEngineEdgeCases:
    """Test edge cases and error handling."""
    
    def test_missing_data_handling(self):
        """Test graceful handling of missing data."""
        # Missing year_built
        mult, _ = pre1974_risk_multiplier({})
        assert mult == 1.0
        
        # Invalid BBL
        inspector_mult = inspector_risk_multiplier('')
        assert inspector_mult == 1.0
        
        # No heat complaints
        forecast = heat_violation_forecast(0, None)
        assert forecast['urgency'] in ['LOW', 'MODERATE']  # Depends on current date
    
    def test_extreme_values(self):
        """Test handling of extreme values."""
        # Very old building (1800 is actually valid, just old)
        mult, _ = pre1974_risk_multiplier({'year_built': 1800})
        assert mult == 3.8  # Pre-1960
        
        # Many heat complaints
        forecast = heat_violation_forecast(100, 30)
        assert forecast['urgency'] == 'CRITICAL'
        
        # Extremely high risk score
        peer = peer_percentile("Test", 150.0, {})
        assert peer['risk_score'] == 150.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
