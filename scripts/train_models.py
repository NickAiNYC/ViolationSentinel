#!/usr/bin/env python3
"""
ViolationSentinel Model Training Script

Production-ready script for training AI risk prediction models on historical violation data.
Supports multiple data sources (CSV, JSON, PostgreSQL), feature engineering, hyperparameter tuning,
and comprehensive model evaluation with reporting.

Usage:
    python scripts/train_models.py --data-path data/violations.csv
    python scripts/train_models.py --db-connection postgresql://user:pass@host/db
    python scripts/train_models.py --config config/training_config.yaml
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit
from tqdm import tqdm

# Import ViolationSentinel modules
try:
    from ai.feature_engineering import FeatureEngineer, FeatureConfig
    from ai.risk_predictor import RiskPredictor
except ImportError:
    print("ERROR: Could not import ViolationSentinel modules.")
    print("Ensure you're running from the project root and modules are installed.")
    sys.exit(1)


# Configure logging
def setup_logging(log_dir: Path, verbose: bool = False) -> logging.Logger:
    """
    Set up logging to both console and file.
    
    Args:
        log_dir: Directory to store log files
        verbose: If True, set DEBUG level, else INFO
        
    Returns:
        Configured logger instance
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"training_{timestamp}.log"
    
    logger = logging.getLogger("ViolationSentinel.Training")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger


def load_data(args: argparse.Namespace, logger: logging.Logger) -> pd.DataFrame:
    """
    Load historical violation data from various sources.
    
    Args:
        args: Command-line arguments
        logger: Logger instance
        
    Returns:
        DataFrame with violation data
        
    Raises:
        SystemExit: If data loading fails
    """
    logger.info("Loading data...")
    
    try:
        if args.data_path:
            data_path = Path(args.data_path)
            if not data_path.exists():
                logger.error(f"Data file not found: {data_path}")
                sys.exit(1)
                
            if data_path.suffix == '.csv':
                logger.info(f"Loading CSV from {data_path}")
                df = pd.read_csv(data_path)
            elif data_path.suffix == '.json':
                logger.info(f"Loading JSON from {data_path}")
                df = pd.read_json(data_path)
            else:
                logger.error(f"Unsupported file format: {data_path.suffix}")
                sys.exit(1)
                
        elif args.db_connection:
            logger.info(f"Loading from database: {args.db_connection.split('@')[-1]}")
            import sqlalchemy
            engine = sqlalchemy.create_engine(args.db_connection)
            query = args.db_query or "SELECT * FROM violations"
            df = pd.read_sql(query, engine)
            
        else:
            logger.error("No data source specified. Use --data-path or --db-connection")
            sys.exit(1)
            
        logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        sys.exit(1)


def validate_data(df: pd.DataFrame, logger: logging.Logger) -> None:
    """
    Validate data quality before training.
    
    Args:
        df: Input DataFrame
        logger: Logger instance
        
    Raises:
        SystemExit: If validation fails
    """
    logger.info("Validating data quality...")
    
    required_features = [
        'property_age', 'violation_history_count', 'days_since_last_violation',
        'neighborhood_risk_score', 'total_units', 'complaint_frequency',
        'owner_compliance_score', 'seasonal_factor', 'economic_zone_risk',
        'flood_zone_risk', 'construction_activity_nearby'
    ]
    
    required_targets = ['is_critical_violation', 'days_until_next_violation']
    
    missing_features = [col for col in required_features if col not in df.columns]
    missing_targets = [col for col in required_targets if col not in df.columns]
    
    if missing_features:
        logger.error(f"Missing required features: {missing_features}")
        sys.exit(1)
        
    if missing_targets:
        logger.error(f"Missing required target columns: {missing_targets}")
        sys.exit(1)
    
    # Check for excessive missing values
    missing_pct = (df[required_features].isnull().sum() / len(df) * 100)
    high_missing = missing_pct[missing_pct > 50]
    
    if not high_missing.empty:
        logger.warning(f"High missing value rates detected:")
        for col, pct in high_missing.items():
            logger.warning(f"  {col}: {pct:.1f}%")
    
    # Check data types
    for col in required_features:
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.warning(f"Non-numeric feature detected: {col} ({df[col].dtype})")
    
    logger.info("✓ Data validation passed")


def prepare_features(
    df: pd.DataFrame, 
    args: argparse.Namespace, 
    logger: logging.Logger
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, FeatureEngineer]:
    """
    Prepare features using FeatureEngineer.
    
    Args:
        df: Input DataFrame
        args: Command-line arguments
        logger: Logger instance
        
    Returns:
        Tuple of (X, y_classification, y_regression, feature_engineer)
    """
    logger.info("Engineering features...")
    
    # Configure feature engineering
    config = FeatureConfig(
        use_temporal=args.use_temporal,
        use_interactions=args.use_interactions,
        use_aggregations=args.use_aggregations,
        use_polynomial=args.use_polynomial,
        polynomial_degree=args.polynomial_degree,
        scaler_type=args.scaler_type,
        handle_missing=True
    )
    
    feature_engineer = FeatureEngineer(config=config)
    
    # Extract features and targets
    feature_cols = [
        'property_age', 'violation_history_count', 'days_since_last_violation',
        'neighborhood_risk_score', 'total_units', 'complaint_frequency',
        'owner_compliance_score', 'seasonal_factor', 'economic_zone_risk',
        'flood_zone_risk', 'construction_activity_nearby'
    ]
    
    X_raw = df[feature_cols].copy()
    y_classification = df['is_critical_violation'].values
    y_regression = df['days_until_next_violation'].values
    
    # Add optional temporal columns if available
    if 'inspection_date' in df.columns:
        X_raw['inspection_date'] = pd.to_datetime(df['inspection_date'])
    if 'building_class' in df.columns:
        X_raw['building_class'] = df['building_class']
    if 'neighborhood' in df.columns:
        X_raw['neighborhood'] = df['neighborhood']
    
    # Fit and transform
    logger.info(f"Original features: {X_raw.shape[1]}")
    with tqdm(total=1, desc="Feature engineering") as pbar:
        X = feature_engineer.fit_transform(X_raw)
        pbar.update(1)
    
    logger.info(f"Engineered features: {X.shape[1]}")
    logger.info(f"Classification target distribution: {np.bincount(y_classification.astype(int))}")
    logger.info(f"Regression target range: [{y_regression.min():.1f}, {y_regression.max():.1f}]")
    
    return X, y_classification, y_regression, feature_engineer


def train_models(
    X: np.ndarray,
    y_classification: np.ndarray,
    y_regression: np.ndarray,
    args: argparse.Namespace,
    logger: logging.Logger
) -> Tuple[RiskPredictor, Dict[str, Any]]:
    """
    Train ensemble models with cross-validation.
    
    Args:
        X: Feature matrix
        y_classification: Classification targets
        y_regression: Regression targets
        args: Command-line arguments
        logger: Logger instance
        
    Returns:
        Tuple of (trained predictor, metrics dict)
    """
    logger.info("Training ensemble models...")
    
    # Initialize predictor
    predictor = RiskPredictor(
        model_dir=args.model_dir,
        cv_splits=args.cv_splits
    )
    
    # Train with progress bar
    with tqdm(total=args.cv_splits, desc="Cross-validation") as pbar:
        def progress_callback(fold: int):
            pbar.update(1)
        
        predictor.train(
            X, 
            y_classification, 
            y_regression,
            cv_splits=args.cv_splits
        )
    
    logger.info("✓ Training completed")
    
    # Calculate comprehensive metrics
    logger.info("Calculating performance metrics...")
    metrics = calculate_metrics(X, y_classification, y_regression, predictor, logger)
    
    return predictor, metrics


def calculate_metrics(
    X: np.ndarray,
    y_classification: np.ndarray,
    y_regression: np.ndarray,
    predictor: RiskPredictor,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics.
    
    Args:
        X: Feature matrix
        y_classification: True classification labels
        y_regression: True regression values
        predictor: Trained predictor
        logger: Logger instance
        
    Returns:
        Dictionary of metrics
    """
    metrics = {}
    
    # Get predictions for all samples
    predictions = []
    logger.info("Generating predictions for evaluation...")
    
    for i in tqdm(range(len(X)), desc="Predicting"):
        result = predictor.predict(X[i:i+1][0])
        predictions.append(result)
    
    # Extract predictions
    y_pred_proba = np.array([p.critical_violation_probability for p in predictions])
    y_pred_class = (y_pred_proba > 0.5).astype(int)
    y_pred_days = np.array([p.days_until_next_violation for p in predictions])
    
    # Classification metrics
    metrics['classification'] = {
        'accuracy': accuracy_score(y_classification, y_pred_class),
        'precision': precision_score(y_classification, y_pred_class, zero_division=0),
        'recall': recall_score(y_classification, y_pred_class, zero_division=0),
        'f1_score': f1_score(y_classification, y_pred_class, zero_division=0),
        'roc_auc': roc_auc_score(y_classification, y_pred_proba)
    }
    
    # Regression metrics
    metrics['regression'] = {
        'mae': mean_absolute_error(y_regression, y_pred_days),
        'rmse': np.sqrt(mean_squared_error(y_regression, y_pred_days)),
        'r2_score': r2_score(y_regression, y_pred_days)
    }
    
    # Log metrics
    logger.info("\n" + "="*60)
    logger.info("CLASSIFICATION METRICS")
    logger.info("="*60)
    for metric, value in metrics['classification'].items():
        logger.info(f"  {metric:20s}: {value:.4f}")
    
    logger.info("\n" + "="*60)
    logger.info("REGRESSION METRICS")
    logger.info("="*60)
    for metric, value in metrics['regression'].items():
        logger.info(f"  {metric:20s}: {value:.4f}")
    logger.info("="*60 + "\n")
    
    return metrics


def save_models(
    predictor: RiskPredictor,
    feature_engineer: FeatureEngineer,
    metrics: Dict[str, Any],
    args: argparse.Namespace,
    logger: logging.Logger
) -> Path:
    """
    Save trained models with versioning.
    
    Args:
        predictor: Trained predictor
        feature_engineer: Fitted feature engineer
        metrics: Performance metrics
        args: Command-line arguments
        logger: Logger instance
        
    Returns:
        Path to saved model
    """
    logger.info("Saving trained models...")
    
    # Create versioned filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version = args.model_version or "1.0.0"
    model_name = f"risk_predictor_v{version}_{timestamp}"
    
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Save predictor
    predictor.save_models(version=model_name)
    logger.info(f"✓ Saved predictor models to {model_dir}/{model_name}")
    
    # Save feature engineer
    fe_path = model_dir / f"feature_engineer_{model_name}.pkl"
    joblib.dump(feature_engineer, fe_path)
    logger.info(f"✓ Saved feature engineer to {fe_path}")
    
    # Save metrics
    metrics_path = model_dir / f"metrics_{model_name}.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"✓ Saved metrics to {metrics_path}")
    
    # Save feature importance
    feature_importance = predictor.get_feature_importance()
    fi_path = model_dir / f"feature_importance_{model_name}.json"
    with open(fi_path, 'w') as f:
        json.dump(feature_importance, f, indent=2)
    logger.info(f"✓ Saved feature importance to {fi_path}")
    
    return model_dir / model_name


def generate_training_report(
    metrics: Dict[str, Any],
    feature_importance: Dict[str, float],
    args: argparse.Namespace,
    logger: logging.Logger
) -> None:
    """
    Generate comprehensive training report.
    
    Args:
        metrics: Performance metrics
        feature_importance: Feature importance scores
        args: Command-line arguments
        logger: Logger instance
    """
    logger.info("Generating training report...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = report_dir / f"training_report_{timestamp}.txt"
    
    with open(report_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write("ViolationSentinel Model Training Report\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model Version: {args.model_version or '1.0.0'}\n")
        f.write(f"Cross-validation Splits: {args.cv_splits}\n\n")
        
        f.write("-"*80 + "\n")
        f.write("CLASSIFICATION METRICS\n")
        f.write("-"*80 + "\n")
        for metric, value in metrics['classification'].items():
            f.write(f"  {metric:20s}: {value:.4f}\n")
        
        f.write("\n" + "-"*80 + "\n")
        f.write("REGRESSION METRICS\n")
        f.write("-"*80 + "\n")
        for metric, value in metrics['regression'].items():
            f.write(f"  {metric:20s}: {value:.4f}\n")
        
        f.write("\n" + "-"*80 + "\n")
        f.write("TOP 10 MOST IMPORTANT FEATURES\n")
        f.write("-"*80 + "\n")
        sorted_features = sorted(
            feature_importance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        for i, (feature, importance) in enumerate(sorted_features, 1):
            f.write(f"  {i:2d}. {feature:40s}: {importance:.4f}\n")
        
        f.write("\n" + "="*80 + "\n")
    
    logger.info(f"✓ Training report saved to {report_path}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Train ViolationSentinel AI risk prediction models",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Data source arguments
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument(
        '--data-path',
        type=str,
        help='Path to CSV or JSON file with violation data'
    )
    data_group.add_argument(
        '--db-connection',
        type=str,
        help='Database connection string (e.g., postgresql://user:pass@host/db)'
    )
    
    parser.add_argument(
        '--db-query',
        type=str,
        help='SQL query to fetch data (default: SELECT * FROM violations)'
    )
    
    # Feature engineering arguments
    parser.add_argument(
        '--use-temporal',
        action='store_true',
        default=True,
        help='Use temporal features (default: True)'
    )
    parser.add_argument(
        '--use-interactions',
        action='store_true',
        default=True,
        help='Use interaction features (default: True)'
    )
    parser.add_argument(
        '--use-aggregations',
        action='store_true',
        default=True,
        help='Use aggregation features (default: True)'
    )
    parser.add_argument(
        '--use-polynomial',
        action='store_true',
        default=False,
        help='Use polynomial features (default: False)'
    )
    parser.add_argument(
        '--polynomial-degree',
        type=int,
        default=2,
        help='Polynomial feature degree (default: 2)'
    )
    parser.add_argument(
        '--scaler-type',
        type=str,
        choices=['robust', 'standard'],
        default='robust',
        help='Feature scaling method (default: robust)'
    )
    
    # Training arguments
    parser.add_argument(
        '--cv-splits',
        type=int,
        default=5,
        help='Number of cross-validation splits (default: 5)'
    )
    parser.add_argument(
        '--model-version',
        type=str,
        help='Model version string (default: auto-generated)'
    )
    
    # Output arguments
    parser.add_argument(
        '--model-dir',
        type=str,
        default='models/ai',
        help='Directory to save trained models (default: models/ai)'
    )
    parser.add_argument(
        '--report-dir',
        type=str,
        default='reports',
        help='Directory to save training reports (default: reports)'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Directory to save log files (default: logs)'
    )
    
    # Misc arguments
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(Path(args.log_dir), args.verbose)
    
    logger.info("="*60)
    logger.info("ViolationSentinel Model Training Pipeline")
    logger.info("="*60)
    
    try:
        # Step 1: Load data
        df = load_data(args, logger)
        
        # Step 2: Validate data
        validate_data(df, logger)
        
        # Step 3: Prepare features
        X, y_classification, y_regression, feature_engineer = prepare_features(
            df, args, logger
        )
        
        # Step 4: Train models
        predictor, metrics = train_models(
            X, y_classification, y_regression, args, logger
        )
        
        # Step 5: Save models
        model_path = save_models(
            predictor, feature_engineer, metrics, args, logger
        )
        
        # Step 6: Generate report
        feature_importance = predictor.get_feature_importance()
        generate_training_report(metrics, feature_importance, args, logger)
        
        logger.info("\n" + "="*60)
        logger.info("✓ TRAINING COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info(f"Models saved to: {model_path}")
        logger.info(f"Classification ROC-AUC: {metrics['classification']['roc_auc']:.4f}")
        logger.info(f"Regression RMSE: {metrics['regression']['rmse']:.2f} days")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("\nTraining interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"\nTraining failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
