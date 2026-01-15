"""
Data Ingestion Tasks
Async tasks for fetching NYC Open Data
"""

from datetime import datetime, timedelta
from typing import List, Dict
import logging

from backend.tasks.celery_app import celery_app
from backend.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.tasks.ingestion_tasks.ingest_dob_violations")
def ingest_dob_violations() -> Dict:
    """
    Ingest DOB violations from NYC Open Data
    """
    logger.info("Starting DOB violations ingestion")
    
    try:
        # Import here to avoid circular dependencies
        from backend.data_ingestion.dob_ingestion import DOBIngestionService
        
        service = DOBIngestionService()
        result = service.ingest_incremental()
        
        logger.info(f"DOB ingestion completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"DOB ingestion failed: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="backend.tasks.ingestion_tasks.ingest_hpd_violations")
def ingest_hpd_violations() -> Dict:
    """
    Ingest HPD violations from NYC Open Data
    """
    logger.info("Starting HPD violations ingestion")
    
    try:
        from backend.data_ingestion.hpd_ingestion import HPDIngestionService
        
        service = HPDIngestionService()
        result = service.ingest_incremental()
        
        logger.info(f"HPD ingestion completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"HPD ingestion failed: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="backend.tasks.ingestion_tasks.ingest_311_complaints")
def ingest_311_complaints() -> Dict:
    """
    Ingest 311 complaints from NYC Open Data
    """
    logger.info("Starting 311 complaints ingestion")
    
    try:
        from backend.data_ingestion.complaint_311_ingestion import Complaint311IngestionService
        
        service = Complaint311IngestionService()
        result = service.ingest_incremental()
        
        logger.info(f"311 ingestion completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"311 ingestion failed: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="backend.tasks.ingestion_tasks.ingest_all_sources")
def ingest_all_sources() -> Dict:
    """
    Ingest data from all sources
    """
    logger.info("Starting full data ingestion from all sources")
    
    results = {
        "dob": None,
        "hpd": None,
        "311": None,
        "started_at": datetime.utcnow().isoformat(),
    }
    
    try:
        # Run ingestion tasks
        results["dob"] = ingest_dob_violations.apply_async().get()
        results["hpd"] = ingest_hpd_violations.apply_async().get()
        results["311"] = ingest_311_complaints.apply_async().get()
        results["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Full ingestion completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Full ingestion failed: {str(e)}", exc_info=True)
        results["error"] = str(e)
        results["completed_at"] = datetime.utcnow().isoformat()
        return results


@celery_app.task(name="backend.tasks.ingestion_tasks.cleanup_old_data")
def cleanup_old_data() -> Dict:
    """
    Clean up old data based on retention policy
    """
    logger.info(f"Starting data cleanup (retention: {settings.DATA_RETENTION_DAYS} days)")
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=settings.DATA_RETENTION_DAYS)
        
        # Import database session
        from backend.database import get_db
        from backend.data_models.violation import Violation
        from sqlalchemy import delete
        
        deleted_count = 0
        
        async def cleanup():
            nonlocal deleted_count
            async with get_db() as db:
                # Delete old closed violations
                stmt = delete(Violation).where(
                    Violation.close_date < cutoff_date.date(),
                    Violation.status == "CLOSED"
                )
                result = await db.execute(stmt)
                deleted_count = result.rowcount
        
        import asyncio
        asyncio.run(cleanup())
        
        result = {
            "deleted_violations": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }
        
        logger.info(f"Data cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}", exc_info=True)
        raise
