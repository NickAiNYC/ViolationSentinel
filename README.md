# ViolationSentinel – NYC Property Compliance Intelligence

**Production-grade data pipeline delivering daily property risk intelligence from NYC's official HPD violations and 311 complaint systems.**

---

## 📊 Pipeline Dashboard – Last Run: Dec 29, 2025 (90-day window)

| Metric | Value | Change |
|--------|-------|--------|
| **Total Properties Monitored** | 14,691 | +2.3% |
| **Properties with Violations** | 7,242 | +1.8% |
| **Properties with Class B Violations** | 4,937 | +3.1% |
| **Properties with Heat/Plumbing Complaints** | 13,200 | +2.5% |
| **Average Risk Score** | 9.67 | -0.4 |

---

## 🎯 What This Delivers

A commercial-grade data pipeline that automatically:

1. **Fetches daily updates** from NYC's official Socrata APIs (no scraping)
2. **Joins HPD violations** with filtered 311 heat/plumbing complaints on BBL
3. **Aggregates & scores** at property level with composite risk algorithm
4. **Exports ready-to-use formats** for immediate integration

**Data Sources:**
- NYC HPD Violations (`wvxf-dwi5`) – Class A/B/C violations
- NYC 311 Complaints (`erm2-nwe9`) – Heat/hot water & plumbing issues
- Rolling 90-day window (configurable)

---

## 📈 Latest Run Highlights

**Top 3 Highest-Risk Properties (Anonymized):**

1. **Risk Score: 405.0**
   - Class B Violations: 29
   - 311 Complaints: 209
   - Total Violations: 67

2. **Risk Score: 364.5**
   - Class B Violations: 11
   - 311 Complaints: 215
   - Total Violations: 40

3. **Risk Score: 345.0**
   - Class B Violations: 1
   - 311 Complaints: 228
   - Total Violations: 2

---

## 🚀 Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
# or manually install:
pip install pandas requests python-dotenv
