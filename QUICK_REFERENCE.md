# ViolationSentinel - Quick Reference Guide

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run tests
pytest tests/ -v

# 3. Validate features
python validate_features.py

# 4. Start dashboard
streamlit run landlord_dashboard.py
```

## 📊 Using Competitive Moat Features

### Pre-1974 Risk Analysis

```python
from risk_engine.pre1974_multiplier import pre1974_risk_multiplier, get_building_era_risk

# Simple risk multiplier
multiplier, explanation = pre1974_risk_multiplier({'year_built': 1965})
print(f"Risk: {multiplier}x - {explanation}")
# Output: Risk: 2.5x - Rent-stabilized era (elevated risk)

# Detailed risk assessment
risk = get_building_era_risk(1950)
print(f"Era: {risk['era']}")
print(f"Multiplier: {risk['multiplier']}x")
print(f"Risk Factors: {risk['risk_factors']}")
print(f"Actions: {risk['action_items']}")
```

### Inspector Beat Patterns

```python
from risk_engine.inspector_patterns import inspector_risk_multiplier, get_district_hotspot

# Get enforcement multiplier
mult = inspector_risk_multiplier('3012650001', 'brooklyn_council_36')
print(f"Enforcement: {mult}x")  # 2.3x in hotspot

# Get hotspot details
hotspot = get_district_hotspot('brooklyn_council_36')
print(f"Risk Level: {hotspot['risk_level']}")
print(f"Actions: {hotspot['action_items']}")
```

### Winter Heat Season Forecast

```python
from risk_engine.seasonal_heat_model import heat_violation_forecast, is_heat_season
from datetime import datetime

# Check if in heat season
if is_heat_season():
    print("Currently in heat season (Oct 1 - May 31)")

# Forecast heat violation risk
forecast = heat_violation_forecast(
    heat_complaints_30d=5,
    avg_temp=50,
    current_date=datetime(2024, 2, 1)
)
print(f"Urgency: {forecast['urgency']}")
print(f"Risk: {forecast['risk_multiplier']}x")
print(f"Days to violation: {forecast['days_to_violation']}")
print(f"Action: {forecast['action']}")
```

### Peer Benchmarking

```python
from risk_engine.peer_benchmark import peer_percentile

# Compare to peers
result = peer_percentile(
    address="123 Main St",
    risk_score=75.0,
    building_data={'units': 24, 'year_built': 1965, 'borough': 'Brooklyn'}
)
print(f"Your score: {result['risk_score']}")
print(f"Comparison: {result['vs_peers']}")
print(f"Percentile: {result['percentile']}th")
print(f"Similar buildings: {result['similar_count']}")
```

### Sales Outreach PDF

```python
from sales.outreach_pdf import generate_outreach_pdf, email_template_for_outreach

# Generate outreach PDF
portfolio_data = [
    {'name': 'Building A', 'bbl': '1012650001', 'year_built': 1950, 
     'risk_score': 85, 'units': 24},
    {'name': 'Building B', 'bbl': '3012650002', 'year_built': 1970, 
     'risk_score': 65, 'units': 12},
]

pdf = generate_outreach_pdf(
    portfolio_bbls=['1012650001', '3012650002'],
    portfolio_data=portfolio_data,
    company_name="ABC Properties LLC"
)

# Save to file
with open(pdf['filename'], 'w') as f:
    f.write(pdf['content'])

# Generate email template
email = email_template_for_outreach(pdf['summary'], "John Doe")
print(email)
```

## 🎨 Streamlit Components

### Pre-1974 Warning Banners

```python
import streamlit as st
import pandas as pd
from vs_components.components.pre1974_banner import show_pre1974_banner, show_pre1974_stats

# Show warning banners
buildings_df = pd.DataFrame([
    {'name': 'Old Building', 'year_built': 1950, 'risk_score': 85},
    {'name': 'Modern Building', 'year_built': 2000, 'risk_score': 45}
])

show_pre1974_banner(buildings_df)

# Show portfolio stats
from risk_engine.pre1974_multiplier import calculate_portfolio_pre1974_stats
stats = calculate_portfolio_pre1974_stats(buildings_df.to_dict('records'))
show_pre1974_stats(stats)
```

### Heat Season Alerts

```python
from vs_components.components.pre1974_banner import show_winter_heat_alert

buildings_with_complaints = [
    {'name': 'Building A', 'heat_complaints_30d': 5, 'year_built': 1950},
    {'name': 'Building B', 'heat_complaints_30d': 3, 'year_built': 1970}
]

show_winter_heat_alert(buildings_with_complaints)
```

### Inspector Hotspot Alerts

```python
from vs_components.components.pre1974_banner import show_inspector_hotspot_alert

hotspot_buildings = [
    {'name': 'Building A', 'council_district': 'brooklyn_council_36', 'inspector_multiplier': 2.3},
    {'name': 'Building B', 'council_district': 'bronx_council_15', 'inspector_multiplier': 2.2}
]

show_inspector_hotspot_alert(hotspot_buildings)
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_pre1974_risk.py -v

# Run with coverage
pytest tests/ --cov=risk_engine --cov-report=html

# Quick validation
python validate_features.py
```

## 🐳 Docker Deployment

```bash
# Development (basic)
docker-compose up

# Production (with PostgreSQL + Redis)
docker-compose -f docker-compose.prod.yml --profile production up

# Environment variables
export NYC_DATA_APP_TOKEN="your_token_here"
export ENABLE_PRE1974_ANALYSIS=true
export ENABLE_INSPECTOR_PATTERNS=true
export ENABLE_HEAT_FORECAST=true
export ENABLE_PEER_BENCHMARK=true
```

## 📈 Real-World Example

```python
# Complete risk analysis for a building
from risk_engine.pre1974_multiplier import pre1974_risk_multiplier
from risk_engine.inspector_patterns import inspector_risk_multiplier
from risk_engine.seasonal_heat_model import heat_violation_forecast
from datetime import datetime

building = {
    'name': '123 Main Street Apartments',
    'bbl': '3012650001',
    'year_built': 1950,
    'council_district': 'brooklyn_council_36',
    'units': 24,
    'heat_complaints_30d': 5,
    'avg_temp': 50
}

# Calculate all risk factors
era_mult, era_exp = pre1974_risk_multiplier(building)
inspector_mult = inspector_risk_multiplier(building['bbl'], building['council_district'])
heat_forecast = heat_violation_forecast(
    building['heat_complaints_30d'],
    building['avg_temp'],
    datetime(2024, 2, 1)
)

# Combined risk
combined_risk = era_mult * inspector_mult * heat_forecast['risk_multiplier']

print(f"Building: {building['name']}")
print(f"Built: {building['year_built']}")
print(f"\nRisk Factors:")
print(f"  Era Risk: {era_mult}x ({era_exp})")
print(f"  Inspector: {inspector_mult}x (hotspot district)")
print(f"  Heat Season: {heat_forecast['risk_multiplier']}x ({heat_forecast['urgency']})")
print(f"\n🚨 COMBINED RISK: {combined_risk:.1f}x baseline")
print(f"\nAction Required: {heat_forecast['action']}")
```

## 💡 Tips & Best Practices

1. **Always include building year** - Critical for pre-1974 analysis
2. **Update district data quarterly** - Inspector patterns change
3. **Monitor heat season closely** - Oct-May, especially Jan-Mar
4. **Use peer benchmarking for sales** - Instant credibility
5. **Generate PDFs for due diligence** - Professional reports
6. **Test features regularly** - Run `validate_features.py`

## 🔗 Key Files

- `risk_engine/` - Core risk analysis modules
- `vs_components/` - Streamlit UI components
- `sales/` - Outreach and sales tools
- `tests/` - Comprehensive test suite
- `docs/COMPETITIVE_MOAT.md` - Full documentation
- `validate_features.py` - Quick validation

## 📞 Need Help?

1. Check `docs/COMPETITIVE_MOAT.md` for detailed explanations
2. Run `python validate_features.py` to verify setup
3. Run `pytest tests/ -v` to ensure everything works
4. Review examples in this guide

---

**ViolationSentinel - NYC Open Data Weaponized for Landlords**
