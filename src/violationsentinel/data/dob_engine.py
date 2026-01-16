"""
NYC DOB Violation Engine for Property Managers
Fetches Department of Buildings violations for landlord property management.
"""

import requests
import os
from typing import List, Dict
from datetime import datetime


def fetch_dob_violations(bbl: str, limit: int = 50) -> List[Dict]:
    """
    Fetch DOB violations for a property by BBL (Borough-Block-Lot).
    
    Args:
        bbl: Property BBL number (10 digits)
        limit: Maximum number of violations to return
        
    Returns:
        List of DOB violation records
    """
    if not bbl or len(bbl) != 10:
        return []
    
    endpoint = "https://data.cityofnewyork.us/resource/6bgk-3dad.json"
    app_token = os.getenv("NYC_DATA_APP_TOKEN")
    
    headers = {"X-App-Token": app_token} if app_token else {}
    params = {
        "bbl": str(bbl),
        "$limit": limit,
        "$order": "issue_date DESC",
        "$select": "violation_number,violation_type,issue_date,violation_category,respondent_name,disposition_date,disposition,penalty_imposed"
    }

    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # Format dates and clean data
            for item in data:
                if 'issue_date' in item:
                    item['issue_date'] = item['issue_date'][:10]
                if 'disposition_date' in item:
                    item['disposition_date'] = item['disposition_date'][:10]
                if 'respondent_name' in item:
                    item['respondent_name'] = str(item['respondent_name']).title()
                
                # Add violation class based on category
                item['violation_class'] = classify_dob_violation(item.get('violation_category', ''))
                
            return data
        return []
    except Exception as e:
        print(f"DOB API Error: {e}")
        return []


def classify_dob_violation(category: str) -> str:
    """Classify DOB violation into A, B, or C class."""
    category = str(category).upper()
    
    # Class C - Immediately Hazardous
    if any(keyword in category for keyword in ["IMMEDIATELY HAZARDOUS", "EMERGENCY", "COLLAPSE", "STRUCTURAL"]):
        return "Class C"
    
    # Class B - Hazardous
    if any(keyword in category for keyword in ["HAZARDOUS", "SAFETY", "FIRE", "ELECTRICAL", "PLUMBING"]):
        return "Class B"
    
    # Class A - Non-Hazardous (default)
    return "Class A"


def get_violation_summary(violations: List[Dict]) -> Dict:
    """Generate summary statistics for DOB violations."""
    if not violations:
        return {
            "total": 0,
            "by_class": {"Class A": 0, "Class B": 0, "Class C": 0},
            "open": 0,
            "resolved": 0,
            "avg_days_open": 0
        }
    
    now = datetime.now()
    open_count = 0
    resolved_count = 0
    total_days = 0
    
    class_counts = {"Class A": 0, "Class B": 0, "Class C": 0}
    
    for violation in violations:
        # Count by class
        violation_class = violation.get('violation_class', 'Class A')
        class_counts[violation_class] = class_counts.get(violation_class, 0) + 1
        
        # Check if resolved
        disposition = violation.get('disposition', '')
        if disposition and disposition.upper() in ['RESOLVED', 'DISMISSED', 'CLOSED']:
            resolved_count += 1
            
            # Calculate days to resolution
            issue_date = violation.get('issue_date')
            disp_date = violation.get('disposition_date')
            if issue_date and disp_date:
                try:
                    issue = datetime.strptime(issue_date, '%Y-%m-%d')
                    disposition = datetime.strptime(disp_date, '%Y-%m-%d')
                    days_open = (disposition - issue).days
                    total_days += days_open
                except:
                    pass
        else:
            open_count += 1
    
    avg_days = total_days / resolved_count if resolved_count > 0 else 0
    
    return {
        "total": len(violations),
        "by_class": class_counts,
        "open": open_count,
        "resolved": resolved_count,
        "avg_days_open": round(avg_days, 1)
    }


class DOBViolationMonitor:
    """Monitor DOB violations for landlord property management."""
    
    def __init__(self, app_token: str = None):
        self.app_token = app_token
        
    def check_property(self, bbl: str, property_name: str = "") -> Dict:
        """Check DOB violations for a single property."""
        violations = fetch_dob_violations(bbl)
        summary = get_violation_summary(violations)
        
        return {
            "bbl": bbl,
            "property_name": property_name,
            "violations": violations,
            "summary": summary,
            "risk_level": self._assess_risk_level(summary),
            "last_checked": datetime.now().isoformat()
        }
    
    def check_portfolio(self, properties: List[Dict]) -> Dict:
        """Check DOB violations for multiple properties."""
        results = []
        total_summary = {"total": 0, "by_class": {"Class A": 0, "Class B": 0, "Class C": 0}, "open": 0}
        
        for prop in properties:
            bbl = prop.get('bbl')
            name = prop.get('name', '')
            
            if bbl:
                result = self.check_property(bbl, name)
                results.append(result)
                
                # Aggregate totals
                summary = result['summary']
                total_summary['total'] += summary['total']
                total_summary['open'] += summary['open']
                for cls in ['Class A', 'Class B', 'Class C']:
                    total_summary['by_class'][cls] += summary['by_class'].get(cls, 0)
        
        return {
            "properties": results,
            "portfolio_summary": total_summary,
            "properties_checked": len(results),
            "check_timestamp": datetime.now().isoformat()
        }
    
    def _assess_risk_level(self, summary: Dict) -> str:
        """Assess risk level based on violation summary."""
        if summary['by_class'].get('Class C', 0) > 0:
            return "CRITICAL"
        elif summary['by_class'].get('Class B', 0) > 2:
            return "HIGH"
        elif summary['open'] > 5:
            return "MEDIUM"
        elif summary['total'] > 0:
            return "LOW"
        else:
            return "CLEAN"


if __name__ == "__main__":
    # Example usage
    monitor = DOBViolationMonitor()
    
    # Test with a sample BBL
    test_bbl = "1012650001"  # Example BBL
    result = monitor.check_property(test_bbl, "Sample Property")
    
    print(f"Property: {result['property_name']} ({result['bbl']})")
    print(f"Violations found: {result['summary']['total']}")
    print(f"Open violations: {result['summary']['open']}")
    print(f"Risk level: {result['risk_level']}")
    print(f"By class: {result['summary']['by_class']}")
