"""
Risk Scoring Tasks
Async tasks for calculating property risk scores
"""

from datetime import datetime
from typing import List, Dict
import logging

from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.tasks.risk_scoring_tasks.calculate_risk_score")
def calculate_risk_score(property_id: str) -> Dict:
    """
    Calculate risk score for a single property
    """
    logger.info(f"Calculating risk score for property {property_id}")
    
    try:
        from backend.risk_scoring.risk_engine import RiskScoringEngine
        
        engine = RiskScoringEngine()
        result = engine.calculate_property_risk(property_id)
        
        logger.info(f"Risk score calculated for {property_id}: {result['overall_score']:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Risk scoring failed for {property_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="backend.tasks.risk_scoring_tasks.calculate_all_risk_scores")
def calculate_all_risk_scores() -> Dict:
    """
    Calculate risk scores for all active properties
    """
    logger.info("Starting batch risk score calculation")
    
    try:
        from backend.risk_scoring.risk_engine import RiskScoringEngine
        from backend.database import get_db
        from backend.data_models.property import Property
        from sqlalchemy import select
        import asyncio
        
        async def calculate_all():
            async with get_db() as db:
                # Get all active properties
                stmt = select(Property).where(Property.deleted_at.is_(None))
                result = await db.execute(stmt)
                properties = result.scalars().all()
                
                engine = RiskScoringEngine()
                results = {
                    "total": len(properties),
                    "success": 0,
                    "failed": 0,
                    "started_at": datetime.utcnow().isoformat(),
                }
                
                for prop in properties:
                    try:
                        await engine.calculate_property_risk_async(str(prop.id))
                        results["success"] += 1
                    except Exception as e:
                        logger.error(f"Failed to calculate risk for {prop.id}: {str(e)}")
                        results["failed"] += 1
                
                results["completed_at"] = datetime.utcnow().isoformat()
                return results
        
        result = asyncio.run(calculate_all())
        logger.info(f"Batch risk scoring completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Batch risk scoring failed: {str(e)}", exc_info=True)
        raise
