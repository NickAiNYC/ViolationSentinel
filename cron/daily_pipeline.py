"""
Daily Data Pipeline
Fetches NYC Open Data and calculates risk scores with email alerts
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# NYC Open Data endpoints
HPD_VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
DOB_VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/3h2n-5cm9.json"
COMPLAINTS_311_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"


class DataPipeline:
    """Fetch and process NYC violation data with email alerts"""
    
    def __init__(self, app_token: str = None, sendgrid_api_key: str = None):
        self.app_token = app_token or os.getenv("NYC_OPEN_DATA_TOKEN")
        self.sendgrid_api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY")
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
    
    def calculate_metrics(self, bbl: str, property_name: str = "") -> Dict:
        """
        Calculate risk metrics for a property
        
        Args:
            bbl: NYC Building Block Lot identifier
            property_name: Property name for alerts
            
        Returns:
            Dictionary of risk metrics including litigation flag
        """
        print(f"Processing {bbl} ({property_name})...")
        
        # Fetch data
        hpd_violations = self.fetch_hpd_violations(bbl)
        dob_violations = self.fetch_dob_violations(bbl)
        complaints_311 = self.fetch_311_complaints(bbl, days_back=7)
        
        # Calculate metrics
        metrics = {
            "bbl": bbl,
            "property_name": property_name,
            "class_c_count": 0,
            "heat_complaints_7d": 0,
            "open_violations_90d": 0,
            "complaint_311_spike": 0,
            "litigation_flag": False,
            "total_violations": 0,
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
        
        # Count open violations > 90 days and detect litigation
        ninety_days_ago = datetime.now() - timedelta(days=90)
        litigation_keywords = ["litigat", "lawsuit", "court", "legal action"]
        
        for viol in hpd_violations + dob_violations:
            issue_date_str = viol.get("inspectiondate") or viol.get("issue_date")
            status = viol.get("violationstatus") or viol.get("status")
            description = str(viol.get("violationdescription", "")).lower()
            
            # Check litigation flag
            if any(kw in description for kw in litigation_keywords):
                metrics["litigation_flag"] = True
            
            if issue_date_str and status != "Close":
                try:
                    issue_date = datetime.strptime(issue_date_str[:10], "%Y-%m-%d")
                    if issue_date < ninety_days_ago:
                        metrics["open_violations_90d"] += 1
                        days_open = (datetime.now() - issue_date).days
                        metrics["days_open_max"] = max(metrics["days_open_max"], days_open)
                except:
                    pass
        
        # Total violations
        metrics["total_violations"] = len([v for v in hpd_violations + dob_violations 
                                          if v.get("violationstatus", "") != "Close"])
        
        # Detect 311 complaint spike (more than 3 in last 7 days)
        if len(complaints_311) > 3:
            metrics["complaint_311_spike"] = 1
        
        return metrics
    
    def process_portfolio(
        self, 
        properties: List[Dict[str, str]], 
        output_file: str = "data/portfolio_violations.json",
        alert_email: Optional[str] = None
    ) -> List[Dict]:
        """
        Process entire portfolio and save results with email alerts
        
        Args:
            properties: List of dicts with 'bbl' and 'name' keys
            output_file: Path to save results
            alert_email: Email address for high-risk alerts
            
        Returns:
            List of property metrics dictionaries
        """
        print(f"Processing {len(properties)} properties...")
        
        results = []
        for prop in properties:
            bbl = prop.get('bbl', '')
            name = prop.get('name', bbl)
            try:
                metrics = self.calculate_metrics(bbl, name)
                results.append(metrics)
            except Exception as e:
                print(f"Error processing {bbl} ({name}): {e}")
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
                print(f"  - BBL {prop['bbl']} ({prop['property_name']}): Risk Score {score}")
            
            # Send email alert if configured
            if alert_email and self.sendgrid_api_key:
                self._send_alert_email(high_risk, alert_email)
        
        return results
    
    def _send_alert_email(self, high_risk_properties: List[Dict], to_email: str):
        """
        Send email alert for high-risk properties using SendGrid
        
        Args:
            high_risk_properties: List of high-risk property metrics
            to_email: Recipient email address
        """
        try:
            # Build email content
            subject = f"⚠️ ViolationSentinel Alert: {len(high_risk_properties)} High-Risk Properties"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background: #DC2626; color: white; padding: 20px; }}
                    .property {{ border: 1px solid #E5E7EB; padding: 15px; margin: 10px 0; }}
                    .critical {{ background: #FEE2E2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🚨 ViolationSentinel High-Risk Alert</h2>
                    <p>{len(high_risk_properties)} properties require immediate attention</p>
                </div>
                <div style="padding: 20px;">
            """
            
            for prop in high_risk_properties:
                score = self._calculate_risk_score(prop)
                html_content += f"""
                <div class="property {'critical' if score >= 80 else ''}">
                    <h3>{prop['property_name']} (BBL: {prop['bbl']})</h3>
                    <p><strong>Risk Score:</strong> {score}/100</p>
                    <p><strong>Class C Violations:</strong> {prop['class_c_count']}</p>
                    <p><strong>Heat Complaints (7d):</strong> {prop['heat_complaints_7d']}</p>
                    <p><strong>Open Violations >90d:</strong> {prop['open_violations_90d']}</p>
                    {f"<p><strong>⚠️ LITIGATION FLAG</strong></p>" if prop.get('litigation_flag') else ""}
                </div>
                """
            
            html_content += """
                </div>
                <div style="padding: 20px; background: #F3F4F6; text-align: center;">
                    <p>Log in to your ViolationSentinel dashboard for detailed recommendations</p>
                </div>
            </body>
            </html>
            """
            
            message = Mail(
                from_email='alerts@violationsentinel.com',
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            
            if response.status_code == 202:
                print(f"✅ Alert email sent to {to_email}")
            else:
                print(f"⚠️  Email send status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error sending alert email: {e}")
            print("   (Continuing pipeline execution...)")
    
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
    
    # Load portfolio (in production, fetch from Supabase)
    portfolio_properties = [
        {"bbl": "1000010001", "name": "Building A"},
        {"bbl": "2000020002", "name": "Building B"},
        {"bbl": "3000030003", "name": "Building C"}
    ]
    
    # Get alert email from environment
    alert_email = os.getenv("ALERT_EMAIL", "alerts@example.com")
    
    # Process portfolio
    results = pipeline.process_portfolio(
        properties=portfolio_properties,
        alert_email=alert_email
    )
    
    print("-" * 50)
    print(f"Completed at: {datetime.now().isoformat()}")
    print(f"Processed {len(results)} properties")


if __name__ == "__main__":
    main()
