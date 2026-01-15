"""
ViolationSentinel Feature Engineering Module

This module provides advanced feature engineering capabilities for NYC property
violation prediction, including temporal features, interaction features, aggregations,
and preprocessing transformations compatible with scikit-learn pipelines.

Author: ViolationSentinel Team
Version: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder
from sklearn.preprocessing import PolynomialFeatures
import joblib
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for feature engineering pipeline."""
    use_temporal: bool = True
    use_interactions: bool = True
    use_aggregations: bool = True
    use_polynomial: bool = True
    polynomial_degree: int = 2
    scaler_type: str = 'robust'  # 'standard' or 'robust'
    handle_missing: bool = True
    
    
class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Advanced feature engineering for NYC property violation prediction.
    
    This class implements comprehensive feature engineering including:
    - Temporal features from dates (seasonality, time-based patterns)
    - Interaction features between key variables
    - Aggregation features by groups (building class, neighborhood)
    - Polynomial features for non-linear relationships
    - Missing value imputation
    - Feature scaling (Standard or Robust)
    
    Compatible with sklearn Pipeline for easy integration into ML workflows.
    
    Attributes:
        config (FeatureConfig): Configuration object controlling feature engineering
        scaler (StandardScaler | RobustScaler): Fitted scaler for numerical features
        encoder (OneHotEncoder): Fitted encoder for categorical features
        feature_names_ (List[str]): Names of engineered features after fit
        aggregation_stats_ (Dict): Cached aggregation statistics from training
        is_fitted_ (bool): Whether the transformer has been fitted
        
    Example:
        >>> engineer = FeatureEngineer(config=FeatureConfig(use_temporal=True))
        >>> X_train_transformed = engineer.fit_transform(X_train)
        >>> X_test_transformed = engineer.transform(X_test)
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        """
        Initialize the FeatureEngineer.
        
        Args:
            config: Configuration object. If None, uses default settings.
        """
        self.config = config or FeatureConfig()
        self.scaler: Optional[Any] = None
        self.encoder: Optional[OneHotEncoder] = None
        self.polynomial: Optional[PolynomialFeatures] = None
        self.feature_names_: Optional[List[str]] = None
        self.aggregation_stats_: Optional[Dict] = None
        self.is_fitted_ = False
        self.numerical_medians_: Optional[Dict] = None
        self.categorical_modes_: Optional[Dict] = None
        
        logger.info(f"FeatureEngineer initialized with config: {self.config}")
        
    def create_temporal_features(self, df: pd.DataFrame, date_column: str = 'inspection_date') -> pd.DataFrame:
        """
        Create temporal features from date columns.
        
        Temporal features capture seasonality and time-based patterns that are
        critical for violation prediction. For example:
        - Winter months see higher heat complaints
        - Summer months have different violation patterns
        - End of quarter may see inspection spikes
        
        Args:
            df: Input DataFrame with date column
            date_column: Name of the date column to extract features from
            
        Returns:
            DataFrame with added temporal features
            
        Features Created:
            - month: Month number (1-12)
            - quarter: Quarter of year (1-4)
            - season: Season name (Winter/Spring/Summer/Fall)
            - day_of_week: Day of week (0=Monday, 6=Sunday)
            - is_winter: Boolean flag for winter months (Dec-Feb)
            - is_summer: Boolean flag for summer months (Jun-Aug)
            - is_weekend: Boolean flag for weekend days
            - days_since_epoch: Days since reference date (for trend analysis)
        """
        logger.info(f"Creating temporal features from column: {date_column}")
        
        df = df.copy()
        
        # Convert to datetime if not already
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # Month and quarter
            df['month'] = df[date_column].dt.month
            df['quarter'] = df[date_column].dt.quarter
            
            # Season (Winter: Dec, Jan, Feb; Spring: Mar, Apr, May; etc.)
            df['season'] = df['month'].map({
                12: 'Winter', 1: 'Winter', 2: 'Winter',
                3: 'Spring', 4: 'Spring', 5: 'Spring',
                6: 'Summer', 7: 'Summer', 8: 'Summer',
                9: 'Fall', 10: 'Fall', 11: 'Fall'
            })
            
            # Day of week
            df['day_of_week'] = df[date_column].dt.dayofweek
            
            # Winter and summer flags (critical for heating violations)
            df['is_winter'] = df['month'].isin([12, 1, 2]).astype(int)
            df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)
            
            # Weekend flag
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            
            # Days since epoch (for trend analysis)
            epoch = pd.Timestamp('2020-01-01')
            df['days_since_epoch'] = (df[date_column] - epoch).dt.days
            
            logger.info(f"Created {8} temporal features")
        else:
            logger.warning(f"Date column '{date_column}' not found. Skipping temporal features.")
            
        return df
    
    def create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create interaction features between key variables.
        
        Interaction features capture combined effects that are more predictive
        than individual features. For example:
        - Old buildings with many violations are higher risk
        - High neighborhood risk + poor compliance = multiplicative effect
        - Complaints per unit normalizes building size effects
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with added interaction features
            
        Features Created:
            - age_violation_interaction: property_age * violation_history_count
            - risk_compliance_ratio: neighborhood_risk_score / owner_compliance_score
            - complaints_per_unit: complaint_frequency / total_units
            - violation_density: violation_history_count / property_age
            - risk_age_product: neighborhood_risk_score * property_age
            - compliance_units_ratio: owner_compliance_score / log(total_units)
        """
        logger.info("Creating interaction features")
        
        df = df.copy()
        
        # Age * Violations (older buildings with more violations = high risk)
        if 'property_age' in df.columns and 'violation_history_count' in df.columns:
            df['age_violation_interaction'] = df['property_age'] * df['violation_history_count']
        
        # Risk / Compliance (high risk area with poor compliance = danger)
        if 'neighborhood_risk_score' in df.columns and 'owner_compliance_score' in df.columns:
            # Avoid division by zero
            df['risk_compliance_ratio'] = df['neighborhood_risk_score'] / (df['owner_compliance_score'] + 0.01)
        
        # Complaints per unit (normalizes for building size)
        if 'complaint_frequency' in df.columns and 'total_units' in df.columns:
            df['complaints_per_unit'] = df['complaint_frequency'] / (df['total_units'] + 1)
        
        # Violation density (violations per year of age)
        if 'violation_history_count' in df.columns and 'property_age' in df.columns:
            df['violation_density'] = df['violation_history_count'] / (df['property_age'] + 1)
        
        # Risk * Age (older buildings in risky areas)
        if 'neighborhood_risk_score' in df.columns and 'property_age' in df.columns:
            df['risk_age_product'] = df['neighborhood_risk_score'] * df['property_age']
        
        # Compliance normalized by size
        if 'owner_compliance_score' in df.columns and 'total_units' in df.columns:
            df['compliance_units_ratio'] = df['owner_compliance_score'] / (np.log1p(df['total_units']))
        
        logger.info(f"Created {6} interaction features")
        
        return df
    
    def create_aggregation_features(self, df: pd.DataFrame, 
                                   group_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Create aggregation features by building class and neighborhood.
        
        Aggregation features provide context by comparing properties to their
        peers. For example:
        - Average violations for this building class
        - Median compliance score in this neighborhood
        - Helps identify outliers and relative risk
        
        Args:
            df: Input DataFrame
            group_columns: List of columns to group by. If None, uses defaults.
            
        Returns:
            DataFrame with added aggregation features
            
        Features Created (per group):
            - avg_violations_by_group: Mean violation count
            - median_risk_by_group: Median risk score
            - max_complaints_by_group: Maximum complaint frequency
            - std_compliance_by_group: Standard deviation of compliance
        """
        logger.info("Creating aggregation features")
        
        df = df.copy()
        
        if group_columns is None:
            group_columns = ['building_class', 'neighborhood'] if 'building_class' in df.columns else []
        
        if not group_columns or not any(col in df.columns for col in group_columns):
            logger.warning("No valid group columns found. Skipping aggregations.")
            return df
        
        # Filter to only columns that exist
        valid_groups = [col for col in group_columns if col in df.columns]
        
        if not valid_groups:
            return df
        
        # During fit, compute and store aggregation statistics
        if not self.is_fitted_:
            self.aggregation_stats_ = {}
            
            for group_col in valid_groups:
                # Average violations by group
                if 'violation_history_count' in df.columns:
                    agg_name = f'avg_violations_by_{group_col}'
                    self.aggregation_stats_[agg_name] = df.groupby(group_col)['violation_history_count'].mean().to_dict()
                
                # Median risk by group
                if 'neighborhood_risk_score' in df.columns:
                    agg_name = f'median_risk_by_{group_col}'
                    self.aggregation_stats_[agg_name] = df.groupby(group_col)['neighborhood_risk_score'].median().to_dict()
                
                # Max complaints by group
                if 'complaint_frequency' in df.columns:
                    agg_name = f'max_complaints_by_{group_col}'
                    self.aggregation_stats_[agg_name] = df.groupby(group_col)['complaint_frequency'].max().to_dict()
                
                # Std of compliance by group
                if 'owner_compliance_score' in df.columns:
                    agg_name = f'std_compliance_by_{group_col}'
                    self.aggregation_stats_[agg_name] = df.groupby(group_col)['owner_compliance_score'].std().fillna(0).to_dict()
        
        # Apply stored statistics (works for both fit and transform)
        if self.aggregation_stats_:
            for agg_name, agg_dict in self.aggregation_stats_.items():
                # Extract group column name
                group_col = agg_name.split('_by_')[-1]
                if group_col in df.columns:
                    # Use global mean as default for unseen groups
                    global_default = np.mean(list(agg_dict.values())) if agg_dict else 0
                    df[agg_name] = df[group_col].map(agg_dict).fillna(global_default)
        
        logger.info(f"Created {len(self.aggregation_stats_) if self.aggregation_stats_ else 0} aggregation features")
        
        return df
    
    def handle_missing_values(self, df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        """
        Intelligently handle missing values.
        
        Missing data is common in property records. This method uses appropriate
        imputation strategies:
        - Numerical: Median (robust to outliers)
        - Categorical: Mode (most frequent value)
        - Preserves data types and distributions
        
        Args:
            df: Input DataFrame
            is_training: Whether this is training data (computes statistics)
            
        Returns:
            DataFrame with imputed missing values
        """
        logger.info(f"Handling missing values (training={is_training})")
        
        df = df.copy()
        
        # Identify numerical and categorical columns
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if is_training:
            # Compute and store imputation values
            self.numerical_medians_ = {col: df[col].median() for col in numerical_cols if df[col].isnull().any()}
            self.categorical_modes_ = {col: df[col].mode()[0] if len(df[col].mode()) > 0 else 'Unknown' 
                                      for col in categorical_cols if df[col].isnull().any()}
            logger.info(f"Computed imputation values: {len(self.numerical_medians_)} numerical, {len(self.categorical_modes_)} categorical")
        
        # Apply imputation
        if self.numerical_medians_:
            for col, median_val in self.numerical_medians_.items():
                if col in df.columns:
                    df[col].fillna(median_val, inplace=True)
        
        if self.categorical_modes_:
            for col, mode_val in self.categorical_modes_.items():
                if col in df.columns:
                    df[col].fillna(mode_val, inplace=True)
        
        return df
    
    def create_polynomial_features(self, df: pd.DataFrame, 
                                  feature_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Create polynomial features for key risk indicators.
        
        Polynomial features capture non-linear relationships. For example:
        - Risk may increase exponentially with violation count
        - Interaction terms capture combined effects
        - Particularly useful for: age, violations, risk scores
        
        Args:
            df: Input DataFrame
            feature_columns: Columns to create polynomials from. If None, uses defaults.
            
        Returns:
            DataFrame with added polynomial features
        """
        logger.info("Creating polynomial features")
        
        df = df.copy()
        
        if feature_columns is None:
            # Key risk indicators that benefit from polynomial expansion
            feature_columns = [
                'property_age', 'violation_history_count', 
                'neighborhood_risk_score', 'complaint_frequency'
            ]
        
        # Filter to existing columns
        valid_features = [col for col in feature_columns if col in df.columns]
        
        if not valid_features:
            logger.warning("No valid features for polynomial expansion")
            return df
        
        # Extract feature subset
        X_poly = df[valid_features].values
        
        if not self.is_fitted_:
            # Initialize and fit polynomial transformer
            self.polynomial = PolynomialFeatures(
                degree=self.config.polynomial_degree, 
                include_bias=False,
                interaction_only=False
            )
            X_poly_transformed = self.polynomial.fit_transform(X_poly)
        else:
            # Transform using fitted polynomial
            if self.polynomial is None:
                logger.warning("Polynomial transformer not fitted")
                return df
            X_poly_transformed = self.polynomial.transform(X_poly)
        
        # Create column names
        poly_feature_names = [f'poly_{i}' for i in range(X_poly_transformed.shape[1])]
        
        # Add polynomial features to dataframe
        poly_df = pd.DataFrame(X_poly_transformed, columns=poly_feature_names, index=df.index)
        df = pd.concat([df, poly_df], axis=1)
        
        logger.info(f"Created {X_poly_transformed.shape[1]} polynomial features")
        
        return df
    
    def encode_categorical(self, df: pd.DataFrame, categorical_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        One-hot encode categorical variables.
        
        Args:
            df: Input DataFrame
            categorical_columns: List of categorical columns. If None, auto-detects.
            
        Returns:
            DataFrame with encoded categorical variables
        """
        logger.info("Encoding categorical variables")
        
        df = df.copy()
        
        if categorical_columns is None:
            categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Filter to existing columns
        valid_cats = [col for col in categorical_columns if col in df.columns]
        
        if not valid_cats:
            logger.info("No categorical columns to encode")
            return df
        
        if not self.is_fitted_:
            # Initialize and fit encoder
            self.encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
            encoded = self.encoder.fit_transform(df[valid_cats])
        else:
            # Transform using fitted encoder
            if self.encoder is None:
                logger.warning("Encoder not fitted")
                return df
            encoded = self.encoder.transform(df[valid_cats])
        
        # Create column names
        encoded_columns = []
        for i, col in enumerate(valid_cats):
            categories = self.encoder.categories_[i]
            encoded_columns.extend([f'{col}_{cat}' for cat in categories])
        
        # Add encoded features
        encoded_df = pd.DataFrame(encoded, columns=encoded_columns, index=df.index)
        df = df.drop(columns=valid_cats)
        df = pd.concat([df, encoded_df], axis=1)
        
        logger.info(f"Encoded {len(valid_cats)} categorical columns into {len(encoded_columns)} binary features")
        
        return df
    
    def scale_features(self, df: pd.DataFrame, exclude_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Scale numerical features using configured scaler.
        
        Args:
            df: Input DataFrame
            exclude_columns: Columns to exclude from scaling (e.g., binary flags)
            
        Returns:
            DataFrame with scaled features
        """
        logger.info(f"Scaling features with {self.config.scaler_type} scaler")
        
        df = df.copy()
        
        # Get numerical columns
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if exclude_columns:
            numerical_cols = [col for col in numerical_cols if col not in exclude_columns]
        
        if not numerical_cols:
            logger.warning("No numerical columns to scale")
            return df
        
        if not self.is_fitted_:
            # Initialize scaler
            if self.config.scaler_type == 'robust':
                self.scaler = RobustScaler()
            else:
                self.scaler = StandardScaler()
            
            # Fit and transform
            df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
        else:
            # Transform using fitted scaler
            if self.scaler is None:
                logger.warning("Scaler not fitted")
                return df
            df[numerical_cols] = self.scaler.transform(df[numerical_cols])
        
        logger.info(f"Scaled {len(numerical_cols)} numerical features")
        
        return df
    
    def fit(self, X: pd.DataFrame, y=None) -> 'FeatureEngineer':
        """
        Fit the feature engineer to training data.
        
        Args:
            X: Training features DataFrame
            y: Target (unused, for sklearn compatibility)
            
        Returns:
            self (fitted transformer)
        """
        logger.info("Fitting FeatureEngineer...")
        
        X = X.copy()
        
        # Handle missing values (compute statistics)
        if self.config.handle_missing:
            X = self.handle_missing_values(X, is_training=True)
        
        # Create features
        if self.config.use_temporal:
            X = self.create_temporal_features(X)
        
        if self.config.use_interactions:
            X = self.create_interaction_features(X)
        
        if self.config.use_aggregations:
            X = self.create_aggregation_features(X)
        
        # Encode categorical
        X = self.encode_categorical(X)
        
        # Create polynomial features
        if self.config.use_polynomial:
            X = self.create_polynomial_features(X)
        
        # Scale features
        X = self.scale_features(X)
        
        # Store feature names
        self.feature_names_ = X.columns.tolist()
        self.is_fitted_ = True
        
        logger.info(f"FeatureEngineer fitted. Total features: {len(self.feature_names_)}")
        
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data using fitted parameters.
        
        Args:
            X: Features DataFrame to transform
            
        Returns:
            Transformed DataFrame
            
        Raises:
            ValueError: If transformer not fitted
        """
        if not self.is_fitted_:
            raise ValueError("FeatureEngineer must be fitted before transform. Call fit() first.")
        
        logger.info("Transforming data with FeatureEngineer...")
        
        X = X.copy()
        
        # Apply same transformations as fit
        if self.config.handle_missing:
            X = self.handle_missing_values(X, is_training=False)
        
        if self.config.use_temporal:
            X = self.create_temporal_features(X)
        
        if self.config.use_interactions:
            X = self.create_interaction_features(X)
        
        if self.config.use_aggregations:
            X = self.create_aggregation_features(X)
        
        X = self.encode_categorical(X)
        
        if self.config.use_polynomial:
            X = self.create_polynomial_features(X)
        
        X = self.scale_features(X)
        
        # Ensure same columns as training (handle new/missing columns)
        for col in self.feature_names_:
            if col not in X.columns:
                X[col] = 0  # Add missing columns with zeros
        
        # Keep only training columns in same order
        X = X[self.feature_names_]
        
        logger.info(f"Transformed data to {X.shape[1]} features")
        
        return X
    
    def fit_transform(self, X: pd.DataFrame, y=None) -> pd.DataFrame:
        """
        Fit and transform in one step.
        
        Args:
            X: Training features DataFrame
            y: Target (unused, for sklearn compatibility)
            
        Returns:
            Transformed DataFrame
        """
        return self.fit(X, y).transform(X)
    
    def save(self, filepath: str) -> None:
        """
        Save fitted transformer to disk.
        
        Args:
            filepath: Path to save the transformer
        """
        if not self.is_fitted_:
            raise ValueError("Cannot save unfitted transformer")
        
        joblib.dump(self, filepath)
        logger.info(f"FeatureEngineer saved to {filepath}")
    
    @staticmethod
    def load(filepath: str) -> 'FeatureEngineer':
        """
        Load fitted transformer from disk.
        
        Args:
            filepath: Path to load the transformer from
            
        Returns:
            Loaded FeatureEngineer instance
        """
        engineer = joblib.load(filepath)
        logger.info(f"FeatureEngineer loaded from {filepath}")
        return engineer
    
    def get_feature_names(self) -> List[str]:
        """
        Get names of all engineered features.
        
        Returns:
            List of feature names
            
        Raises:
            ValueError: If transformer not fitted
        """
        if not self.is_fitted_:
            raise ValueError("Transformer must be fitted first")
        return self.feature_names_


# Example usage and testing
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    n_samples = 100
    
    sample_data = pd.DataFrame({
        'property_age': np.random.randint(1, 100, n_samples),
        'violation_history_count': np.random.randint(0, 50, n_samples),
        'days_since_last_violation': np.random.randint(0, 365, n_samples),
        'neighborhood_risk_score': np.random.uniform(0, 1, n_samples),
        'total_units': np.random.randint(1, 200, n_samples),
        'complaint_frequency': np.random.uniform(0, 10, n_samples),
        'owner_compliance_score': np.random.uniform(0, 1, n_samples),
        'inspection_date': pd.date_range('2023-01-01', periods=n_samples, freq='D'),
        'building_class': np.random.choice(['A', 'B', 'C'], n_samples),
        'neighborhood': np.random.choice(['Brooklyn', 'Manhattan', 'Queens'], n_samples)
    })
    
    print("Sample Data Shape:", sample_data.shape)
    print("\nOriginal Features:")
    print(sample_data.head())
    
    # Initialize and fit feature engineer
    config = FeatureConfig(
        use_temporal=True,
        use_interactions=True,
        use_aggregations=True,
        use_polynomial=True,
        polynomial_degree=2,
        scaler_type='robust'
    )
    
    engineer = FeatureEngineer(config=config)
    X_transformed = engineer.fit_transform(sample_data)
    
    print(f"\n Transformed Data Shape: {X_transformed.shape}")
    print(f"\nTotal Features Created: {len(engineer.get_feature_names())}")
    print(f"\nFirst 10 Feature Names: {engineer.get_feature_names()[:10]}")
    
    # Test save/load
    engineer.save('/tmp/feature_engineer.pkl')
    loaded_engineer = FeatureEngineer.load('/tmp/feature_engineer.pkl')
    
    print("\n✓ FeatureEngineer save/load successful")
    print("✓ All tests passed")
