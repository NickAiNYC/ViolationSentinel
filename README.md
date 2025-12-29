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

**Data Coverage**: Rolling 90-day window (configurable)  
**Refresh**: Daily automated (cron-ready)

## Latest Run Highlights

**Top 3 Highest-Risk Properties** (anonymized):

1. **Risk Score: 405.0**  
   - Class B Violations: 29  
   - 311 Heat/Plumbing Complaints: 209  
   - Total Violations: 67  

2. **Risk Score: 364.5**  
   - Class B Violations: 11  
   - 311 Heat/Plumbing Complaints: 215  
   - Total Violations: 40  

3. **Risk Score: 345.0**  
   - Class B Violations: 1  
   - 311 Heat/Plumbing Complaints: 228  
   - Total Violations: 2  

## Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
# or manually:
pip install pandas requests python-dotenv
