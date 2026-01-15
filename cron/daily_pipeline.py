"""
Daily Data Pipeline
Fetches NYC Open Data and calculates risk scores
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import json

# NYC Open Data endpoints
HPD_VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
DOB_VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/3h2n-5cm9.json"
COMPLAINTS_311_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"


class DataPipeline:
    """Fetch and process NYC violation data"""
    
    def __init__(self, app_token: str = None):
        self.app_token = app_token or os.getenv("NYC_OPEN_DATA_TOKEN")
        self.headers = {}
        if self.app_token:
            self.headers["X-App-Token"] = self.app_token
    
    def fetch_hpd_violations(self, bbl: str, limit: int = 1000) -> List[Dict]:
        """Fetch HPD violations for a property"""
        try:
            params = {
                "$where": f"bbl='{bbl}'",
                "$limit": limit,
                "$order": "inspectiondate DESC"
            }
            response = requests.get(HPD_VIOLATIONS_URL, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching HPD violations for {bbl}: {e}")
            return []
    
    def fetch_dob_violations(self, bbl: str, limit: int = 1000) -> List[Dict]:
        """Fetch DOB violations for a property"""
        try:
            params = {
                "$where": f"bin='{bbl}'",  # Note: May need BBL->BIN conversion
                "$limit": limit,
                "$order": "issue_date DESC"
            }
            response = requests.get(DOB_VIOLATIONS_URL, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching DOB violations for {bbl}: {e}")
            return []
    
    def fetch_311_complaints(self, bbl: str, days_back: int = 7, limit: int = 1000) -> List[Dict]:
        """Fetch 311 complaints for a property"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            params = {
                "$where": f"bbl='{bbl}' AND created_date >= '{cutoff_date}'",
                "$limit": limit,
                "$order": "created_date DESC"
            }
            response = requests.get(COMPLAINTS_311_URL, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching 311 complaints for {bbl}: {e}")
            return []
    
    def calculate_metrics(self, bbl: str) -> Dict:
        """Calculate risk metrics for a property"""
        print(f"Processing {bbl}...")
        
        # Fetch data
        hpd_violations = self.fetch_hpd_violations(bbl)
        dob_violations = self.fetch_dob_violations(bbl)
        complaints_311 = self.fetch_311_complaints(bbl, days_back=7)
        
        # Calculate metrics
        metrics = {
            "bbl": bbl,
            "class_c_count": 0,
            "heat_complaints_7d": 0,
            "open_violations_90d": 0,
            "complaint_311_spike": 0,
            "days_open_max": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        # Count Class C violations (HPD)
        for viol in hpd_violations:
            if viol.get("class") == "C" and viol.get("violationstatus") != "Close":
                metrics["class_c_count"] += 1
        
        # Count heat complaints in last 7 days
        heat_keywords = ["heat", "hot water", "heating", "no heat"]
        for complaint in complaints_311:
            complaint_type = complaint.get("complaint_type", "").lower()
            if any(kw in complaint_type for kw in heat_keywords):
                metrics["heat_complaints_7d"] += 1
        
        # Count open violations > 90 days
        ninety_days_ago = datetime.now() - timedelta(days=90)
        for viol in hpd_violations + dob_violations:
            issue_date_str = viol.get("inspectiondate") or viol.get("issue_date")
            status = viol.get("violationstatus") or viol.get("status")
            
            if issue_date_str and status != "Close":
                try:
                    issue_date = datetime.strptime(issue_date_str[:10], "%Y-%m-%d")
                    if issue_date < ninety_days_ago:
                        metrics["open_violations_90d"] += 1
                        days_open = (datetime.now() - issue_date).days
                        metrics["days_open_max"] = max(metrics["days_open_max"], days_open)
                except:
                    pass
        
        # Detect 311 complaint spike (more than 3 in last 7 days)
        if len(complaints_311) > 3:
            metrics["complaint_311_spike"] = 1
        
        return metrics
    
    def process_portfolio(self, bbls: List[str], output_file: str = "data/portfolio_violations.json"):
        """Process entire portfolio and save results"""
        print(f"Processing {len(bbls)} properties...")
        
        results = []
        for bbl in bbls:
            try:
                metrics = self.calculate_metrics(bbl)
                results.append(metrics)
            except Exception as e:
                print(f"Error processing {bbl}: {e}")
                continue
        
        # Save to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Saved {len(results)} results to {output_file}")
        
        # Check for high-risk properties and trigger alerts
        high_risk = [r for r in results if self._calculate_risk_score(r) > 70]
        if high_risk:
            print(f"\n⚠️  {len(high_risk)} HIGH RISK PROPERTIES DETECTED:")
            for prop in high_risk:
                score = self._calculate_risk_score(prop)
                print(f"  - BBL {prop['bbl']}: Risk Score {score}")
                # TODO: Trigger alert via email/SMS
        
        return results
    
    def _calculate_risk_score(self, metrics: Dict) -> int:
        """Calculate risk score from metrics"""
        score = 0
        score += metrics.get("class_c_count", 0) * 40
        score += metrics.get("heat_complaints_7d", 0) * 30
        score += metrics.get("open_violations_90d", 0) * 20
        score += metrics.get("complaint_311_spike", 0) * 10
        return min(100, score)


def main():
    """Main pipeline execution"""
    print("ViolationSentinel Daily Pipeline")
    print(f"Started at: {datetime.now().isoformat()}")
    print("-" * 50)
    
    # Initialize pipeline
    pipeline = DataPipeline()
    
    # Load portfolio BBLs (in production, fetch from Supabase)
    portfolio_bbls = [
        "1000010001",  # Example BBLs
        "2000020002",
        "3000030003"
    ]
    
    # Process portfolio
    results = pipeline.process_portfolio(portfolio_bbls)
    
    print("-" * 50)
    print(f"Completed at: {datetime.now().isoformat()}")
    print(f"Processed {len(results)} properties")


if __name__ == "__main__":
    main()
