# 🏢 ViolationSentinel: NYC Property Compliance Dashboard

> **Production-ready violation monitoring for landlords, property managers, and PropTech platforms**

## 🎯 Built for Property Management

ViolationSentinel provides comprehensive NYC property violation monitoring specifically designed for landlords and property managers. It tracks DOB, HPD, and 311 violations across your entire portfolio with real-time alerts and compliance reporting.

### 🚀 Landlord-Specific Features

- **DOB Violation Monitoring**: Department of Buildings violations tracking
- **HPD Violation Dashboard**: Housing Preservation Department violations
- **311 Complaint Tracking**: Tenant and neighbor complaints
- **Portfolio Management**: Monitor multiple properties in one dashboard
- **Risk Assessment**: Automated risk scoring for each property
- **Compliance Reporting**: Ready-to-share compliance reports
- **Real-time Alerts**: Get notified of new violations

## 📊 Property Management Workflow

| Task | Manual Process | With ViolationSentinel |
|------|----------------|------------------------|
| **Violation Checks** | Manual API queries per property | **Automated portfolio scanning** |
| **Compliance Tracking** | Spreadsheet management | **Centralized dashboard** |
| **Risk Assessment** | Subjective evaluation | **Data-driven risk scoring** |
| **Reporting** | Manual compilation | **Automated report generation** |
| **Alerts** | Manual monitoring | **Real-time notifications** |

## 🏢 Landlord & Property Manager Use Cases

1. **Portfolio Monitoring**: Track violations across all properties
2. **Due Diligence**: Pre-purchase violation checks
3. **Compliance Management**: Stay ahead of regulatory requirements
4. **Tenant Relations**: Proactively address complaint patterns
5. **Insurance Reporting**: Document compliance for carriers
6. **Property Valuation**: Understand violation impact on value

## 🛠️ Technology Stack

- **Data Sources**: NYC Open Data (SOCRATA API) - DOB, HPD, 311
- **Backend**: Python, FastAPI, PostgreSQL (optional)
- **Dashboard**: Streamlit for real-time monitoring
- **Alerts**: Email, SMS, or webhook integrations
- **Reporting**: PDF/Excel export for compliance documentation

## 🚀 Quick Start for Landlords

### Prerequisites
- Python 3.11+
- NYC Open Data App Token (optional, for higher limits)
- Property BBL numbers (10-digit identifiers)

### Installation
```bash
# Clone the repository
git clone https://github.com/NickAiNYC/ViolationSentinel.git
cd ViolationSentinel

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your NYC Open Data token
```

### Running the Dashboard
```bash
# Start the landlord dashboard
streamlit run landlord_dashboard.py

# Or use the CLI monitor
python monitor_cli.py
```

## 📁 Project Structure for Property Management

```
ViolationSentinel/
├── landlord_dashboard.py  # Main property management dashboard
├── dob_violations/        # DOB violation monitoring
│   └── dob_engine.py     # DOB violation fetching & analysis
├── fetch_final.py         # HPD/311 data fetching (production)
├── real_time_monitor.py   # Real-time monitoring service
├── dashboard.py           # Analytics dashboard
├── data/                  # Property data and samples
├── docs/                  # Documentation
└── requirements.txt       # Dependencies
```

## 🔧 Property Management API

### Monitor Single Property
```python
from dob_violations.dob_engine import DOBViolationMonitor

monitor = DOBViolationMonitor()
result = monitor.check_property("1012650001", "123 Main St Apartments")
print(f"Risk Level: {result['risk_level']}")
print(f"Violations: {result['summary']['total']}")
```

### Monitor Entire Portfolio
```python
from dob_violations.dob_engine import DOBViolationMonitor

portfolio = [
    {"name": "Building A", "bbl": "1012650001", "units": 24},
    {"name": "Building B", "bbl": "1012650002", "units": 12},
]

monitor = DOBViolationMonitor()
results = monitor.check_portfolio(portfolio)
print(f"Scanned {results['properties_checked']} properties")
print(f"Total violations: {results['portfolio_summary']['total']}")
```

## 📊 Landlord Workflow Example

1. **Add Properties** to your portfolio with BBL numbers
2. **Automated Scanning** checks DOB, HPD, and 311 databases
3. **Risk Assessment** calculates risk levels for each property
4. **Dashboard View** shows portfolio-wide compliance status
5. **Alerts & Reports** for proactive management

## 🏛️ NYC Compliance Coverage

- **DOB Violations**: Building code and permit violations
- **HPD Violations**: Housing maintenance code violations
- **311 Complaints**: Tenant and public complaints
- **Violation Classes**: A (non-hazardous), B (hazardous), C (immediately hazardous)
- **Resolution Tracking**: Open vs. resolved violation monitoring

## 🏗️ Related Project: Scope

For **general contractors and construction companies** needing construction site compliance and progress tracking, see our sister project:

**[Scope](https://github.com/NickAiNYC/Scope)** - Construction site compliance auditor

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 📈 Production Ready

This system currently monitors **15,973+ properties** with daily updates of HPD violations and 311 complaints. Ready for commercial licensing and PropTech platform integration.

## 🙏 Acknowledgments

- **NYC Open Data** for comprehensive violation databases
- **PropTech community** for workflow validation
- **Property managers** for real-world testing

---

*ViolationSentinel is maintained for the property management community.*
*Built for landlords, by data experts.*
