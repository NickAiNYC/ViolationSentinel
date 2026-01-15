"""
Risk Scoring Engine
Property risk assessment with deterministic and ML hybrid approach
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from uuid import UUID
import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data_models.violation import Violation, ViolationSeverity, ViolationStatus
from backend.data_models.risk_score import RiskScore, TrendDirection
from backend.database import get_db

logger = logging.getLogger(__name__)


class RiskScoringEngine:
    """
    Risk scoring engine with deterministic + ML hybrid approach
    
    Scoring methodology:
    1. Base score from open violations (deterministic)
    2. Severity weighting (Class C > Class B > Class A)
    3. Time decay (older violations have less impact)
    4. Escalation detection (increasing violation trends)
    5. Confidence scoring based on data completeness
    6. ML enhancement (placeholder for XGBoost model)
    """
    
    # Severity weights (higher = more risk)
    SEVERITY_WEIGHTS = {
        ViolationSeverity.CLASS_C: 10.0,  # Immediately hazardous
        ViolationSeverity.CLASS_B: 5.0,   # Hazardous
        ViolationSeverity.CLASS_A: 2.0,   # Non-hazardous
        ViolationSeverity.UNKNOWN: 1.0,   # Unknown severity
    }
    
    # Category weights for sub-scores
    SAFETY_CATEGORIES = ['hazard', 'safety', 'fire', 'structural', 'emergency']
    LEGAL_CATEGORIES = ['permit', 'zoning', 'certificate', 'inspection', 'compliance']
    FINANCIAL_CATEGORIES = ['penalty', 'fine', 'fee', 'payment']
    
    # Time decay parameters
    TIME_DECAY_HALF_LIFE_DAYS = 180  # 6 months half-life
    
    # Escalation detection window
    ESCALATION_WINDOW_DAYS = 90
    
    def __init__(self):
        self.model_version = "v1.1.0"
        self.model_name = "RiskEngine-Deterministic-Hybrid"
        logger.info(f"Risk Scoring Engine initialized: {self.model_name} {self.model_version}")
    
    def _calculate_time_decay_factor(self, issue_date: date) -> float:
        """
        Calculate time decay factor using exponential decay
        More recent violations have higher impact
        """
        days_old = (date.today() - issue_date).days
        if days_old < 0:
            days_old = 0
        
        # Exponential decay: factor = 0.5^(days_old / half_life)
        decay_factor = math.pow(0.5, days_old / self.TIME_DECAY_HALF_LIFE_DAYS)
        return decay_factor
    
    def _calculate_violation_score(self, violation: Violation) -> float:
        """
        Calculate individual violation score with severity and time decay
        """
        # Base score from severity
        severity_weight = self.SEVERITY_WEIGHTS.get(
            violation.severity, 
            self.SEVERITY_WEIGHTS[ViolationSeverity.UNKNOWN]
        )
        
        # Apply time decay
        time_decay = self._calculate_time_decay_factor(violation.issue_date)
        
        # Calculate score
        score = severity_weight * time_decay
        
        return score
    
    def _categorize_violation(self, violation: Violation) -> Tuple[bool, bool, bool]:
        """
        Categorize violation into safety, legal, or financial
        Returns: (is_safety, is_legal, is_financial)
        """
        description_lower = violation.description.lower() if violation.description else ""
        category_lower = violation.category.lower() if violation.category else ""
        
        is_safety = any(keyword in description_lower or keyword in category_lower 
                       for keyword in self.SAFETY_CATEGORIES)
        is_legal = any(keyword in description_lower or keyword in category_lower 
                      for keyword in self.LEGAL_CATEGORIES)
        is_financial = any(keyword in description_lower or keyword in category_lower 
                          for keyword in self.FINANCIAL_CATEGORIES)
        
        # Default to legal if no specific category matched
        if not (is_safety or is_legal or is_financial):
            is_legal = True
            
        return is_safety, is_legal, is_financial
    
    def _detect_escalation(self, violations: List[Violation]) -> Tuple[bool, float]:
        """
        Detect if violations are escalating over time
        Returns: (is_escalating, escalation_rate)
        """
        if len(violations) < 2:
            return False, 0.0
        
        # Sort by issue date
        sorted_violations = sorted(violations, key=lambda v: v.issue_date)
        
        # Split into recent and older periods
        cutoff_date = date.today() - timedelta(days=self.ESCALATION_WINDOW_DAYS)
        recent_violations = [v for v in sorted_violations if v.issue_date >= cutoff_date]
        older_violations = [v for v in sorted_violations if v.issue_date < cutoff_date]
        
        if not older_violations:
            return False, 0.0
        
        # Calculate violation rates
        recent_count = len(recent_violations)
        older_count = len(older_violations)
        
        # Normalize by time period
        recent_days = min(self.ESCALATION_WINDOW_DAYS, (date.today() - cutoff_date).days)
        older_days = (cutoff_date - sorted_violations[0].issue_date).days
        
        if older_days == 0:
            return False, 0.0
        
        recent_rate = recent_count / recent_days if recent_days > 0 else 0
        older_rate = older_count / older_days if older_days > 0 else 0
        
        # Calculate escalation
        if older_rate == 0:
            escalation_rate = recent_rate * 100 if recent_rate > 0 else 0
        else:
            escalation_rate = ((recent_rate - older_rate) / older_rate) * 100
        
        is_escalating = escalation_rate > 20  # 20% increase threshold
        
        return is_escalating, escalation_rate
    
    def _calculate_confidence_score(
        self, 
        violations: List[Violation],
        property_age_days: Optional[int] = None
    ) -> float:
        """
        Calculate confidence score based on data completeness
        Range: 0.0 to 1.0
        """
        confidence_factors = []
        
        # Factor 1: Number of violations (more data = higher confidence)
        violation_count = len(violations)
        if violation_count == 0:
            confidence_factors.append(0.3)
        elif violation_count < 5:
            confidence_factors.append(0.5)
        elif violation_count < 10:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.9)
        
        # Factor 2: Data recency (recent data = higher confidence)
        if violations:
            most_recent = max(v.issue_date for v in violations)
            days_since_update = (date.today() - most_recent).days
            if days_since_update < 30:
                confidence_factors.append(0.95)
            elif days_since_update < 90:
                confidence_factors.append(0.85)
            elif days_since_update < 180:
                confidence_factors.append(0.70)
            else:
                confidence_factors.append(0.50)
        else:
            confidence_factors.append(0.5)
        
        # Factor 3: Data completeness (all fields populated)
        if violations:
            complete_violations = sum(
                1 for v in violations 
                if v.severity != ViolationSeverity.UNKNOWN 
                and v.category is not None
            )
            completeness_ratio = complete_violations / len(violations)
            confidence_factors.append(completeness_ratio)
        else:
            confidence_factors.append(0.5)
        
        # Calculate average confidence
        confidence = sum(confidence_factors) / len(confidence_factors)
        
        return round(confidence, 3)
    
    async def calculate_property_risk_async(self, property_id: UUID) -> Dict:
        """
        Calculate comprehensive risk score for a property (async version)
        """
        start_time = datetime.utcnow()
        
        try:
            async with get_db() as db:
                # Fetch all open violations for the property
                stmt = select(Violation).where(
                    Violation.property_id == property_id,
                    Violation.status == ViolationStatus.OPEN
                )
                result = await db.execute(stmt)
                open_violations = list(result.scalars().all())
                
                logger.info(f"Property {property_id}: Found {len(open_violations)} open violations")
                
                # Initialize scores
                total_score = 0.0
                safety_score = 0.0
                legal_score = 0.0
                financial_score = 0.0
                
                safety_count = 0
                legal_count = 0
                financial_count = 0
                
                # Calculate scores for each violation
                for violation in open_violations:
                    violation_score = self._calculate_violation_score(violation)
                    total_score += violation_score
                    
                    # Categorize and add to sub-scores
                    is_safety, is_legal, is_financial = self._categorize_violation(violation)
                    
                    if is_safety:
                        safety_score += violation_score
                        safety_count += 1
                    if is_legal:
                        legal_score += violation_score
                        legal_count += 1
                    if is_financial:
                        financial_score += violation_score
                        financial_count += 1
                
                # Normalize scores to 0-100 range
                # Using logarithmic scaling to handle wide range of violation counts
                max_expected_score = 50.0  # Calibration point
                
                overall_score = min(100.0, (total_score / max_expected_score) * 100)
                safety_score_normalized = min(100.0, (safety_score / max_expected_score) * 100) if safety_count > 0 else 0.0
                legal_score_normalized = min(100.0, (legal_score / max_expected_score) * 100) if legal_count > 0 else 0.0
                financial_score_normalized = min(100.0, (financial_score / max_expected_score) * 100) if financial_count > 0 else 0.0
                
                # Detect escalation
                is_escalating, escalation_rate = self._detect_escalation(open_violations)
                
                # Adjust overall score for escalation
                if is_escalating:
                    escalation_adjustment = min(15.0, escalation_rate * 0.1)
                    overall_score = min(100.0, overall_score + escalation_adjustment)
                    logger.info(f"Property {property_id}: Escalation detected (+{escalation_adjustment:.2f})")
                
                # Determine trend direction
                if is_escalating:
                    trend_direction = TrendDirection.WORSENING
                elif len(open_violations) == 0:
                    trend_direction = TrendDirection.IMPROVING
                else:
                    # Check for recent closures to determine trend
                    recent_closed_stmt = select(func.count(Violation.id)).where(
                        Violation.property_id == property_id,
                        Violation.status == ViolationStatus.CLOSED,
                        Violation.close_date >= date.today() - timedelta(days=self.ESCALATION_WINDOW_DAYS)
                    )
                    recent_closed_result = await db.execute(recent_closed_stmt)
                    recent_closed_count = recent_closed_result.scalar() or 0
                    
                    if recent_closed_count > len(open_violations):
                        trend_direction = TrendDirection.IMPROVING
                    elif recent_closed_count > 0:
                        trend_direction = TrendDirection.STABLE
                    else:
                        trend_direction = TrendDirection.STABLE
                
                # Calculate confidence
                confidence = self._calculate_confidence_score(open_violations)
                
                # Calculate duration
                calculation_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Prepare features for ML enhancement (future use)
                features = {
                    "open_violation_count": len(open_violations),
                    "class_c_count": sum(1 for v in open_violations if v.severity == ViolationSeverity.CLASS_C),
                    "class_b_count": sum(1 for v in open_violations if v.severity == ViolationSeverity.CLASS_B),
                    "class_a_count": sum(1 for v in open_violations if v.severity == ViolationSeverity.CLASS_A),
                    "is_escalating": is_escalating,
                    "escalation_rate": round(escalation_rate, 2),
                    "safety_violation_count": safety_count,
                    "legal_violation_count": legal_count,
                    "financial_violation_count": financial_count,
                    "avg_violation_age_days": int(
                        sum((date.today() - v.issue_date).days for v in open_violations) / len(open_violations)
                    ) if open_violations else 0,
                }
                
                # Store risk score in database
                risk_score = RiskScore(
                    property_id=property_id,
                    overall_score=round(overall_score, 2),
                    safety_score=round(safety_score_normalized, 2),
                    legal_score=round(legal_score_normalized, 2),
                    financial_score=round(financial_score_normalized, 2),
                    trend_direction=trend_direction,
                    trend_change_pct=round(escalation_rate, 2) if is_escalating else None,
                    confidence=confidence,
                    model_version=self.model_version,
                    model_name=self.model_name,
                    calculated_at=datetime.utcnow(),
                    calculation_duration_ms=calculation_duration_ms,
                    features=features,
                )
                
                db.add(risk_score)
                await db.commit()
                
                logger.info(
                    f"Property {property_id}: Risk score calculated - "
                    f"Overall: {overall_score:.2f}, Safety: {safety_score_normalized:.2f}, "
                    f"Legal: {legal_score_normalized:.2f}, Financial: {financial_score_normalized:.2f}, "
                    f"Confidence: {confidence:.3f}, Trend: {trend_direction}"
                )
                
                # Return result
                result = {
                    "property_id": str(property_id),
                    "overall_score": round(overall_score, 2),
                    "safety_score": round(safety_score_normalized, 2),
                    "legal_score": round(legal_score_normalized, 2),
                    "financial_score": round(financial_score_normalized, 2),
                    "trend_direction": trend_direction.value,
                    "trend_change_pct": round(escalation_rate, 2) if is_escalating else None,
                    "confidence": confidence,
                    "model_version": self.model_version,
                    "model_name": self.model_name,
                    "calculated_at": datetime.utcnow().isoformat(),
                    "calculation_duration_ms": calculation_duration_ms,
                    "features": features,
                    "risk_level": risk_score.get_risk_level(),
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error calculating risk score for property {property_id}: {str(e)}", exc_info=True)
            raise
    
    def calculate_property_risk(self, property_id: str) -> Dict:
        """
        Synchronous wrapper for calculate_property_risk_async
        Note: Use async version when possible for better performance
        """
        import asyncio
        try:
            property_uuid = UUID(property_id)
            result = asyncio.run(self.calculate_property_risk_async(property_uuid))
            return result
        except ValueError:
            logger.error(f"Invalid property_id format: {property_id}")
            raise ValueError(f"property_id must be a valid UUID, got: {property_id}")
