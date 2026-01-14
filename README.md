# 🛡️ ViolationSentinel – NYC Property Risk Intelligence

**Production-grade data pipeline + Monetization system for NYC property violation monitoring**

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Monetization](https://img.shields.io/badge/Monetization-$297/month-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Get Started in 10 Minutes

### Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API server
./start_api.sh

# 3. Access API documentation
# Open http://localhost:8000/docs

# 4. Deploy landing page
# Upload landing_page.html to Netlify/GitHub Pages
```

### First Customer in 2 Hours
1. **Deploy landing page** to Netlify (drag & drop)
2. **Send 5 emails** using templates in `docs/outreach_templates.md`
3. **Process payment** ($297 via PayPal/Venmo)
4. **Generate API key**: `python admin_tools.py add customer@email.com`

## 📊 What This Is

A complete system to monetize NYC property violation data:
- **Data Pipeline:** Fetches HPD violations + 311 complaints for 14,691+ NYC properties
- **API Server:** FastAPI with API key authentication and usage limits
- **Monetization:** $297/month Pro tier, $999/month Enterprise
- **Landing Page:** Professional sales page ready to deploy
- **Admin Tools:** Command-line tools for customer management

## 💰 Business Model

### Pricing
| Tier | Price | API Calls/Month | Target Customer |
|------|-------|----------------|-----------------|
| Free | $0 | 10 | Evaluation, testing |
| **Pro** | **$297** | **1,000** | **Real estate investors** |
| Enterprise | $999 | 10,000+ | Funds, property managers |

### Revenue Projection
- **Month 1:** 10 customers = $2,970 MRR
- **Month 3:** 30 customers = $8,910 MRR  
- **Month 6:** 50 customers = $14,850 MRR
- **Profit Margin:** ~85% (low infrastructure costs)

## 📁 Project Structure

```
ViolationSentinel/
├── simple_api.py           # FastAPI server with monetization
├── simple_monetization.py  # User & payment management
├── landing_page.html       # Sales landing page
├── admin_tools.py          # Admin commands for customer management
├── start_api.sh            # One-click startup script
├── fetch_final.py          # Data pipeline (fetches from NYC Open Data)
├── requirements.txt        # Python dependencies
├── LICENSE
├── .gitignore
├── data/                   # Sample data files
│   ├── nyc_compliance_demo_*.csv
│   └── nyc_compliance_full_*.csv
└── docs/                   # Documentation
    ├── MONETIZATION_README.md
    └── outreach_templates.md
```

## 🌐 API Endpoints

### Base URL: `http://localhost:8000`

### Authentication
All endpoints require `X-API-Key` header.

### Key Endpoints
- `GET /` - API status
- `GET /properties` - Filter properties by borough, risk score, etc.
- `GET /property/{bbl}` - Get specific property by BBL
- `GET /high-risk` - Get highest risk properties
- `GET /usage` - Check your API usage

## 🛠️ Admin Commands

```bash
# List all users
python admin_tools.py list

# Add new customer
python admin_tools.py add customer@email.com pro

# Upgrade customer tier
python admin_tools.py upgrade customer@email.com enterprise

# Reset usage counter
python admin_tools.py reset customer@email.com

# Show business stats
python admin_tools.py stats
```

## 🎯 Customer Acquisition

### Target Audience
1. Real estate investors in NYC
2. Property management companies
3. Hedge funds (real estate division)
4. Insurance companies
5. Law firms (real estate practice)

### Outreach Strategy
- **Cold Email:** Use templates in `docs/outreach_templates.md`
- **LinkedIn:** Connect with real estate professionals
- **Referrals:** Offer $500 referral bonus
- **Content:** Blog posts about NYC property risks

## 🔄 Development Roadmap

### Phase 1: Manual System (Now)
- [x] API with key authentication
- [x] Landing page
- [x] Admin tools
- [ ] First 10 customers

### Phase 2: Automation (Month 2)
- [ ] Stripe integration
- [ ] Self-service signup
- [ ] Admin dashboard
- [ ] Automated billing

### Phase 3: Scale (Month 3+)
- [ ] Mobile app
- [ ] Additional data sources (DOB, ECB)
- [ ] Team features
- [ ] Multi-city expansion

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 📞 Support

- **Sales:** sales@thrivai.com
- **API Docs:** http://localhost:8000/docs (when server running)
- **Business Questions:** Open an issue

## 🚀 Immediate Next Steps

1. **Start API:** `./start_api.sh`
2. **Deploy landing page:** Upload to Netlify
3. **Send emails:** Use templates in `docs/outreach_templates.md`
4. **Get first customer:** Process manual payment

**Your first $297 is waiting. Launch now.**
