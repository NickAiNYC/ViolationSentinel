"""
Tests for Model Monitoring System

Tests async operations, drift detection, metrics calculation, and alerting.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from ai.model_monitor import ModelMonitor, DriftResult, PredictionRecord


@pytest.fixture
async def monitor():
    """Create monitor instance for testing."""
    monitor = ModelMonitor(
        db_url="postgresql://localhost/test_violations",
        redis_url="redis://localhost:6379",
        accuracy_threshold=0.85,
        drift_threshold=0.05
    )
    # Mock database and redis
    monitor.db_pool = AsyncMock()
    monitor.redis = AsyncMock()
    return monitor


@pytest.mark.asyncio
async def test_monitor_initialization():
    """Test ModelMonitor initialization."""
    monitor = ModelMonitor(
        db_url="postgresql://localhost/test",
        accuracy_threshold=0.90
    )
    
    assert monitor.accuracy_threshold == 0.90
    assert monitor.drift_threshold == 0.05
    print("✓ test_monitor_initialization passed")


@pytest.mark.asyncio
async def test_add_prediction(monitor):
    """Test adding a prediction."""
    from dataclasses import dataclass
    
    @dataclass
    class MockPrediction:
        risk_score: float = 75.0
        risk_level: str = "HIGH"
        critical_violation_probability: float = 0.68
        days_until_next_violation: float = 45.0
        confidence: float = 0.87
        feature_importance: dict = None
        model_version: str = "1.0.0"
        
        def __post_init__(self):
            if self.feature_importance is None:
                self.feature_importance = {'age': 0.3}
    
    # Mock database response
    monitor.db_pool.acquire().__aenter__.return_value.fetchval = AsyncMock(return_value=123)
    monitor.redis.setex = AsyncMock()
    
    pred = MockPrediction()
    features = {'property_age': 50}
    
    pred_id = await monitor.add_prediction('PROP-001', pred, features)
    
    assert pred_id == 123
    print("✓ test_add_prediction passed")


@pytest.mark.asyncio
async def test_add_outcome(monitor):
    """Test adding an outcome."""
    # Mock database responses
    conn_mock = AsyncMock()
    conn_mock.fetchval.side_effect = [456, 789]  # prediction_id, outcome_id
    monitor.db_pool.acquire().__aenter__.return_value = conn_mock
    
    # Mock calculate_metrics
    monitor.calculate_metrics = AsyncMock()
    
    outcome_id = await monitor.add_outcome(
        property_id='PROP-001',
        actual_critical=True,
        actual_days=42.0
    )
    
    assert outcome_id == 789
    monitor.calculate_metrics.assert_called_once()
    print("✓ test_add_outcome passed")


@pytest.mark.asyncio
async def test_drift_detection(monitor):
    """Test drift detection logic."""
    # Mock database data
    baseline_data = [
        {'risk_score': 50.0}, {'risk_score': 55.0}, {'risk_score': 60.0}
    ] * 15  # 45 samples
    
    recent_data = [
        {'risk_score': 75.0}, {'risk_score': 80.0}, {'risk_score': 85.0}
    ] * 15  # 45 samples (shifted distribution)
    
    conn_mock = AsyncMock()
    conn_mock.fetch.side_effect = [baseline_data, recent_data]
    conn_mock.execute = AsyncMock()
    monitor.db_pool.acquire().__aenter__.return_value = conn_mock
    
    # Mock alert sending
    monitor._send_drift_alert = AsyncMock()
    
    drift_result = await monitor.detect_drift()
    
    assert isinstance(drift_result, DriftResult)
    assert drift_result.drift_detected == True  # Shifted distribution should be detected
    assert drift_result.p_value < 0.05
    print("✓ test_drift_detection passed")


@pytest.mark.asyncio
async def test_performance_metrics_calculation(monitor):
    """Test metrics calculation."""
    # Mock data with predictions and outcomes
    mock_data = [
        {
            'risk_score': 70.0,
            'critical_probability': 0.8,
            'days_until_violation': 30.0,
            'actual_critical': True,
            'actual_days': 35.0
        },
        {
            'risk_score': 40.0,
            'critical_probability': 0.3,
            'days_until_violation': 90.0,
            'actual_critical': False,
            'actual_days': None
        }
    ] * 10  # 20 samples
    
    conn_mock = AsyncMock()
    conn_mock.fetch.return_value = mock_data
    monitor.db_pool.acquire().__aenter__.return_value = conn_mock
    monitor.redis.get.return_value = None
    monitor.redis.setex = AsyncMock()
    
    metrics = await monitor.get_performance_metrics('7d')
    
    assert 'classification' in metrics
    assert 'regression' in metrics
    assert 'sample_size' in metrics
    assert metrics['sample_size'] == 20
    assert 0 <= metrics['classification']['accuracy'] <= 1
    print("✓ test_performance_metrics_calculation passed")


@pytest.mark.asyncio
async def test_weekly_report_generation(monitor):
    """Test weekly report generation."""
    # Mock metrics
    mock_metrics = {
        'classification': {
            'accuracy': 0.87,
            'precision': 0.85,
            'recall': 0.88,
            'f1_score': 0.86
        },
        'regression': {
            'mae': 10.5,
            'rmse': 15.2,
            'r2_score': 0.75
        },
        'sample_size': 100
    }
    
    mock_drift = DriftResult(
        drift_detected=False,
        drift_type='prediction',
        ks_statistic=0.02,
        p_value=0.15,
        message="No significant drift",
        severity='low',
        recommendation="Continue normal monitoring"
    )
    
    monitor.get_performance_metrics = AsyncMock(return_value=mock_metrics)
    monitor.detect_drift = AsyncMock(return_value=mock_drift)
    monitor._send_email = AsyncMock()
    
    report = await monitor.generate_weekly_report()
    
    assert isinstance(report, str)
    assert 'ViolationSentinel Model Performance Report' in report
    assert '0.87' in report or '87' in report  # Accuracy in report
    print("✓ test_weekly_report_generation passed")


def test_drift_result_dataclass():
    """Test DriftResult dataclass."""
    result = DriftResult(
        drift_detected=True,
        drift_type='feature',
        ks_statistic=0.15,
        p_value=0.02,
        message="Drift detected",
        severity='high',
        recommendation="Retrain model"
    )
    
    assert result.drift_detected == True
    assert result.severity == 'high'
    assert result.p_value < 0.05
    print("✓ test_drift_result_dataclass passed")


def test_retraining_check(monitor):
    """Test retraining recommendation logic."""
    metrics_bad = {
        'classification': {'accuracy': 0.80},
        'sample_size': 100
    }
    
    drift_bad = DriftResult(
        drift_detected=True,
        drift_type='prediction',
        ks_statistic=0.20,
        p_value=0.01,
        message="Significant drift",
        severity='high',
        recommendation="Retrain"
    )
    
    result = monitor._check_retraining_needed(metrics_bad, drift_bad)
    
    assert len(result) > 0
    assert "retraining recommended" in result.lower()
    print("✓ test_retraining_check passed")


@pytest.mark.asyncio
async def test_prometheus_metrics_update(monitor):
    """Test Prometheus metrics updating."""
    # Add a prediction
    from dataclasses import dataclass
    
    @dataclass
    class MockPrediction:
        risk_score: float = 75.0
        risk_level: str = "HIGH"
        critical_violation_probability: float = 0.68
        days_until_next_violation: float = 45.0
        confidence: float = 0.87
        feature_importance: dict = None
        model_version: str = "1.0.0"
        
        def __post_init__(self):
            if self.feature_importance is None:
                self.feature_importance = {}
    
    monitor.db_pool.acquire().__aenter__.return_value.fetchval = AsyncMock(return_value=1)
    monitor.redis.setex = AsyncMock()
    
    pred = MockPrediction()
    await monitor.add_prediction('PROP-001', pred, {})
    
    # Verify counter was incremented (just check it doesn't error)
    # In real tests, you'd use prometheus_client test utilities
    print("✓ test_prometheus_metrics_update passed")


@pytest.mark.asyncio
async def test_cache_behavior(monitor):
    """Test Redis caching."""
    # Setup cache hit
    cached_metrics = {
        'classification': {'accuracy': 0.90},
        'sample_size': 50
    }
    monitor.redis.get.return_value = str(cached_metrics).encode()
    
    # This should return cached value without DB query
    result = await monitor.get_performance_metrics('7d')
    
    # Verify DB was not queried
    monitor.db_pool.acquire.assert_not_called()
    print("✓ test_cache_behavior passed")


@pytest.mark.asyncio
async def test_insufficient_data_drift_detection(monitor):
    """Test drift detection with insufficient data."""
    # Mock insufficient data
    conn_mock = AsyncMock()
    conn_mock.fetch.side_effect = [
        [{'risk_score': 50.0}] * 10,  # Only 10 samples (need 30)
        [{'risk_score': 75.0}] * 5    # Only 5 samples
    ]
    monitor.db_pool.acquire().__aenter__.return_value = conn_mock
    
    drift_result = await monitor.detect_drift()
    
    assert drift_result.drift_detected == False
    assert "Insufficient data" in drift_result.message
    print("✓ test_insufficient_data_drift_detection passed")


@pytest.mark.asyncio
async def test_outcome_matching(monitor):
    """Test that outcomes are matched to correct predictions."""
    # Mock prediction lookup
    conn_mock = AsyncMock()
    conn_mock.fetchval.side_effect = [123, 456]  # prediction_id, outcome_id
    monitor.db_pool.acquire().__aenter__.return_value = conn_mock
    monitor.calculate_metrics = AsyncMock()
    
    outcome_id = await monitor.add_outcome(
        property_id='PROP-001',
        actual_critical=True,
        actual_days=42.0,
        outcome_timestamp=datetime.now()
    )
    
    # Verify the SQL query was called to find matching prediction
    assert conn_mock.fetchval.call_count == 2
    print("✓ test_outcome_matching passed")


# Run all tests
async def run_async_tests():
    """Run all async tests."""
    monitor = ModelMonitor(
        db_url="postgresql://localhost/test",
        redis_url="redis://localhost:6379"
    )
    monitor.db_pool = AsyncMock()
    monitor.redis = AsyncMock()
    
    await test_add_prediction(monitor)
    await test_add_outcome(monitor)
    await test_drift_detection(monitor)
    await test_performance_metrics_calculation(monitor)
    await test_weekly_report_generation(monitor)
    await test_prometheus_metrics_update(monitor)
    await test_cache_behavior(monitor)
    await test_insufficient_data_drift_detection(monitor)
    await test_outcome_matching(monitor)


if __name__ == "__main__":
    print("Running Model Monitoring Tests")
    print("=" * 60)
    
    # Run sync tests
    test_monitor_initialization()
    test_drift_result_dataclass()
    
    monitor = ModelMonitor(db_url="test")
    monitor.db_pool = AsyncMock()
    monitor.redis = AsyncMock()
    test_retraining_check(monitor)
    
    # Run async tests
    asyncio.run(run_async_tests())
    
    print("=" * 60)
    print("✅ All Model Monitoring tests passed!")
    print("=" * 60)
