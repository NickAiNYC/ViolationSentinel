"""
Alert Tasks
Async tasks for checking alert rules and sending notifications
"""

from datetime import datetime
from typing import List, Dict
import logging

from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.tasks.alert_tasks.check_alert_rule")
def check_alert_rule(rule_id: str) -> Dict:
    """
    Check a single alert rule
    """
    logger.info(f"Checking alert rule {rule_id}")
    
    try:
        from backend.alerts.alert_engine import AlertEngine
        
        engine = AlertEngine()
        result = engine.check_rule(rule_id)
        
        logger.info(f"Alert rule {rule_id} checked: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Alert rule check failed for {rule_id}: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="backend.tasks.alert_tasks.check_all_alert_rules")
def check_all_alert_rules() -> Dict:
    """
    Check all active alert rules
    """
    logger.info("Starting alert rule check for all active rules")
    
    try:
        from backend.alerts.alert_engine import AlertEngine
        from backend.database import get_db
        from backend.data_models.alert import AlertRule
        from sqlalchemy import select
        import asyncio
        
        async def check_all():
            async with get_db() as db:
                # Get all active alert rules
                stmt = select(AlertRule).where(AlertRule.is_active == True)
                result = await db.execute(stmt)
                rules = result.scalars().all()
                
                engine = AlertEngine()
                results = {
                    "total_rules": len(rules),
                    "alerts_triggered": 0,
                    "started_at": datetime.utcnow().isoformat(),
                }
                
                for rule in rules:
                    try:
                        check_result = await engine.check_rule_async(str(rule.id))
                        if check_result.get("triggered"):
                            results["alerts_triggered"] += 1
                    except Exception as e:
                        logger.error(f"Failed to check rule {rule.id}: {str(e)}")
                
                results["completed_at"] = datetime.utcnow().isoformat()
                return results
        
        result = asyncio.run(check_all())
        logger.info(f"Alert rule check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Alert rule check failed: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="backend.tasks.alert_tasks.send_alert_notification")
def send_alert_notification(alert_id: str, channels: List[str]) -> Dict:
    """
    Send notifications for an alert through specified channels
    """
    logger.info(f"Sending notifications for alert {alert_id} via {channels}")
    
    try:
        from backend.alerts.notification_service import NotificationService
        
        service = NotificationService()
        result = service.send_alert_notifications(alert_id, channels)
        
        logger.info(f"Notifications sent for alert {alert_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Notification sending failed for {alert_id}: {str(e)}", exc_info=True)
        raise
