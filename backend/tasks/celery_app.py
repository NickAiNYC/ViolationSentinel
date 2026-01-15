"""
Celery Application
Async task processing
"""

from celery import Celery
from celery.schedules import crontab

from backend.config import settings

# Create Celery app
celery_app = Celery(
    "violation_sentinel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.ingestion_tasks",
        "backend.tasks.risk_scoring_tasks",
        "backend.tasks.alert_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Daily data ingestion at 2 AM
    "ingest-nyc-data-daily": {
        "task": "backend.tasks.ingestion_tasks.ingest_all_sources",
        "schedule": crontab(hour=2, minute=0),
    },
    # Risk scoring every 6 hours
    "calculate-risk-scores": {
        "task": "backend.tasks.risk_scoring_tasks.calculate_all_risk_scores",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Check alerts every 15 minutes
    "check-alert-rules": {
        "task": "backend.tasks.alert_tasks.check_all_alert_rules",
        "schedule": crontab(minute="*/15"),
    },
    # Cleanup old data weekly
    "cleanup-old-data": {
        "task": "backend.tasks.ingestion_tasks.cleanup_old_data",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
}

if __name__ == "__main__":
    celery_app.start()
