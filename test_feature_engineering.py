"""
Unit tests for the FeatureEngineer class.

Tests cover:
- Temporal feature creation
- Interaction feature creation
- Aggregation feature creation
- Missing value handling
- Polynomial features
- Categorical encoding
- Feature scaling
- Fit/transform paradigm
- Save/load functionality
- Pipeline compatibility
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os

from ai.feature_engineering import FeatureEngineer, FeatureConfig


class TestFeatureEngineer(unittest.TestCase):
    """Test suite for FeatureEngineer class."""
    
    def setUp(self):
        """Create sample data for testing."""
        np.random.seed(42)
        self.n_samples = 100
        
        # Create realistic property data
        base_date = datetime(2023, 1, 1)
        self.sample_data = pd.DataFrame({
            'property_age': np.random.randint(1, 100, self.n_samples),
            'violation_history_count': np.random.randint(0, 50, self.n_samples),
            'days_since_last_violation': np.random.randint(0, 365, self.n_samples),
            'neighborhood_risk_score': np.random.uniform(0, 1, self.n_samples),
            'total_units': np.random.randint(1, 200, self.n_samples),
            'complaint_frequency': np.random.uniform(0, 10, self.n_samples),
            'owner_compliance_score': np.random.uniform(0, 1, self.n_samples),
            'seasonal_factor': np.random.uniform(0, 1, self.n_samples),
            'economic_zone_risk': np.random.uniform(0, 1, self.n_samples),
            'flood_zone_risk': np.random.uniform(0, 1, self.n_samples),
            'construction_activity_nearby': np.random.choice([0, 1], self.n_samples),
            'inspection_date': [base_date + timedelta(days=i) for i in range(self.n_samples)],
            'building_class': np.random.choice(['A', 'B', 'C'], self.n_samples),
            'neighborhood': np.random.choice(['Brooklyn', 'Manhattan', 'Queens'], self.n_samples)
        })
        
    def test_initialization(self):
        """Test FeatureEngineer initialization."""
        # Default config
        engineer = FeatureEngineer()
        self.assertIsNotNone(engineer.config)
        self.assertFalse(engineer.is_fitted_)
        
        # Custom config
        config = FeatureConfig(use_temporal=False, polynomial_degree=3)
        engineer = FeatureEngineer(config=config)
        self.assertEqual(engineer.config.polynomial_degree, 3)
        self.assertFalse(engineer.config.use_temporal)
        
    def test_temporal_features(self):
        """Test temporal feature creation."""
        engineer = FeatureEngineer()
        df_with_temporal = engineer.create_temporal_features(self.sample_data.copy())
        
        # Check new temporal columns exist
        expected_cols = ['month', 'quarter', 'season', 'day_of_week', 
                        'is_winter', 'is_summer', 'is_weekend', 'days_since_epoch']
        for col in expected_cols:
            self.assertIn(col, df_with_temporal.columns)
        
        # Check value ranges
        self.assertTrue(df_with_temporal['month'].between(1, 12).all())
        self.assertTrue(df_with_temporal['quarter'].between(1, 4).all())
        self.assertTrue(df_with_temporal['day_of_week'].between(0, 6).all())
        self.assertTrue(df_with_temporal['is_winter'].isin([0, 1]).all())
        
    def test_interaction_features(self):
        """Test interaction feature creation."""
        engineer = FeatureEngineer()
        df_with_interactions = engineer.create_interaction_features(self.sample_data.copy())
        
        # Check new interaction columns exist
        expected_cols = ['age_violation_interaction', 'risk_compliance_ratio', 
                        'complaints_per_unit', 'violation_density', 
                        'risk_age_product', 'compliance_units_ratio']
        for col in expected_cols:
            self.assertIn(col, df_with_interactions.columns)
        
        # Verify calculations
        self.assertTrue((df_with_interactions['age_violation_interaction'] >= 0).all())
        self.assertTrue((df_with_interactions['complaints_per_unit'] >= 0).all())
        
    def test_aggregation_features(self):
        """Test aggregation feature creation."""
        config = FeatureConfig(use_aggregations=True)
        engineer = FeatureEngineer(config=config)
        
        # First fit to compute aggregations
        engineer.is_fitted_ = False
        df_with_agg = engineer.create_aggregation_features(self.sample_data.copy())
        
        # Check aggregation stats were computed
        self.assertIsNotNone(engineer.aggregation_stats_)
        self.assertGreater(len(engineer.aggregation_stats_), 0)
        
    def test_missing_value_handling(self):
        """Test missing value imputation."""
        # Add missing values
        data_with_missing = self.sample_data.copy()
        data_with_missing.loc[0:5, 'property_age'] = np.nan
        data_with_missing.loc[10:15, 'neighborhood'] = np.nan
        
        engineer = FeatureEngineer()
        
        # Handle missing values
        df_imputed = engineer.handle_missing_values(data_with_missing, is_training=True)
        
        # Check no missing values remain
        self.assertEqual(df_imputed['property_age'].isnull().sum(), 0)
        self.assertEqual(df_imputed['neighborhood'].isnull().sum(), 0)
        
        # Check imputation values were stored
        self.assertIsNotNone(engineer.numerical_medians_)
        self.assertIsNotNone(engineer.categorical_modes_)
        
    def test_polynomial_features(self):
        """Test polynomial feature creation."""
        config = FeatureConfig(use_polynomial=True, polynomial_degree=2)
        engineer = FeatureEngineer(config=config)
        engineer.is_fitted_ = False
        
        df_with_poly = engineer.create_polynomial_features(self.sample_data.copy())
        
        # Check polynomial features were added
        poly_cols = [col for col in df_with_poly.columns if col.startswith('poly_')]
        self.assertGreater(len(poly_cols), 0)
        
        # Polynomial should create interactions and squares
        self.assertIsNotNone(engineer.polynomial)
        
    def test_categorical_encoding(self):
        """Test one-hot encoding of categorical variables."""
        engineer = FeatureEngineer()
        engineer.is_fitted_ = False
        
        df_encoded = engineer.encode_categorical(self.sample_data.copy())
        
        # Check original categorical columns are removed
        self.assertNotIn('building_class', df_encoded.columns)
        self.assertNotIn('neighborhood', df_encoded.columns)
        
        # Check encoded columns exist
        encoded_cols = [col for col in df_encoded.columns if 'building_class_' in col or 'neighborhood_' in col]
        self.assertGreater(len(encoded_cols), 0)
        
        # Check encoder was fitted
        self.assertIsNotNone(engineer.encoder)
        
    def test_feature_scaling(self):
        """Test feature scaling with RobustScaler and StandardScaler."""
        # Test RobustScaler
        config = FeatureConfig(scaler_type='robust')
        engineer = FeatureEngineer(config=config)
        engineer.is_fitted_ = False
        
        df_scaled = engineer.scale_features(self.sample_data.copy())
        
        # Check scaler was fitted
        self.assertIsNotNone(engineer.scaler)
        
        # Test StandardScaler
        config = FeatureConfig(scaler_type='standard')
        engineer2 = FeatureEngineer(config=config)
        engineer2.is_fitted_ = False
        
        df_scaled2 = engineer2.scale_features(self.sample_data.copy())
        self.assertIsNotNone(engineer2.scaler)
        
    def test_fit_transform_paradigm(self):
        """Test fit and transform work correctly."""
        config = FeatureConfig(
            use_temporal=True,
            use_interactions=True,
            use_aggregations=True,
            use_polynomial=True
        )
        engineer = FeatureEngineer(config=config)
        
        # Fit on training data
        X_train = self.sample_data.iloc[:80].copy()
        X_test = self.sample_data.iloc[80:].copy()
        
        engineer.fit(X_train)
        
        # Check fitted flag
        self.assertTrue(engineer.is_fitted_)
        self.assertIsNotNone(engineer.feature_names_)
        
        # Transform test data
        X_test_transformed = engineer.transform(X_test)
        
        # Check same number of features
        self.assertEqual(len(engineer.feature_names_), X_test_transformed.shape[1])
        
    def test_fit_transform_combined(self):
        """Test fit_transform method."""
        engineer = FeatureEngineer()
        
        X_transformed = engineer.fit_transform(self.sample_data.copy())
        
        # Check fitted and transformed
        self.assertTrue(engineer.is_fitted_)
        self.assertGreater(X_transformed.shape[1], self.sample_data.shape[1])
        
    def test_transform_without_fit_raises_error(self):
        """Test that transform without fit raises ValueError."""
        engineer = FeatureEngineer()
        
        with self.assertRaises(ValueError):
            engineer.transform(self.sample_data.copy())
            
    def test_save_load(self):
        """Test saving and loading fitted transformer."""
        # Fit engineer
        engineer = FeatureEngineer()
        engineer.fit(self.sample_data.copy())
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as tmp:
            tmp_path = tmp.name
        
        try:
            engineer.save(tmp_path)
            
            # Load and verify
            loaded_engineer = FeatureEngineer.load(tmp_path)
            
            self.assertTrue(loaded_engineer.is_fitted_)
            self.assertEqual(engineer.feature_names_, loaded_engineer.feature_names_)
            
            # Test transform works with loaded engineer
            X_transformed = loaded_engineer.transform(self.sample_data.copy())
            self.assertIsNotNone(X_transformed)
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    def test_save_unfitted_raises_error(self):
        """Test that saving unfitted transformer raises ValueError."""
        engineer = FeatureEngineer()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as tmp:
            tmp_path = tmp.name
        
        try:
            with self.assertRaises(ValueError):
                engineer.save(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    def test_get_feature_names(self):
        """Test getting feature names."""
        engineer = FeatureEngineer()
        engineer.fit(self.sample_data.copy())
        
        feature_names = engineer.get_feature_names()
        
        self.assertIsInstance(feature_names, list)
        self.assertGreater(len(feature_names), 0)
        
    def test_get_feature_names_unfitted_raises_error(self):
        """Test that getting feature names before fit raises ValueError."""
        engineer = FeatureEngineer()
        
        with self.assertRaises(ValueError):
            engineer.get_feature_names()
            
    def test_handles_new_categories_in_transform(self):
        """Test that transform handles new categorical values gracefully."""
        # Train with limited categories
        train_data = self.sample_data[self.sample_data['building_class'].isin(['A', 'B'])].copy()
        
        engineer = FeatureEngineer()
        engineer.fit(train_data)
        
        # Test with data containing new category 'C'
        test_data = self.sample_data[self.sample_data['building_class'] == 'C'].copy()
        
        # Should not raise error
        X_test_transformed = engineer.transform(test_data)
        self.assertIsNotNone(X_test_transformed)
        
    def test_consistent_output_shape(self):
        """Test that output shape is consistent between fit and transform."""
        config = FeatureConfig(
            use_temporal=True,
            use_interactions=True,
            use_polynomial=True
        )
        engineer = FeatureEngineer(config=config)
        
        # Split data
        X_train = self.sample_data.iloc[:80].copy()
        X_test = self.sample_data.iloc[80:].copy()
        
        # Fit and transform
        X_train_transformed = engineer.fit_transform(X_train)
        X_test_transformed = engineer.transform(X_test)
        
        # Check same number of columns
        self.assertEqual(X_train_transformed.shape[1], X_test_transformed.shape[1])
        
    def test_all_features_enabled(self):
        """Test with all feature engineering options enabled."""
        config = FeatureConfig(
            use_temporal=True,
            use_interactions=True,
            use_aggregations=True,
            use_polynomial=True,
            polynomial_degree=2,
            scaler_type='robust',
            handle_missing=True
        )
        
        engineer = FeatureEngineer(config=config)
        X_transformed = engineer.fit_transform(self.sample_data.copy())
        
        # Should have significantly more features than input
        self.assertGreater(X_transformed.shape[1], self.sample_data.shape[1] * 2)
        
        # Check no NaN values
        self.assertEqual(X_transformed.isnull().sum().sum(), 0)
        

def run_tests():
    """Run all tests and print results."""
    print("Running FeatureEngineer Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFeatureEngineer)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} error(s) occurred")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
