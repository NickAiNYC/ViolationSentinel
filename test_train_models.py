"""
Test script for scripts/train_models.py

Tests the model training pipeline with synthetic data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.train_models import (
    validate_data,
    prepare_features,
    calculate_metrics
)


def create_synthetic_data(n_samples: int = 100) -> pd.DataFrame:
    """Create synthetic violation data for testing."""
    np.random.seed(42)
    
    df = pd.DataFrame({
        'property_age': np.random.randint(1, 100, n_samples),
        'violation_history_count': np.random.randint(0, 50, n_samples),
        'days_since_last_violation': np.random.randint(1, 730, n_samples),
        'neighborhood_risk_score': np.random.uniform(0, 1, n_samples),
        'total_units': np.random.randint(1, 200, n_samples),
        'complaint_frequency': np.random.uniform(0, 10, n_samples),
        'owner_compliance_score': np.random.uniform(0, 1, n_samples),
        'seasonal_factor': np.random.uniform(0, 1, n_samples),
        'economic_zone_risk': np.random.uniform(0, 1, n_samples),
        'flood_zone_risk': np.random.uniform(0, 1, n_samples),
        'construction_activity_nearby': np.random.randint(0, 2, n_samples),
        'is_critical_violation': np.random.randint(0, 2, n_samples),
        'days_until_next_violation': np.random.randint(1, 365, n_samples)
    })
    
    return df


def test_data_validation():
    """Test data validation function."""
    import logging
    logger = logging.getLogger("test")
    
    # Valid data
    df = create_synthetic_data(50)
    try:
        validate_data(df, logger)
        print("✓ test_data_validation passed")
    except SystemExit:
        raise AssertionError("Valid data should not raise SystemExit")


def test_data_validation_missing_columns():
    """Test validation with missing columns."""
    import logging
    logger = logging.getLogger("test")
    
    df = pd.DataFrame({
        'property_age': [50],
        'violation_history_count': [10]
    })
    
    try:
        validate_data(df, logger)
        raise AssertionError("Should have raised SystemExit for missing columns")
    except SystemExit:
        pass  # Expected
    
    print("✓ test_data_validation_missing_columns passed")


def test_feature_preparation():
    """Test feature engineering."""
    import logging
    import argparse
    
    logger = logging.getLogger("test")
    
    df = create_synthetic_data(50)
    
    # Create mock args
    args = argparse.Namespace(
        use_temporal=False,
        use_interactions=True,
        use_aggregations=False,
        use_polynomial=False,
        polynomial_degree=2,
        scaler_type='robust'
    )
    
    X, y_class, y_reg, engineer = prepare_features(df, args, logger)
    
    assert X.shape[0] == 50, "Should have 50 samples"
    assert y_class.shape[0] == 50, "Should have 50 classification targets"
    assert y_reg.shape[0] == 50, "Should have 50 regression targets"
    assert X.shape[1] > 11, "Should have more than base features (interactions added)"
    
    print(f"✓ test_feature_preparation passed (features: {X.shape[1]})")


def test_data_loading_csv():
    """Test CSV data loading."""
    df = create_synthetic_data(30)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        temp_path = f.name
    
    try:
        import logging
        import argparse
        from scripts.train_models import load_data
        
        logger = logging.getLogger("test")
        args = argparse.Namespace(
            data_path=temp_path,
            db_connection=None,
            db_query=None
        )
        
        loaded_df = load_data(args, logger)
        assert len(loaded_df) == 30, "Should load 30 records"
        print("✓ test_data_loading_csv passed")
        
    finally:
        Path(temp_path).unlink()


def test_data_loading_json():
    """Test JSON data loading."""
    df = create_synthetic_data(20)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        df.to_json(f.name, orient='records')
        temp_path = f.name
    
    try:
        import logging
        import argparse
        from scripts.train_models import load_data
        
        logger = logging.getLogger("test")
        args = argparse.Namespace(
            data_path=temp_path,
            db_connection=None,
            db_query=None
        )
        
        loaded_df = load_data(args, logger)
        assert len(loaded_df) == 20, "Should load 20 records"
        print("✓ test_data_loading_json passed")
        
    finally:
        Path(temp_path).unlink()


def test_end_to_end_training():
    """Test complete training pipeline with small dataset."""
    import logging
    import argparse
    from scripts.train_models import prepare_features
    from ai.risk_predictor import RiskPredictor
    
    logger = logging.getLogger("test")
    
    # Create small dataset
    df = create_synthetic_data(100)
    
    args = argparse.Namespace(
        use_temporal=False,
        use_interactions=True,
        use_aggregations=False,
        use_polynomial=False,
        polynomial_degree=2,
        scaler_type='robust',
        cv_splits=2
    )
    
    # Prepare features
    X, y_class, y_reg, engineer = prepare_features(df, args, logger)
    
    # Train small model
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = RiskPredictor(model_dir=tmpdir, cv_splits=2)
        predictor.train(X, y_class, y_reg, cv_splits=2)
        
        # Make a prediction
        result = predictor.predict(X[0])
        
        assert hasattr(result, 'risk_score'), "Should have risk_score"
        assert hasattr(result, 'risk_level'), "Should have risk_level"
        assert 0 <= result.risk_score <= 100, "Risk score should be 0-100"
        
        print("✓ test_end_to_end_training passed")


if __name__ == '__main__':
    print("\nRunning training script tests...")
    print("="*60)
    
    try:
        test_data_validation()
        test_data_validation_missing_columns()
        test_feature_preparation()
        test_data_loading_csv()
        test_data_loading_json()
        test_end_to_end_training()
        
        print("="*60)
        print("✅ All training script tests passed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
