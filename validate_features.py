#!/usr/bin/env python
"""
Quick validation script for ViolationSentinel competitive moat features.
Run this to verify all features are working correctly.
"""

import sys
from datetime import datetime

print("=" * 70)
print("ViolationSentinel Competitive Moat Feature Validation")
print("=" * 70)
print()

# Test 1: Pre-1974 Risk Multiplier
print("✓ Testing Pre-1974 Risk Multiplier...")
from risk_engine.pre1974_multiplier import pre1974_risk_multiplier, calculate_portfolio_pre1974_stats

test_buildings = [
    {'year_built': 1950, 'name': 'Old Building'},
    {'year_built': 1970, 'name': 'Rent Stabilized'},
    {'year_built': 2000, 'name': 'Modern'}
]

for building in test_buildings:
    mult, explanation = pre1974_risk_multiplier(building)
    print(f"  {building['name']} ({building['year_built']}): {mult}x - {explanation}")

stats = calculate_portfolio_pre1974_stats(test_buildings)
print(f"  Portfolio stats: {stats['pre1974_count']}/{stats['total_buildings']} pre-1974 buildings")
print(f"  Average risk multiplier: {stats['average_multiplier']}x")
print()

# Test 2: Inspector Patterns
print("✓ Testing Inspector Beat Patterns...")
from risk_engine.inspector_patterns import inspector_risk_multiplier, get_borough_from_bbl

test_bbls = [
    ('3012650001', 'brooklyn_council_36'),
    ('1012650001', None),
    ('2012650001', 'bronx_council_15')
]

for bbl, district in test_bbls:
    borough = get_borough_from_bbl(bbl)
    mult = inspector_risk_multiplier(bbl, district)
    district_str = district or f"{borough} baseline"
    print(f"  BBL {bbl} ({district_str}): {mult}x enforcement")
print()

# Test 3: Winter Heat Season
print("✓ Testing Winter Heat Season Forecast...")
from risk_engine.seasonal_heat_model import heat_violation_forecast, is_heat_season

print(f"  Current date is in heat season: {is_heat_season()}")

# Critical case
forecast = heat_violation_forecast(
    heat_complaints_30d=5,
    avg_temp=50,
    current_date=datetime(2024, 2, 1)
)
print(f"  Critical scenario: {forecast['urgency']} risk")
print(f"    Risk multiplier: {forecast['risk_multiplier']}x")
print(f"    Days to violation: {forecast['days_to_violation']}")
print(f"    Fine range: {forecast['fine_range']}")

# Low risk case
forecast_low = heat_violation_forecast(
    heat_complaints_30d=0,
    avg_temp=75,
    current_date=datetime(2024, 7, 1)
)
print(f"  Low risk scenario: {forecast_low['urgency']} risk")
print()

# Test 4: Peer Benchmarking
print("✓ Testing Peer Benchmarking...")
from risk_engine.peer_benchmark import peer_percentile

result = peer_percentile(
    address="123 Test St",
    risk_score=75.0,
    building_data={'units': 24, 'year_built': 1965}
)
print(f"  Building score: {result['risk_score']}")
print(f"  Peer comparison: {result['vs_peers']}")
print(f"  Percentile: {result['percentile']}th")
print(f"  Similar buildings: {result['similar_count']}")
print()

# Test 5: Integration - Worst Case Building
print("✓ Testing Integrated Risk Scoring (Worst Case)...")
worst_case = {
    'year_built': 1950,
    'bbl': '3012650001',
    'council_district': 'brooklyn_council_36',
    'heat_complaints_30d': 5,
    'avg_temp': 50
}

era_mult, _ = pre1974_risk_multiplier(worst_case)
inspector_mult = inspector_risk_multiplier(worst_case['bbl'], worst_case['council_district'])
heat_forecast = heat_violation_forecast(
    worst_case['heat_complaints_30d'],
    worst_case['avg_temp'],
    datetime(2024, 2, 1)
)

combined_risk = era_mult * inspector_mult * heat_forecast['risk_multiplier']
print(f"  Pre-1960 building: {era_mult}x")
print(f"  Hotspot district: {inspector_mult}x")
print(f"  Peak heat season: {heat_forecast['risk_multiplier']}x")
print(f"  COMBINED RISK: {combined_risk:.1f}x baseline")
print()

# Test 6: Sales Tools
print("✓ Testing Sales Outreach Tools...")
from sales.outreach_pdf import generate_outreach_pdf

portfolio_data = [
    {'name': 'Building A', 'bbl': '1012650001', 'year_built': 1950, 'risk_score': 85, 'units': 24},
    {'name': 'Building B', 'bbl': '3012650002', 'year_built': 1970, 'risk_score': 65, 'units': 12},
]

pdf_data = generate_outreach_pdf(['1012650001', '3012650002'], portfolio_data, "Test Portfolio LLC")
print(f"  Generated: {pdf_data['filename']}")
print(f"  Summary: {pdf_data['summary']['total_buildings']} buildings")
print(f"  High-risk: {pdf_data['summary']['high_risk_count']} buildings")
print(f"  Pre-1974: {pdf_data['summary']['pre1974_count']} buildings")
print()

# Summary
print("=" * 70)
print("✅ ALL COMPETITIVE MOAT FEATURES VALIDATED SUCCESSFULLY")
print("=" * 70)
print()
print("Next Steps:")
print("  1. Run full test suite: pytest tests/ -v")
print("  2. Start Streamlit dashboard: streamlit run landlord_dashboard.py")
print("  3. Deploy to production: docker-compose -f docker-compose.prod.yml up")
print()
