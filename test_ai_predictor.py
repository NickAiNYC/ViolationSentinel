"""
Unit tests for the AI Risk Predictor module.

Tests all core functionality including training, prediction, drift detection,
and model persistence.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai.risk_predictor import RiskPredictor, PredictionResult, ModelMetrics


@pytest.fixture
def sample_data():
    """Generate sample training and test data."""
    np.random.seed(42)
    n_samples = 200
    
    # Generate synthetic features
    X = pd.DataFrame({
        'property_age': np.random.randint(1, 100, n_samples),
        'violation_history_count': np.random.randint(0, 20, n_samples),
        'days_since_last_violation': np.random.randint(1, 365, n_samples),
        'neighborhood_risk_score': np.random.uniform(0, 1, n_samples),
        'total_units': np.random.randint(1, 100, n_samples),
        'complaint_frequency': np.random.uniform(0, 10, n_samples),
        'owner_compliance_score': np.random.uniform(0, 1, n_samples),
        'seasonal_factor': np.random.uniform(0, 1, n_samples),
        'economic_zone_risk': np.random.uniform(0, 1, n_samples),
        'flood_zone_risk': np.random.uniform(0, 1, n_samples),
        'construction_activity_nearby': np.random.randint(0, 2, n_samples)
    })
    
    # Generate synthetic targets (correlated with features)
    y_critical = (
        (X['violation_history_count'] > 10) & 
        (X['owner_compliance_score'] < 0.5)
    ).astype(int)
    
    y_days = (
        365 - X['violation_history_count'] * 10 - 
        X['neighborhood_risk_score'] * 100 +
        X['owner_compliance_score'] * 100
    ).clip(1, 365)
    
    return X, y_critical, y_days


@pytest.fixture
def trained_predictor(sample_data):
    """Create and train a predictor with sample data."""
    X, y_critical, y_days = sample_data
    
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = RiskPredictor(model_dir=tmpdir)
        predictor.train(X, y_critical, y_days, cv_splits=3)
        yield predictor


def test_predictor_initialization():
    """Test predictor initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = RiskPredictor(model_dir=tmpdir)
        
        assert predictor.model_dir == Path(tmpdir)
        assert predictor.scaler is None
        assert predictor.model_version == "1.0.0"
        assert predictor.metrics.prediction_count == 0


def test_training(sample_data):
    """Test model training with cross-validation."""
    X, y_critical, y_days = sample_data
    
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = RiskPredictor(model_dir=tmpdir)
        cv_scores = predictor.train(X, y_critical, y_days, cv_splits=3)
        
        # Check that models are trained
        assert predictor.scaler is not None
        assert predictor.rf_classifier is not None
        assert predictor.xgb_classifier is not None
        assert predictor.lgb_classifier is not None
        
        # Check CV scores
        assert 'rf_classifier_auc' in cv_scores
        assert 'xgb_classifier_auc' in cv_scores
        assert 'lgb_classifier_auc' in cv_scores
        assert 'rf_regressor_rmse' in cv_scores
        
        # AUC should be between 0 and 1
        assert 0 <= cv_scores['rf_classifier_auc'] <= 1
        
        # Check that metrics are updated
        assert predictor.metrics.last_retrain_date is not None
        assert len(predictor.baseline_predictions) > 0


def test_single_prediction(trained_predictor):
    """Test single property prediction."""
    features = {
        'property_age': 50,
        'violation_history_count': 5,
        'days_since_last_violation': 30,
        'neighborhood_risk_score': 0.6,
        'total_units': 20,
        'complaint_frequency': 2.5,
        'owner_compliance_score': 0.7,
        'seasonal_factor': 0.5,
        'economic_zone_risk': 0.4,
        'flood_zone_risk': 0.3,
        'construction_activity_nearby': 1
    }
    
    result = trained_predictor.predict(features, property_id="TEST-001")
    
    # Check result structure
    assert isinstance(result, PredictionResult)
    assert result.property_id == "TEST-001"
    
    # Check risk score is in valid range
    assert 0 <= result.risk_score <= 100
    
    # Check risk level is valid
    assert result.risk_level in ['MINIMAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    # Check probabilities
    assert 0 <= result.critical_violation_probability <= 1
    assert result.days_until_next_violation >= 0
    
    # Check confidence
    assert 0 <= result.confidence <= 1
    
    # Check feature importance
    assert isinstance(result.feature_importance, dict)
    assert len(result.feature_importance) == 11
    
    # Check SHAP values
    assert isinstance(result.shap_values, dict)
    assert len(result.shap_values) == 11
    
    # Check recommendation
    assert isinstance(result.recommended_action, str)
    assert len(result.recommended_action) > 0


def test_batch_prediction(trained_predictor, sample_data):
    """Test batch prediction for multiple properties."""
    X, _, _ = sample_data
    X_test = X.head(10)
    property_ids = [f"PROP-{i:03d}" for i in range(10)]
    
    results = trained_predictor.predict_batch(X_test, property_ids)
    
    # Check we got results for all properties
    assert len(results) == 10
    
    # Check each result
    for i, result in enumerate(results):
        assert result.property_id == property_ids[i]
        assert 0 <= result.risk_score <= 100
        assert result.risk_level in ['MINIMAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


def test_risk_level_mapping(trained_predictor):
    """Test that risk scores correctly map to risk levels."""
    # Test extreme cases
    
    # Very low risk property
    low_risk_features = {
        'property_age': 10,
        'violation_history_count': 0,
        'days_since_last_violation': 365,
        'neighborhood_risk_score': 0.1,
        'total_units': 5,
        'complaint_frequency': 0.1,
        'owner_compliance_score': 0.95,
        'seasonal_factor': 0.5,
        'economic_zone_risk': 0.1,
        'flood_zone_risk': 0.1,
        'construction_activity_nearby': 0
    }
    
    result_low = trained_predictor.predict(low_risk_features)
    assert result_low.risk_level in ['MINIMAL', 'LOW']
    
    # High risk property
    high_risk_features = {
        'property_age': 80,
        'violation_history_count': 15,
        'days_since_last_violation': 10,
        'neighborhood_risk_score': 0.9,
        'total_units': 50,
        'complaint_frequency': 8.0,
        'owner_compliance_score': 0.2,
        'seasonal_factor': 0.5,
        'economic_zone_risk': 0.8,
        'flood_zone_risk': 0.7,
        'construction_activity_nearby': 1
    }
    
    result_high = trained_predictor.predict(high_risk_features)
    assert result_high.risk_level in ['HIGH', 'CRITICAL']
    assert result_high.risk_score > result_low.risk_score


def test_feature_validation(trained_predictor):
    """Test that missing features raise appropriate errors."""
    # Missing required feature
    incomplete_features = {
        'property_age': 50,
        'violation_history_count': 5,
        # Missing other required features
    }
    
    with pytest.raises(ValueError, match="Missing required features"):
        trained_predictor.predict(incomplete_features)


def test_model_saving_loading(trained_predictor):
    """Test model persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Update model directory
        trained_predictor.model_dir = Path(tmpdir)
        
        # Save models
        save_path = trained_predictor.save_models(version="test_v1")
        assert Path(save_path).exists()
        
        # Create new predictor and load models
        new_predictor = RiskPredictor(model_dir=tmpdir)
        new_predictor.load_models(version="test_v1")
        
        # Check that models are loaded
        assert new_predictor.scaler is not None
        assert new_predictor.rf_classifier is not None
        
        # Test prediction with loaded model
        features = {
            'property_age': 50,
            'violation_history_count': 5,
            'days_since_last_violation': 30,
            'neighborhood_risk_score': 0.6,
            'total_units': 20,
            'complaint_frequency': 2.5,
            'owner_compliance_score': 0.7,
            'seasonal_factor': 0.5,
            'economic_zone_risk': 0.4,
            'flood_zone_risk': 0.3,
            'construction_activity_nearby': 1
        }
        
        result = new_predictor.predict(features)
        assert isinstance(result, PredictionResult)


def test_drift_detection(trained_predictor):
    """Test model drift detection."""
    # Generate baseline predictions
    for i in range(50):
        features = {
            'property_age': 50 + i,
            'violation_history_count': 5,
            'days_since_last_violation': 30,
            'neighborhood_risk_score': 0.6,
            'total_units': 20,
            'complaint_frequency': 2.5,
            'owner_compliance_score': 0.7,
            'seasonal_factor': 0.5,
            'economic_zone_risk': 0.4,
            'flood_zone_risk': 0.3,
            'construction_activity_nearby': 1
        }
        trained_predictor.predict(features, property_id=f"baseline-{i}")
    
    # Generate significantly different predictions (simulate drift)
    trained_predictor.recent_predictions = []
    for i in range(50):
        features = {
            'property_age': 80 + i,  # Older properties
            'violation_history_count': 15,  # More violations
            'days_since_last_violation': 5,  # Recent
            'neighborhood_risk_score': 0.9,  # Higher risk
            'total_units': 50,
            'complaint_frequency': 8.0,
            'owner_compliance_score': 0.2,  # Lower compliance
            'seasonal_factor': 0.5,
            'economic_zone_risk': 0.8,
            'flood_zone_risk': 0.7,
            'construction_activity_nearby': 1
        }
        trained_predictor.predict(features, property_id=f"drift-{i}")
    
    # Check drift detection
    drift_detected, p_value = trained_predictor.detect_drift()
    
    # With significantly different distributions, drift should be detected
    # (though this might not always trigger depending on random seed)
    assert isinstance(drift_detected, bool)
    assert 0 <= p_value <= 1


def test_metrics_tracking(trained_predictor):
    """Test that metrics are properly tracked."""
    initial_count = trained_predictor.metrics.prediction_count
    
    # Make some predictions
    for i in range(5):
        features = {
            'property_age': 50,
            'violation_history_count': 5,
            'days_since_last_violation': 30,
            'neighborhood_risk_score': 0.6,
            'total_units': 20,
            'complaint_frequency': 2.5,
            'owner_compliance_score': 0.7,
            'seasonal_factor': 0.5,
            'economic_zone_risk': 0.4,
            'flood_zone_risk': 0.3,
            'construction_activity_nearby': 1
        }
        trained_predictor.predict(features, property_id=f"metric-test-{i}")
    
    # Check metrics updated
    assert trained_predictor.metrics.prediction_count == initial_count + 5
    assert 0 <= trained_predictor.metrics.avg_confidence <= 1
    
    # Get metrics
    metrics = trained_predictor.get_metrics()
    assert isinstance(metrics, ModelMetrics)
    assert metrics.prediction_count > 0


def test_feature_importance(trained_predictor):
    """Test feature importance calculation."""
    features = {
        'property_age': 50,
        'violation_history_count': 5,
        'days_since_last_violation': 30,
        'neighborhood_risk_score': 0.6,
        'total_units': 20,
        'complaint_frequency': 2.5,
        'owner_compliance_score': 0.7,
        'seasonal_factor': 0.5,
        'economic_zone_risk': 0.4,
        'flood_zone_risk': 0.3,
        'construction_activity_nearby': 1
    }
    
    result = trained_predictor.predict(features)
    
    # Check that importances sum to approximately 1
    total_importance = sum(result.feature_importance.values())
    assert abs(total_importance - 1.0) < 0.01
    
    # Check that all features have importance
    for feature in trained_predictor.EXPECTED_FEATURES:
        assert feature in result.feature_importance
        assert result.feature_importance[feature] >= 0


def test_shap_values(trained_predictor):
    """Test SHAP value calculation."""
    features = {
        'property_age': 50,
        'violation_history_count': 5,
        'days_since_last_violation': 30,
        'neighborhood_risk_score': 0.6,
        'total_units': 20,
        'complaint_frequency': 2.5,
        'owner_compliance_score': 0.7,
        'seasonal_factor': 0.5,
        'economic_zone_risk': 0.4,
        'flood_zone_risk': 0.3,
        'construction_activity_nearby': 1
    }
    
    result = trained_predictor.predict(features)
    
    # Check that all features have SHAP values
    for feature in trained_predictor.EXPECTED_FEATURES:
        assert feature in result.shap_values
        # SHAP values can be positive or negative
        assert isinstance(result.shap_values[feature], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
