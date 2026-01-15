# ViolationSentinel V1 - Complete Deployable Product

> NYC Property Compliance Risk Dashboard for Landlords & Property Managers

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What is ViolationSentinel?

ViolationSentinel helps NYC landlords and property managers **prevent $5k+ fines** by providing early warning of HPD Class C violations and heat complaints.

**Key Value**: Upload your building portfolio CSV → Get instant risk scores, priority alerts, and fine exposure estimates.

## 🚀 Quick Start

### Run Locally

```bash
# Install dependencies
pip install -r requirements-v1.txt

# Start API server
python backend/v1/api.py &

# Start Streamlit dashboard
streamlit run streamlit/app.py
```

Visit: `http://localhost:8501`

### Deploy to Production

**Streamlit Cloud**:
1. Push repo to GitHub
2. Connect to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Deploy `streamlit/app.py`

**API (Docker)**:
```bash
docker-compose -f docker-compose-v1.yml up -d
```

## 📁 File Structure

```
streamlit/
  app.py                 # Main dashboard UI
backend/v1/
  api.py                 # FastAPI server
  risk_engine.py         # Deterministic risk scoring
cron/
  daily_pipeline.py      # NYC Open Data ingestion
stripe/
  webhook.py             # Payment webhooks
requirements-v1.txt      # Dependencies
docker-compose-v1.yml    # Container orchestration
```

## 🎨 Product Features

### 1. Dashboard (Streamlit)
- CSV upload: `bbl,name,units,address`
- Risk heatmap visualization
- Top 5 highest-risk properties
- Priority levels: IMMEDIATE / URGENT / NORMAL
- Status colors: 🔴 RED / 🟡 YELLOW / 🟢 GREEN
- Fine exposure estimates
- Export: CSV, PDF (coming soon)

### 2. Risk Scoring Engine
**Deterministic Algorithm**:
- Class C violations: **40 pts each**
- Heat complaints (7d): **30 pts each**
- Open violations >90d: **20 pts each**
- 311 complaint spike: **10 pts**

**Output**:
```json
{
  "risk_score": 85,
  "priority": "IMMEDIATE",
  "fine_risk_estimate": "$12,350",
  "status_color": "RED"
}
```

### 3. Data Pipeline
- Fetches HPD, DOB, 311 data daily (2 AM EST)
- Normalizes by BBL
- Calculates: `days_open`, `class_c_count`, `heat_complaints_7d`
- Stores in JSON (use Supabase in production)
- Triggers alerts if `risk_score > 70`

### 4. Monetization
**Free Plan**: 3 buildings, daily updates
**Pro Plan**: $99/mo, unlimited buildings, real-time alerts

Stripe Checkout integration:
- Payment webhooks → Upgrade/downgrade users
- Server-side tier enforcement

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | Supabase (Postgres) or JSON |
| Payments | Stripe Checkout |
| Data | NYC Open Data API |
| Deploy | Streamlit Cloud + Docker |

## 📊 NYC Open Data Sources

- **HPD Violations**: `wvxf-dwi5`
- **DOB Violations**: `3h2n-5cm9`
- **311 Complaints**: `erm2-nwe9`

## 🔑 Environment Variables

```bash
# API
API_URL=http://localhost:8000

# NYC Open Data
NYC_OPEN_DATA_TOKEN=your_app_token_here

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# Database (optional)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_key_here
```

## 📝 Sample CSV Format

```csv
bbl,name,units,address
1000010001,Building A,24,123 Main St Manhattan
2000020002,Building B,48,456 Oak Ave Brooklyn
3000030003,Building C,12,789 Elm St Queens
```

## 🎬 Usage Flow

1. **Upload Portfolio**: Landlord uploads building list CSV
2. **Risk Calculation**: System fetches violations and calculates risk scores
3. **Dashboard View**: See color-coded priority levels and fine estimates
4. **Take Action**: Address Class C violations and heat complaints ASAP
5. **Export Reports**: Download CSV/PDF for insurance or lender requirements

## 🚨 Alert Logic

System triggers alerts when:
- `risk_score >= 80` (IMMEDIATE priority)
- New Class C violation detected
- Heat complaint during heating season (Oct 1 - May 31)

## 💰 Stripe Integration

### Checkout Flow
1. User clicks "Upgrade to Pro"
2. Redirects to Stripe Checkout
3. Webhook updates user tier
4. Buildings limit increased

### Plans
```python
FREE_PLAN = {
    "buildings": 3,
    "updates": "daily"
}

PRO_PLAN = {
    "price": "$99/mo",
    "buildings": "unlimited",
    "updates": "real-time",
    "support": "priority"
}
```

## 📈 Roadmap

**V1 (Current)**:
- ✅ Streamlit dashboard
- ✅ CSV upload
- ✅ Deterministic risk scoring
- ✅ Stripe payments
- ✅ Daily data pipeline

**V2 (Next)**:
- [ ] Supabase integration
- [ ] Email/SMS alerts
- [ ] PDF export
- [ ] Mobile responsive
- [ ] Multi-user accounts

**V3 (Future)**:
- [ ] ML-powered forecasting
- [ ] Integration with Yardi/AppFolio
- [ ] White-label offering
- [ ] API for insurers/lenders

## 🧪 Testing

```bash
# Test API
python backend/v1/api.py &
curl http://localhost:8000/health

# Test risk engine
python -c "from backend.v1.risk_engine import risk_engine; print(risk_engine.calculate_risk(class_c_count=2))"

# Test pipeline
python cron/daily_pipeline.py
```

## 📧 Support

Questions? Email: support@violationsentinel.com

## 📄 License

MIT License - see LICENSE file

---

**Built with ❤️ for NYC landlords and property managers**

*Prevent fines. Protect your portfolio. Stay compliant.*
