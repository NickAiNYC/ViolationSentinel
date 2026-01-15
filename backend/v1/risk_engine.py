"""
Risk Scoring Engine V1
Deterministic scoring for NYC property compliance risk
"""

from typing import Dict
from datetime import datetime, timedelta


class RiskEngine:
    """
    Simple, deterministic risk scoring engine
    
    Scoring rules:
    - Class C violations: 40 pts each
    - Heat complaints (last 7 days): 30 pts each
    - Open violations >90 days: 20 pts each
    - 311 complaint spike: 10 pts
    
    Max score: 100
    """
    
    def __init__(self):
        # Scoring weights
        self.CLASS_C_WEIGHT = 40
        self.HEAT_COMPLAINT_WEIGHT = 30
        self.OLD_VIOLATION_WEIGHT = 20
        self.COMPLAINT_SPIKE_WEIGHT = 10
        
    def calculate_risk(
        self,
        class_c_count: int = 0,
        heat_complaints_7d: int = 0,
        open_violations_90d: int = 0,
        complaint_311_spike: int = 0
    ) -> Dict:
        """
        Calculate property risk score
        
        Args:
            class_c_count: Number of Class C (immediate hazard) violations
            heat_complaints_7d: Heat/hot water complaints in last 7 days
            open_violations_90d: Violations open >90 days
            complaint_311_spike: Has 311 complaint spike (0 or 1)
            
        Returns:
            {
                "risk_score": int (0-100),
                "priority": str ("NORMAL"|"URGENT"|"IMMEDIATE"),
                "fine_risk_estimate": str ("$X,XXX"),
                "breakdown": dict
            }
        """
        # Calculate score
        score = 0
        breakdown = {}
        
        # Class C violations
        class_c_points = class_c_count * self.CLASS_C_WEIGHT
        score += class_c_points
        breakdown['class_c'] = class_c_points
        
        # Heat complaints
        heat_points = heat_complaints_7d * self.HEAT_COMPLAINT_WEIGHT
        score += heat_points
        breakdown['heat'] = heat_points
        
        # Old violations
        old_viol_points = open_violations_90d * self.OLD_VIOLATION_WEIGHT
        score += old_viol_points
        breakdown['old_violations'] = old_viol_points
        
        # 311 spike
        spike_points = complaint_311_spike * self.COMPLAINT_SPIKE_WEIGHT
        score += spike_points
        breakdown['311_spike'] = spike_points
        
        # Cap at 100
        score = min(100, score)
        
        # Determine priority
        if score >= 80:
            priority = "IMMEDIATE"
        elif score >= 50:
            priority = "URGENT"
        else:
            priority = "NORMAL"
        
        # Estimate fine risk
        fine_estimate = 0
        fine_estimate += class_c_count * 3000  # $1k-$5k avg = $3k
        fine_estimate += heat_complaints_7d * 350  # $250-$500/day avg = $350
        fine_estimate += open_violations_90d * 500  # $100-$1k avg = $500
        
        fine_risk_str = f"${fine_estimate:,}"
        
        return {
            "risk_score": score,
            "priority": priority,
            "fine_risk_estimate": fine_risk_str,
            "breakdown": breakdown,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def get_status_color(self, risk_score: int) -> str:
        """Get status color based on risk score"""
        if risk_score >= 80:
            return "RED"
        elif risk_score >= 50:
            return "YELLOW"
        else:
            return "GREEN"
    
    def get_recommendations(
        self,
        class_c_count: int = 0,
        heat_complaints_7d: int = 0,
        open_violations_90d: int = 0
    ) -> list:
        """Get action recommendations based on violations"""
        recommendations = []
        
        if class_c_count > 0:
            recommendations.append({
                "priority": "CRITICAL",
                "action": f"Address {class_c_count} Class C violation(s) IMMEDIATELY",
                "reason": "Class C violations indicate immediate hazards and can result in $1,000-$5,000 fines per violation"
            })
        
        if heat_complaints_7d > 0:
            recommendations.append({
                "priority": "URGENT",
                "action": f"Resolve {heat_complaints_7d} heat complaint(s) within 24 hours",
                "reason": "Heat violations can result in $250-$500 per day fines during heating season"
            })
        
        if open_violations_90d > 2:
            recommendations.append({
                "priority": "HIGH",
                "action": f"Clear {open_violations_90d} old violation(s)",
                "reason": "Long-standing violations increase risk of escalation and additional fines"
            })
        
        if not recommendations:
            recommendations.append({
                "priority": "LOW",
                "action": "Continue monitoring",
                "reason": "Property is in good standing"
            })
        
        return recommendations


# Singleton instance
risk_engine = RiskEngine()
