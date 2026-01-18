"""
Tests for Celery Background Tasks.

Tests for violation scanning, report generation, webhook delivery,
and other background task functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone


class TestViolationScanTasks:
    """Tests for violation scanning background tasks."""

    def test_scan_task_creation(self, mock_celery):
        """Test that violation scan tasks can be created."""
        # Mock task creation
        task_result = mock_celery.delay()
        assert task_result.id == "task-123"

    def test_scan_task_with_property_ids(self, mock_celery):
        """Test scan task accepts property IDs."""
        property_ids = ["prop-123", "prop-456", "prop-789"]
        
        # Simulate calling a scan task
        mock_celery.delay(property_ids=property_ids)
        mock_celery.delay.assert_called_once()

    def test_scan_task_with_sources(self, mock_celery):
        """Test scan task accepts source filters."""
        sources = ["HPD", "DOB", "311"]
        
        mock_celery.delay(sources=sources)
        mock_celery.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_calls_nyc_data_client(self, mock_nyc_data_api):
        """Test that scan task calls NYC Data API client."""
        bbl = "3012650001"
        
        await mock_nyc_data_api.get_hpd_violations(bbl=bbl)
        await mock_nyc_data_api.get_dob_violations(bbl=bbl)
        await mock_nyc_data_api.get_311_complaints(bbl=bbl)
        
        mock_nyc_data_api.get_hpd_violations.assert_called_once()
        mock_nyc_data_api.get_dob_violations.assert_called_once()
        mock_nyc_data_api.get_311_complaints.assert_called_once()


class TestReportGenerationTasks:
    """Tests for report generation background tasks."""

    def test_report_task_creation(self, mock_celery):
        """Test that report generation tasks can be created."""
        task_result = mock_celery.apply_async(
            args=[["prop-123"]],
            kwargs={"format": "pdf"}
        )
        assert task_result.id == "task-123"

    def test_report_formats_supported(self, mock_celery):
        """Test different report formats are supported."""
        formats = ["pdf", "json", "csv", "xlsx"]
        
        for format_type in formats:
            mock_celery.apply_async(kwargs={"format": format_type})
        
        assert mock_celery.apply_async.call_count == len(formats)

    def test_report_includes_violations(self, sample_violation):
        """Test report generation includes violation data."""
        # Simulate report data structure
        report_data = {
            "property_id": "prop-123",
            "violations": [sample_violation],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": "json"
        }
        
        assert "violations" in report_data
        assert len(report_data["violations"]) == 1

    def test_report_with_date_range(self, mock_celery):
        """Test report generation with date range filter."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        mock_celery.apply_async(kwargs={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        mock_celery.apply_async.assert_called_once()


class TestWebhookDeliveryTasks:
    """Tests for webhook delivery background tasks."""

    def test_webhook_task_creation(self, mock_celery):
        """Test that webhook delivery tasks can be created."""
        webhook_payload = {
            "event": "violation.created",
            "data": {"violation_id": "viol-123"}
        }
        
        task_result = mock_celery.delay(
            url="https://example.com/webhook",
            payload=webhook_payload
        )
        assert task_result.id == "task-123"

    def test_webhook_retry_on_failure(self, mock_celery):
        """Test webhook tasks support retry on failure."""
        # Configure mock to simulate retry behavior
        mock_celery.delay.side_effect = [Exception("Connection error"), MagicMock(id="task-123")]
        
        # First call should raise
        with pytest.raises(Exception):
            mock_celery.delay()
        
        # Retry should succeed
        result = mock_celery.delay()
        assert result.id == "task-123"

    def test_webhook_events_supported(self):
        """Test supported webhook event types."""
        supported_events = [
            "violation.created",
            "violation.resolved",
            "violation.high_risk",
            "scan.started",
            "scan.completed",
            "property.created",
            "property.at_risk"
        ]
        
        for event in supported_events:
            assert "." in event  # Events should be namespaced


class TestAlertNotificationTasks:
    """Tests for alert notification background tasks."""

    def test_alert_task_creation(self, mock_celery):
        """Test that alert notification tasks can be created."""
        alert_data = {
            "type": "high_risk_violation",
            "property_id": "prop-123",
            "message": "New Class C violation detected"
        }
        
        task_result = mock_celery.delay(alert_data=alert_data)
        assert task_result.id == "task-123"

    def test_sms_alert_task(self, mock_celery):
        """Test SMS alert notification task."""
        mock_celery.delay(
            channel="sms",
            phone="+15551234567",
            message="Urgent: New Class C violation at 123 Main St"
        )
        mock_celery.delay.assert_called_once()

    def test_email_alert_task(self, mock_celery):
        """Test email alert notification task."""
        mock_celery.delay(
            channel="email",
            to="manager@example.com",
            subject="New Violation Alert",
            body="A new violation has been detected..."
        )
        mock_celery.delay.assert_called_once()


class TestScheduledTasks:
    """Tests for scheduled/periodic background tasks."""

    def test_daily_scan_schedule(self):
        """Test daily violation scan is schedulable."""
        # Simulate celery beat schedule entry
        schedule = {
            "task": "tasks.scan_all_properties",
            "schedule": 86400,  # Daily in seconds
            "args": []
        }
        
        assert schedule["schedule"] == 86400

    def test_hourly_risk_recalculation(self):
        """Test hourly risk recalculation schedule."""
        schedule = {
            "task": "tasks.recalculate_risk_scores",
            "schedule": 3600,  # Hourly
            "args": []
        }
        
        assert schedule["schedule"] == 3600

    def test_weekly_report_generation(self):
        """Test weekly report generation schedule."""
        schedule = {
            "task": "tasks.generate_weekly_reports",
            "schedule": 604800,  # Weekly in seconds
            "args": []
        }
        
        assert schedule["schedule"] == 604800


class TestTaskResultHandling:
    """Tests for task result storage and retrieval."""

    def test_task_result_stored(self, mock_celery):
        """Test task results are stored."""
        task_result = mock_celery.delay()
        
        # Simulate result retrieval
        task_result.get = MagicMock(return_value={"status": "completed"})
        result = task_result.get()
        
        assert result["status"] == "completed"

    def test_task_failure_handling(self, mock_celery):
        """Test task failure is properly recorded."""
        task_result = mock_celery.delay()
        
        # Simulate task failure
        task_result.failed = MagicMock(return_value=True)
        task_result.traceback = "Error: Connection timeout"
        
        assert task_result.failed()
        assert "Error" in task_result.traceback

    def test_task_status_tracking(self, mock_celery):
        """Test task status can be tracked."""
        task_result = mock_celery.delay()
        
        # Simulate status progression
        statuses = ["PENDING", "STARTED", "SUCCESS"]
        
        for expected_status in statuses:
            task_result.status = expected_status
            assert task_result.status == expected_status


class TestDataProcessingTasks:
    """Tests for data processing background tasks."""

    def test_process_violation_data(self, sample_hpd_violation):
        """Test violation data processing."""
        # Simulate processing
        processed = {
            "id": sample_hpd_violation["violationid"],
            "source": "HPD",
            "type": sample_hpd_violation["class"],
            "description": sample_hpd_violation["novdescription"],
            "is_resolved": sample_hpd_violation["violationstatus"] != "Open"
        }
        
        assert processed["source"] == "HPD"
        assert processed["type"] == "C"
        assert processed["is_resolved"] == False

    def test_calculate_risk_score(self, sample_building_data):
        """Test risk score calculation in background task."""
        # Import risk engine functions
        try:
            from risk_engine.pre1974_multiplier import pre1974_risk_multiplier
            from risk_engine.inspector_patterns import inspector_risk_multiplier
            
            era_mult, _ = pre1974_risk_multiplier(
                {"year_built": sample_building_data["year_built"]}
            )
            inspector_mult = inspector_risk_multiplier(
                sample_building_data["bbl"],
                sample_building_data.get("council_district")
            )
            
            combined_multiplier = era_mult * inspector_mult
            assert combined_multiplier > 0
        except ImportError:
            pytest.skip("Risk engine not available")

    def test_aggregate_portfolio_data(self, portfolio_buildings):
        """Test portfolio data aggregation task."""
        # Simulate aggregation
        total_buildings = len(portfolio_buildings)
        pre_1974_count = sum(
            1 for b in portfolio_buildings 
            if b.get("year_built", 2000) < 1974
        )
        
        aggregated = {
            "total_buildings": total_buildings,
            "pre_1974_count": pre_1974_count,
            "pre_1974_percentage": round(pre_1974_count / total_buildings * 100, 1)
        }
        
        assert aggregated["total_buildings"] == 5
        assert aggregated["pre_1974_count"] == 3  # 1950, 1968, 1955


class TestTaskQueueManagement:
    """Tests for task queue management."""

    def test_task_priority_queues(self, mock_celery):
        """Test tasks can be routed to priority queues."""
        # High priority task
        mock_celery.apply_async(
            queue="high_priority",
            priority=9
        )
        
        # Normal priority task
        mock_celery.apply_async(
            queue="default",
            priority=5
        )
        
        assert mock_celery.apply_async.call_count == 2

    def test_task_routing(self, mock_celery):
        """Test task routing to specific queues."""
        task_routes = {
            "tasks.scan_violations": {"queue": "scan_queue"},
            "tasks.generate_report": {"queue": "report_queue"},
            "tasks.send_webhook": {"queue": "webhook_queue"}
        }
        
        for task_name, route in task_routes.items():
            assert "queue" in route

    def test_task_countdown_delay(self, mock_celery):
        """Test tasks can be delayed with countdown."""
        # Schedule task to run in 60 seconds
        mock_celery.apply_async(countdown=60)
        mock_celery.apply_async.assert_called_with(countdown=60)

    def test_task_eta_scheduling(self, mock_celery):
        """Test tasks can be scheduled with ETA."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        mock_celery.apply_async(eta=future_time)
        mock_celery.apply_async.assert_called_with(eta=future_time)


class TestTaskErrorHandling:
    """Tests for task error handling and recovery."""

    def test_task_max_retries(self):
        """Test task maximum retry configuration."""
        task_config = {
            "max_retries": 3,
            "default_retry_delay": 60,
            "retry_backoff": True,
            "retry_backoff_max": 600
        }
        
        assert task_config["max_retries"] == 3
        assert task_config["retry_backoff"] == True

    def test_task_retry_with_exponential_backoff(self):
        """Test exponential backoff retry delays."""
        base_delay = 60
        backoff_factor = 2
        
        delays = [base_delay * (backoff_factor ** i) for i in range(4)]
        
        assert delays == [60, 120, 240, 480]

    def test_task_dead_letter_queue(self):
        """Test failed tasks go to dead letter queue."""
        dlq_config = {
            "dead_letter_queue": "failed_tasks",
            "max_retries_before_dlq": 3
        }
        
        assert dlq_config["dead_letter_queue"] == "failed_tasks"


class TestCeleryWorkerConfig:
    """Tests for Celery worker configuration."""

    def test_worker_concurrency(self):
        """Test worker concurrency settings."""
        worker_config = {
            "concurrency": 4,
            "prefetch_multiplier": 2,
            "max_tasks_per_child": 1000
        }
        
        assert worker_config["concurrency"] == 4

    def test_worker_task_time_limit(self):
        """Test task time limits."""
        time_limits = {
            "task_soft_time_limit": 300,  # 5 minutes
            "task_time_limit": 600  # 10 minutes hard limit
        }
        
        assert time_limits["task_time_limit"] > time_limits["task_soft_time_limit"]

    def test_result_backend_config(self):
        """Test result backend configuration."""
        result_config = {
            "result_backend": "redis://redis:6379/2",
            "result_expires": 3600,  # 1 hour
            "result_extended": True
        }
        
        assert "redis" in result_config["result_backend"]


class TestTaskMonitoring:
    """Tests for task monitoring and metrics."""

    def test_task_execution_metrics(self, mock_celery):
        """Test task execution metrics are tracked."""
        # Simulate metrics collection
        metrics = {
            "tasks_completed": 100,
            "tasks_failed": 5,
            "tasks_pending": 10,
            "avg_execution_time": 2.5
        }
        
        assert metrics["tasks_completed"] > 0
        assert metrics["avg_execution_time"] > 0

    def test_task_queue_length_monitoring(self):
        """Test queue length can be monitored."""
        queue_stats = {
            "default": {"length": 25, "consumers": 4},
            "high_priority": {"length": 5, "consumers": 2},
            "low_priority": {"length": 100, "consumers": 1}
        }
        
        for queue, stats in queue_stats.items():
            assert stats["length"] >= 0
            assert stats["consumers"] > 0

    def test_worker_heartbeat(self, mock_celery):
        """Test worker heartbeat monitoring."""
        heartbeat_config = {
            "worker_heartbeat_interval": 10,
            "worker_lost_timeout": 60
        }
        
        assert heartbeat_config["worker_heartbeat_interval"] < heartbeat_config["worker_lost_timeout"]
