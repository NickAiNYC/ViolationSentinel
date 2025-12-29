# ViolationSentinel – NYC Property Compliance Intelligence

Production-grade daily data pipeline delivering actionable NYC property risk signals from official HPD violations and 311 complaint systems.

![Status](https://img.shields.io/badge/Status-MVP%20Live-brightgreen?style=flat-square)
![Last Run](https://img.shields.io/badge/Last%20Run-Dec%2029%2C%202025-blue?style=flat-square)
![Properties](https://img.shields.io/badge/Properties-14%2C691+-yellow?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## Pipeline Snapshot – Last Run: Dec 29, 2025 (90-day window)

| Metric                                   | Value     | Change |
|------------------------------------------|-----------|--------|
| Total Properties Monitored               | 14,691    | —      |
| Properties with Violations               | 7,242     | —      |
| Properties with Class B Violations       | 4,937     | —      |
| Properties with Heat/Plumbing Complaints | 13,200    | —      |
| Average Risk Score                       | 9.67      | —      |
| Maximum Risk Score                       | 405.0     | —      |

## What This Delivers

A clean, reliable, commercial-grade data product that:

1. Fetches daily updates from official NYC Open Data APIs (no scraping)  
2. Joins HPD Violations (wvxf-dwi5) with filtered 311 Complaints (erm2-nwe9) on BBL  
3. Aggregates per property: total violations, Class B count, heat/plumbing complaint count  
4. Calculates a simple composite risk score (customizable)  
5. Exports ready-to-use files: full dataset, top-100 client sample, anonymized demo

Data Coverage: Rolling 90-day window (configurable)  
Refresh: Daily automated (cron-ready)

## Latest Run Highlights

Top 3 Highest-Risk Properties (anonymized):

1. Risk Score: 405.0  
   - Class B Violations: 29  
   - 311 Heat/Plumbing Complaints: 209  
   - Total Violations: 67  

2. Risk Score: 364.5  
   - Class B Violations: 11  
   - 311 Heat/Plumbing Complaints: 215  
   - Total Violations: 40  

3. Risk Score: 345.0  
   - Class B Violations: 1  
   - 311 Heat/Plumbing Complaints: 228  
   - Total Violations: 2  

## Quick Start

### Prerequisites
pip install -r requirements.txt
# or manually:
pip install pandas requests python-dotenv

### Configuration
Create .env file in project root:

SOCRATA_APP_TOKEN=your_token_here

Get free token: https://dev.socrata.com → sign in → Developer Settings → App Tokens

### Run the pipeline
python fetch_final.py

Generated files (timestamped):
- nyc_compliance_full_*.csv — full dataset (~14k+ properties)  
- nyc_compliance_sample_*.json — top 100 highest-risk (client-ready)  
- nyc_compliance_demo_*.csv — anonymized top 50 (for demos/presentations)

## Commercial Licensing & Pricing (2025 Pilot Rates)

Tier          | Monthly Price | Properties Limit | Features                              | Best For
--------------|---------------|------------------|---------------------------------------|---------------------------------------
Starter       | $750          | ≤10,000          | Daily CSV/JSON, basic support         | Early-stage PropTech, nonprofits
Professional  | $1,500        | Unlimited        | API endpoint, SLA, priority support   | Mid-size platforms & analytics firms
Enterprise    | Custom        | Unlimited        | On-prem, white-label, historical data | Large insurers, enterprise SaaS

Free 30-day pilot available — includes custom sample feed and support.

Use Cases
- Property management SaaS → real-time compliance alerts
- Landlord fintech → tenant & property risk scoring
- Real estate analytics → distressed asset screening
- Nonprofits → enforcement monitoring & advocacy
- Insurance → property risk underwriting

Ready to integrate?
Email [your-email] with subject: "PILOT – NYC Compliance Feed"
We'll send a free trial feed + support setup within 24 hours.

## Tech Stack
- Python 3.10+
- pandas (aggregation & cleaning)
- requests (API calls)
- python-dotenv (secure token management)

## Legal & Disclaimer
Data sourced from official NYC Open Data APIs (public domain).  
This pipeline is provided as-is. Not legal, financial, or investment advice.  
Use for informational/business intelligence purposes only.

MIT License – see LICENSE file.

Questions, pilots, partnerships, or customizations?  
Open an issue or contact the maintainer.

Built by NickAiNYC | December 2025
