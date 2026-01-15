"""
Risk Scoring Engine V1
Deterministic scoring for NYC property compliance risk with ML feature extraction
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
import math


class RiskEngine:
    """
    Production-grade deterministic risk scoring engine with ML-ready features
    
    Scoring rules:
    - Class C violations: 40 pts each
    - Heat complaints (last 7 days): 30 pts each
    - Open violations >90 days: 20 pts each
    - 311 complaint spike: 10 pts
    
    Max score: 100
    
    Additional features:
    - Confidence scoring (0-1) based on data volume, recency, completeness
    - ML feature vector extraction for future XGBoost integration
    - Full explainability and audit trail
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
        complaint_311_spike: int = 0,
        total_violations: int = 0,
        days_since_last_inspection: int = 0,
        litigation_flag: bool = False,
        building_age: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive property risk score with confidence and ML features
        
        Args:
            class_c_count: Number of Class C (immediate hazard) violations
            heat_complaints_7d: Heat/hot water complaints in last 7 days
            open_violations_90d: Violations open >90 days
            complaint_311_spike: Has 311 complaint spike (0 or 1)
            total_violations: Total violation count (for confidence scoring)
            days_since_last_inspection: Days since last inspection (for confidence)
            litigation_flag: Property is in litigation
            building_age: Age of building in years (for features)
            
        Returns:
            {
                "risk_score": int (0-100),
                "priority": str ("NORMAL"|"URGENT"|"IMMEDIATE"),
                "fine_risk_estimate": str ("$X,XXX"),
                "confidence": float (0-1),
                "confidence_breakdown": dict,
                "breakdown": dict,
                "ml_features": dict,
                "calculated_at": str (ISO timestamp)
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
        if litigation_flag:
            fine_estimate += 10000  # Litigation adds $10k exposure
        
        fine_risk_str = f"${fine_estimate:,}"
        
        # Calculate confidence score
        confidence_data = self._calculate_confidence(
            total_violations=total_violations,
            days_since_last_inspection=days_since_last_inspection,
            has_class_c=class_c_count > 0,
            has_recent_complaints=heat_complaints_7d > 0
        )
        
        # Extract ML features for future model training
        ml_features = self._extract_ml_features(
            class_c_count=class_c_count,
            heat_complaints_7d=heat_complaints_7d,
            open_violations_90d=open_violations_90d,
            complaint_311_spike=complaint_311_spike,
            total_violations=total_violations,
            days_since_last_inspection=days_since_last_inspection,
            litigation_flag=litigation_flag,
            building_age=building_age
        )
        
        return {
            "risk_score": score,
            "priority": priority,
            "fine_risk_estimate": fine_risk_str,
            "confidence": confidence_data['overall'],
            "confidence_breakdown": confidence_data['breakdown'],
            "breakdown": breakdown,
            "ml_features": ml_features,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_confidence(
        self,
        total_violations: int,
        days_since_last_inspection: int,
        has_class_c: bool,
        has_recent_complaints: bool
    ) -> Dict[str, Any]:
        """
        Calculate confidence score based on data volume, recency, and completeness
        
        Returns:
            {
                "overall": float (0-1),
                "breakdown": {
                    "volume_factor": float,
                    "recency_factor": float,
                    "completeness_factor": float
                }
            }
        """
        # Volume factor (more data = higher confidence)
        # Scale: 0 violations = 0.3, 5 violations = 0.7, 10+ = 1.0
        volume_factor = min(1.0, 0.3 + (total_violations / 15.0))
        
        # Recency factor (fresh data = higher confidence)
        # Scale: 0 days = 1.0, 30 days = 0.8, 90 days = 0.5, 180+ = 0.3
        if days_since_last_inspection == 0:
            recency_factor = 1.0
        else:
            recency_factor = max(0.3, 1.0 - (days_since_last_inspection / 360.0))
        
        # Completeness factor (having critical violation types = higher confidence)
        completeness_score = 0.5  # Base score
        if has_class_c or has_recent_complaints:
            completeness_score += 0.3
        if has_class_c and has_recent_complaints:
            completeness_score += 0.2
        completeness_factor = min(1.0, completeness_score)
        
        # Overall confidence (weighted average)
        overall = (volume_factor * 0.4 + recency_factor * 0.4 + completeness_factor * 0.2)
        
        return {
            "overall": round(overall, 2),
            "breakdown": {
                "volume_factor": round(volume_factor, 2),
                "recency_factor": round(recency_factor, 2),
                "completeness_factor": round(completeness_factor, 2)
            }
        }
    
    def _extract_ml_features(
        self,
        class_c_count: int,
        heat_complaints_7d: int,
        open_violations_90d: int,
        complaint_311_spike: int,
        total_violations: int,
        days_since_last_inspection: int,
        litigation_flag: bool,
        building_age: int
    ) -> Dict[str, float]:
        """
        Extract feature vector for ML model training (XGBoost/Random Forest)
        
        Returns:
            Dictionary of normalized features ready for model input
        """
        # Normalize features to [0, 1] range for ML
        features = {
            # Core violation features
            "class_c_normalized": min(1.0, class_c_count / 5.0),
            "heat_complaints_normalized": min(1.0, heat_complaints_7d / 3.0),
            "old_violations_normalized": min(1.0, open_violations_90d / 10.0),
            "complaint_spike": float(complaint_311_spike),
            
            # Derived features
            "violation_rate": min(1.0, total_violations / 20.0) if total_violations > 0 else 0.0,
            "inspection_staleness": min(1.0, days_since_last_inspection / 365.0),
            "litigation_risk": 1.0 if litigation_flag else 0.0,
            
            # Interaction features
            "class_c_x_heat": (class_c_count * heat_complaints_7d) / 15.0 if (class_c_count + heat_complaints_7d) > 0 else 0.0,
            "old_x_total": (open_violations_90d / max(total_violations, 1)) if total_violations > 0 else 0.0,
            
            # Building characteristics
            "building_age_normalized": min(1.0, building_age / 100.0) if building_age > 0 else 0.5,
            
            # Risk ratios
            "critical_ratio": class_c_count / max(total_violations, 1) if total_violations > 0 else 0.0,
        }
        
        return {k: round(v, 4) for k, v in features.items()}
    
    def get_status_color(self, risk_score: int) -> str:
        """
        Get status color based on risk score
        
        Args:
            risk_score: Risk score (0-100)
            
        Returns:
            "RED" (>=80), "YELLOW" (>=50), or "GREEN" (<50)
        """
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
        open_violations_90d: int = 0,
        litigation_flag: bool = False
    ) -> List[Dict[str, str]]:
        """
        Get action recommendations based on violations
        
        Args:
            class_c_count: Number of Class C violations
            heat_complaints_7d: Heat complaints in last 7 days
            open_violations_90d: Open violations >90 days
            litigation_flag: Property is in litigation
            
        Returns:
            List of recommendation dictionaries with priority, action, and reason
        """
        recommendations = []
        
        if class_c_count > 0:
            recommendations.append({
                "priority": "CRITICAL",
                "action": f"Address {class_c_count} Class C violation(s) IMMEDIATELY",
                "reason": "Class C violations indicate immediate hazards and can result in $1,000-$5,000 fines per violation",
                "deadline": "24-48 hours"
            })
        
        if heat_complaints_7d > 0:
            recommendations.append({
                "priority": "URGENT",
                "action": f"Resolve {heat_complaints_7d} heat complaint(s) within 24 hours",
                "reason": "Heat violations can result in $250-$500 per day fines during heating season",
                "deadline": "24 hours"
            })
        
        if open_violations_90d > 2:
            recommendations.append({
                "priority": "HIGH",
                "action": f"Clear {open_violations_90d} old violation(s)",
                "reason": "Long-standing violations increase risk of escalation and additional fines",
                "deadline": "30 days"
            })
        
        if litigation_flag:
            recommendations.append({
                "priority": "HIGH",
                "action": "Consult legal counsel regarding ongoing litigation",
                "reason": "Litigation exposure can result in significant additional costs",
                "deadline": "Immediate"
            })
        
        if not recommendations:
            recommendations.append({
                "priority": "LOW",
                "action": "Continue monitoring",
                "reason": "Property is in good standing",
                "deadline": "N/A"
            })
        
        return recommendations


# Singleton instance
risk_engine = RiskEngine()
