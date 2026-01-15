"""
Unit tests for Pre-1974 Risk Multiplier

Tests the core competitive moat feature.
"""

import pytest
from risk_engine.pre1974_multiplier import (
    pre1974_risk_multiplier,
    get_building_era_risk,
    is_pre1974_building,
    calculate_portfolio_pre1974_stats
)


class TestPre1974RiskMultiplier:
    """Test pre-1974 risk multiplier calculations."""
    
    def test_modern_building_baseline(self):
        """Modern buildings (1974+) should have 1.0x baseline."""
        result = pre1974_risk_multiplier({'year_built': 2000})
        assert result[0] == 1.0
        assert "Modern construction" in result[1]
        
        result = pre1974_risk_multiplier({'year_built': 1974})
        assert result[0] == 1.0
    
    def test_rent_stabilized_era(self):
        """Buildings 1960-1973 should have 2.5x multiplier."""
        result = pre1974_risk_multiplier({'year_built': 1965})
        assert result[0] == 2.5
        assert "Rent-stabilized era" in result[1]
        
        result = pre1974_risk_multiplier({'year_built': 1973})
        assert result[0] == 2.5
        
        result = pre1974_risk_multiplier({'year_built': 1960})
        assert result[0] == 2.5
    
    def test_pre1960_critical(self):
        """Pre-1960 buildings should have 3.8x multiplier."""
        result = pre1974_risk_multiplier({'year_built': 1950})
        assert result[0] == 3.8
        assert "Pre-1960" in result[1]
        assert "critical risk" in result[1].lower()
        
        result = pre1974_risk_multiplier({'year_built': 1920})
        assert result[0] == 3.8
    
    def test_invalid_year_defaults(self):
        """Invalid years should default to baseline."""
        result = pre1974_risk_multiplier({'year_built': None})
        assert result[0] == 1.0
        
        result = pre1974_risk_multiplier({'year_built': 1500})  # Too old
        assert result[0] == 1.0
        
        result = pre1974_risk_multiplier({'year_built': 3000})  # Future
        assert result[0] == 1.0
        
        result = pre1974_risk_multiplier({})  # Missing
        assert result[0] == 1.0


class TestBuildingEraRisk:
    """Test detailed building era risk assessment."""
    
    def test_modern_era_details(self):
        """Test modern building era details."""
        result = get_building_era_risk(2000)
        
        assert result['multiplier'] == 1.0
        assert result['era'] == 'Modern (1974+)'
        assert len(result['risk_factors']) == 0
        assert 'Standard maintenance' in result['action_items'][0]
    
    def test_rent_stabilized_era_details(self):
        """Test rent-stabilized era details."""
        result = get_building_era_risk(1965)
        
        assert result['multiplier'] == 2.5
        assert result['era'] == 'Rent-Stabilized Era (1960-1973)'
        assert len(result['risk_factors']) > 0
        assert any('lead paint' in factor.lower() for factor in result['risk_factors'])
        assert any('heat system' in action.lower() for action in result['action_items'])
    
    def test_pre1960_era_details(self):
        """Test pre-1960 era details."""
        result = get_building_era_risk(1950)
        
        assert result['multiplier'] == 3.8
        assert result['era'] == 'Pre-1960 Legacy'
        assert len(result['risk_factors']) > 0
        assert len(result['action_items']) > 0
        assert any('lead paint' in factor.lower() for factor in result['risk_factors'])
        assert any('urgent' in action.lower() for action in result['action_items'])
    
    def test_unknown_year_handling(self):
        """Test handling of unknown/invalid years."""
        result = get_building_era_risk(None)
        assert result['multiplier'] == 1.0
        assert result['era'] == 'Unknown'


class TestPre1974Check:
    """Test pre-1974 building check function."""
    
    def test_is_pre1974_true(self):
        """Test buildings that are pre-1974."""
        assert is_pre1974_building(1973) == True
        assert is_pre1974_building(1960) == True
        assert is_pre1974_building(1920) == True
    
    def test_is_pre1974_false(self):
        """Test buildings that are not pre-1974."""
        assert is_pre1974_building(1974) == False
        assert is_pre1974_building(2000) == False
        assert is_pre1974_building(2023) == False
    
    def test_is_pre1974_invalid(self):
        """Test invalid year inputs."""
        assert is_pre1974_building(None) == False
        assert is_pre1974_building(1500) == False
        assert is_pre1974_building(3000) == False


class TestPortfolioStats:
    """Test portfolio-level statistics."""
    
    def test_empty_portfolio(self):
        """Test with empty portfolio."""
        stats = calculate_portfolio_pre1974_stats([])
        
        assert stats['total_buildings'] == 0
        assert stats['pre1974_count'] == 0
        assert stats['pre1974_percentage'] == 0
        assert stats['average_multiplier'] == 1.0
    
    def test_all_modern_buildings(self):
        """Test portfolio with all modern buildings."""
        buildings = [
            {'year_built': 2000},
            {'year_built': 1990},
            {'year_built': 1985}
        ]
        
        stats = calculate_portfolio_pre1974_stats(buildings)
        
        assert stats['total_buildings'] == 3
        assert stats['pre1974_count'] == 0
        assert stats['pre1960_count'] == 0
        assert stats['pre1974_percentage'] == 0
        assert stats['average_multiplier'] == 1.0
        assert stats['portfolio_risk_level'] == 'STANDARD'
    
    def test_mixed_portfolio(self):
        """Test portfolio with mixed building ages."""
        buildings = [
            {'year_built': 2000},  # 1.0x
            {'year_built': 1965},  # 2.5x
            {'year_built': 1950},  # 3.8x
            {'year_built': 1980}   # 1.0x
        ]
        
        stats = calculate_portfolio_pre1974_stats(buildings)
        
        assert stats['total_buildings'] == 4
        assert stats['pre1974_count'] == 2
        assert stats['pre1960_count'] == 1
        assert stats['pre1974_percentage'] == 50.0
        
        # Average: (1.0 + 2.5 + 3.8 + 1.0) / 4 = 2.075
        assert stats['average_multiplier'] == 2.08
        assert stats['high_risk_count'] == 1
        assert stats['portfolio_risk_level'] == 'CRITICAL'  # Has pre-1960
    
    def test_all_pre1960_portfolio(self):
        """Test portfolio with all pre-1960 buildings."""
        buildings = [
            {'year_built': 1950},
            {'year_built': 1945},
            {'year_built': 1955}
        ]
        
        stats = calculate_portfolio_pre1974_stats(buildings)
        
        assert stats['total_buildings'] == 3
        assert stats['pre1974_count'] == 3
        assert stats['pre1960_count'] == 3
        assert stats['pre1974_percentage'] == 100.0
        assert stats['average_multiplier'] == 3.8
        assert stats['portfolio_risk_level'] == 'CRITICAL'
    
    def test_portfolio_with_invalid_years(self):
        """Test portfolio with some invalid year data."""
        buildings = [
            {'year_built': 2000},
            {'year_built': None},
            {'year_built': 1965},
            {}  # Missing year_built
        ]
        
        stats = calculate_portfolio_pre1974_stats(buildings)
        
        assert stats['total_buildings'] == 4
        assert stats['pre1974_count'] == 1  # Only 1965
        # Average includes defaults to 1.0x for invalid years
        assert stats['average_multiplier'] > 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
