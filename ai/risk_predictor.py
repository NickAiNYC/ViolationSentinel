"""
Enterprise-grade AI Risk Prediction System for ViolationSentinel.

This module implements a production-ready machine learning system for predicting
property violation risks using ensemble learning, model drift detection, and
SHAP explainability.

Author: ViolationSentinel Team
Version: 1.0.0
"""

import logging
import pickle
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import RobustScaler

warnings.filterwarnings('ignore', category=FutureWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """
    Structured prediction result with comprehensive risk assessment.
    
    Attributes:
        property_id: Unique identifier for the property
        risk_score: Overall risk score (0-100)
        risk_level: Risk classification (MINIMAL/LOW/MEDIUM/HIGH/CRITICAL)
        critical_violation_probability: Probability of critical violation (0-1)
        days_until_next_violation: Predicted days until next violation
        recommended_action: Actionable recommendation based on risk
        confidence: Model confidence in prediction (0-1)
        feature_importance: Dictionary of feature names to importance scores
        shap_values: SHAP values for model explainability
        prediction_timestamp: When the prediction was made
        model_version: Version of the model used for prediction
    """
    property_id: str
    risk_score: float
    risk_level: str
    critical_violation_probability: float
    days_until_next_violation: float
    recommended_action: str
    confidence: float
    feature_importance: Dict[str, float]
    shap_values: Dict[str, float]
    prediction_timestamp: datetime = field(default_factory=datetime.now)
    model_version: str = "1.0.0"


@dataclass
class ModelMetrics:
    """
    Tracks model performance metrics over time for drift detection.
    
    Attributes:
        prediction_count: Total number of predictions made
        avg_confidence: Average confidence across predictions
        drift_detected: Whether model drift has been detected
        drift_score: Statistical measure of drift (higher = more drift)
        last_retrain_date: When the model was last retrained
        performance_metrics: Dictionary of performance metrics
    """
    prediction_count: int = 0
    avg_confidence: float = 0.0
    drift_detected: bool = False
    drift_score: float = 0.0
    last_retrain_date: Optional[datetime] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class RiskPredictor:
    """
    Enterprise-grade AI risk prediction system using ensemble learning.
    
    This class implements a production-ready machine learning pipeline for
    predicting property violation risks. It uses ensemble learning (RandomForest,
    XGBoost, LightGBM), RobustScaler for outlier handling, SHAP for explainability,
    and statistical tests for drift detection.
    
    Example:
        >>> predictor = RiskPredictor()
        >>> predictor.train(X_train, y_critical, y_days)
        >>> result = predictor.predict({
        ...     'property_age': 50,
        ...     'violation_history_count': 5,
        ...     'days_since_last_violation': 30,
        ...     # ... other features
        ... })
        >>> print(f"Risk Score: {result.risk_score}")
    """
    
    # Feature names expected by the model
    EXPECTED_FEATURES = [
        'property_age',
        'violation_history_count',
        'days_since_last_violation',
        'neighborhood_risk_score',
        'total_units',
        'complaint_frequency',
        'owner_compliance_score',
        'seasonal_factor',
        'economic_zone_risk',
        'flood_zone_risk',
        'construction_activity_nearby'
    ]
    
    # Risk level thresholds
    RISK_THRESHOLDS = {
        'MINIMAL': 20,
        'LOW': 40,
        'MEDIUM': 60,
        'HIGH': 80,
        'CRITICAL': 100
    }
    
    def __init__(self, model_dir: str = "models/ai"):
        """
        Initialize the RiskPredictor with model storage directory.
        
        Args:
            model_dir: Directory path for saving/loading models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Model components
        self.scaler: Optional[RobustScaler] = None
        self.rf_classifier: Optional[RandomForestClassifier] = None
        self.xgb_classifier: Optional[xgb.XGBClassifier] = None
        self.lgb_classifier: Optional[lgb.LGBMClassifier] = None
        self.rf_regressor: Optional[RandomForestRegressor] = None
        self.xgb_regressor: Optional[xgb.XGBRegressor] = None
        self.lgb_regressor: Optional[lgb.LGBMRegressor] = None
        
        # SHAP explainers
        self.shap_explainer_clf: Optional[shap.Explainer] = None
        self.shap_explainer_reg: Optional[shap.Explainer] = None
        
        # Model metrics and drift detection
        self.metrics = ModelMetrics()
        self.baseline_predictions: List[float] = []
        self.recent_predictions: List[float] = []
        
        # Model version
        self.model_version = "1.0.0"
        
        logger.info(f"RiskPredictor initialized with model directory: {self.model_dir}")
    
    def train(
        self,
        X: pd.DataFrame,
        y_critical: pd.Series,
        y_days: pd.Series,
        cv_splits: int = 5,
        random_state: int = 42
    ) -> Dict[str, float]:
        """
        Train ensemble models with cross-validation and time series split.
        
        Args:
            X: Feature dataframe with property characteristics
            y_critical: Binary target for critical violation (0/1)
            y_days: Continuous target for days until next violation
            cv_splits: Number of cross-validation splits
            random_state: Random seed for reproducibility
            
        Returns:
            Dictionary of cross-validation scores for each model
            
        Raises:
            ValueError: If input data is invalid or missing required features
        """
        logger.info("Starting model training...")
        
        # Validate input
        self._validate_features(X)
        if len(X) != len(y_critical) or len(X) != len(y_days):
            raise ValueError("Feature and target dimensions must match")
        
        # Initialize scaler with RobustScaler (handles outliers better)
        self.scaler = RobustScaler()
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X),
            columns=X.columns,
            index=X.index
        )
        
        # Initialize models with optimized hyperparameters
        logger.info("Initializing ensemble models...")
        
        # Classification models (critical violation prediction)
        self.rf_classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.xgb_classifier = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1,
            eval_metric='logloss'
        )
        
        self.lgb_classifier = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1
        )
        
        # Regression models (days until violation prediction)
        self.rf_regressor = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.xgb_regressor = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.lgb_regressor = lgb.LGBMRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1
        )
        
        # Cross-validation with TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=cv_splits)
        cv_scores = {}
        
        try:
            # Train and evaluate classification models
            logger.info("Training classification models...")
            
            logger.info("  - RandomForest Classifier")
            rf_clf_scores = cross_val_score(
                self.rf_classifier, X_scaled, y_critical,
                cv=tscv, scoring='roc_auc', n_jobs=-1
            )
            cv_scores['rf_classifier_auc'] = rf_clf_scores.mean()
            self.rf_classifier.fit(X_scaled, y_critical)
            
            logger.info("  - XGBoost Classifier")
            xgb_clf_scores = cross_val_score(
                self.xgb_classifier, X_scaled, y_critical,
                cv=tscv, scoring='roc_auc', n_jobs=-1
            )
            cv_scores['xgb_classifier_auc'] = xgb_clf_scores.mean()
            self.xgb_classifier.fit(X_scaled, y_critical)
            
            logger.info("  - LightGBM Classifier")
            lgb_clf_scores = cross_val_score(
                self.lgb_classifier, X_scaled, y_critical,
                cv=tscv, scoring='roc_auc', n_jobs=-1
            )
            cv_scores['lgb_classifier_auc'] = lgb_clf_scores.mean()
            self.lgb_classifier.fit(X_scaled, y_critical)
            
            # Train and evaluate regression models
            logger.info("Training regression models...")
            
            logger.info("  - RandomForest Regressor")
            rf_reg_scores = cross_val_score(
                self.rf_regressor, X_scaled, y_days,
                cv=tscv, scoring='neg_mean_squared_error', n_jobs=-1
            )
            cv_scores['rf_regressor_rmse'] = np.sqrt(-rf_reg_scores.mean())
            self.rf_regressor.fit(X_scaled, y_days)
            
            logger.info("  - XGBoost Regressor")
            xgb_reg_scores = cross_val_score(
                self.xgb_regressor, X_scaled, y_days,
                cv=tscv, scoring='neg_mean_squared_error', n_jobs=-1
            )
            cv_scores['xgb_regressor_rmse'] = np.sqrt(-xgb_reg_scores.mean())
            self.xgb_regressor.fit(X_scaled, y_days)
            
            logger.info("  - LightGBM Regressor")
            lgb_reg_scores = cross_val_score(
                self.lgb_regressor, X_scaled, y_days,
                cv=tscv, scoring='neg_mean_squared_error', n_jobs=-1
            )
            cv_scores['lgb_regressor_rmse'] = np.sqrt(-lgb_reg_scores.mean())
            self.lgb_regressor.fit(X_scaled, y_days)
            
            # Initialize SHAP explainers
            logger.info("Initializing SHAP explainers...")
            self.shap_explainer_clf = shap.TreeExplainer(self.xgb_classifier)
            self.shap_explainer_reg = shap.TreeExplainer(self.xgb_regressor)
            
            # Update metrics
            self.metrics.last_retrain_date = datetime.now()
            self.metrics.performance_metrics = cv_scores
            
            # Store baseline predictions for drift detection
            self.baseline_predictions = self._get_ensemble_predictions(X_scaled)[:, 0].tolist()
            
            logger.info("Training completed successfully!")
            logger.info(f"Cross-validation scores: {cv_scores}")
            
            return cv_scores
            
        except Exception as e:
            logger.error(f"Error during training: {str(e)}", exc_info=True)
            raise
    
    def predict(
        self,
        features: Union[Dict[str, float], pd.DataFrame],
        property_id: str = "unknown"
    ) -> PredictionResult:
        """
        Predict violation risk for a single property.
        
        Args:
            features: Dictionary or DataFrame with property features
            property_id: Unique identifier for the property
            
        Returns:
            PredictionResult with comprehensive risk assessment
            
        Raises:
            ValueError: If models are not trained or features are invalid
        """
        if not self._models_trained():
            raise ValueError("Models must be trained before prediction. Call train() first.")
        
        # Convert dict to DataFrame if necessary
        if isinstance(features, dict):
            features_df = pd.DataFrame([features])
        else:
            features_df = features.copy()
        
        # Validate and prepare features
        self._validate_features(features_df)
        X_scaled = pd.DataFrame(
            self.scaler.transform(features_df),
            columns=features_df.columns
        )
        
        try:
            # Get ensemble predictions
            critical_proba = self._predict_critical_violation(X_scaled)
            days_pred = self._predict_days_until_violation(X_scaled)
            
            # Calculate risk score (0-100)
            risk_score = self._calculate_risk_score(critical_proba, days_pred)
            
            # Determine risk level
            risk_level = self._get_risk_level(risk_score)
            
            # Get recommended action
            recommended_action = self._get_recommendation(risk_level, critical_proba, days_pred)
            
            # Calculate confidence
            confidence = self._calculate_confidence(X_scaled)
            
            # Get feature importance
            feature_importance = self._get_feature_importance()
            
            # Calculate SHAP values
            shap_values = self._calculate_shap_values(X_scaled)
            
            # Create prediction result
            result = PredictionResult(
                property_id=property_id,
                risk_score=float(risk_score),
                risk_level=risk_level,
                critical_violation_probability=float(critical_proba),
                days_until_next_violation=float(days_pred),
                recommended_action=recommended_action,
                confidence=float(confidence),
                feature_importance=feature_importance,
                shap_values=shap_values,
                model_version=self.model_version
            )
            
            # Update metrics and check for drift
            self._update_metrics(result)
            
            logger.debug(f"Prediction completed for property {property_id}: risk_score={risk_score:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during prediction for property {property_id}: {str(e)}", exc_info=True)
            raise
    
    def predict_batch(
        self,
        features_df: pd.DataFrame,
        property_ids: Optional[List[str]] = None
    ) -> List[PredictionResult]:
        """
        Predict violation risk for multiple properties efficiently.
        
        Args:
            features_df: DataFrame with features for multiple properties
            property_ids: Optional list of property IDs (uses index if not provided)
            
        Returns:
            List of PredictionResult objects
            
        Raises:
            ValueError: If models are not trained or features are invalid
        """
        if not self._models_trained():
            raise ValueError("Models must be trained before prediction. Call train() first.")
        
        logger.info(f"Starting batch prediction for {len(features_df)} properties...")
        
        if property_ids is None:
            property_ids = [str(i) for i in features_df.index]
        
        if len(property_ids) != len(features_df):
            raise ValueError("Length of property_ids must match features_df rows")
        
        results = []
        for idx, (prop_id, (_, row)) in enumerate(zip(property_ids, features_df.iterrows())):
            try:
                result = self.predict(row.to_dict(), property_id=prop_id)
                results.append(result)
                
                if (idx + 1) % 100 == 0:
                    logger.info(f"Processed {idx + 1}/{len(features_df)} properties")
                    
            except Exception as e:
                logger.warning(f"Failed to predict for property {prop_id}: {str(e)}")
                continue
        
        logger.info(f"Batch prediction completed: {len(results)}/{len(features_df)} successful")
        return results
    
    def detect_drift(self, threshold: float = 0.05) -> Tuple[bool, float]:
        """
        Detect model drift using Kolmogorov-Smirnov test.
        
        Compares recent predictions to baseline predictions using statistical test.
        
        Args:
            threshold: P-value threshold for drift detection (default: 0.05)
            
        Returns:
            Tuple of (drift_detected: bool, p_value: float)
        """
        if len(self.baseline_predictions) < 30 or len(self.recent_predictions) < 30:
            logger.warning("Insufficient data for drift detection (need 30+ predictions each)")
            return False, 1.0
        
        # Perform Kolmogorov-Smirnov test
        statistic, p_value = stats.ks_2samp(self.baseline_predictions, self.recent_predictions)
        
        drift_detected = bool(p_value < threshold)
        
        if drift_detected:
            logger.warning(f"Model drift detected! KS statistic: {statistic:.4f}, p-value: {p_value:.4f}")
            self.metrics.drift_detected = True
            self.metrics.drift_score = float(statistic)
        else:
            logger.info(f"No drift detected. KS statistic: {statistic:.4f}, p-value: {p_value:.4f}")
        
        return drift_detected, float(p_value)
    
    def save_models(self, version: Optional[str] = None) -> str:
        """
        Save all models and scalers to disk with versioning.
        
        Args:
            version: Optional version string (uses timestamp if not provided)
            
        Returns:
            Path to saved model directory
        """
        if not self._models_trained():
            raise ValueError("No trained models to save")
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        save_dir = self.model_dir / f"v{version}"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save scaler
            joblib.dump(self.scaler, save_dir / "scaler.pkl")
            
            # Save classifiers
            joblib.dump(self.rf_classifier, save_dir / "rf_classifier.pkl")
            joblib.dump(self.xgb_classifier, save_dir / "xgb_classifier.pkl")
            joblib.dump(self.lgb_classifier, save_dir / "lgb_classifier.pkl")
            
            # Save regressors
            joblib.dump(self.rf_regressor, save_dir / "rf_regressor.pkl")
            joblib.dump(self.xgb_regressor, save_dir / "xgb_regressor.pkl")
            joblib.dump(self.lgb_regressor, save_dir / "lgb_regressor.pkl")
            
            # Save metrics
            with open(save_dir / "metrics.pkl", 'wb') as f:
                pickle.dump(self.metrics, f)
            
            # Save metadata
            metadata = {
                'version': version,
                'model_version': self.model_version,
                'saved_at': datetime.now().isoformat(),
                'feature_names': self.EXPECTED_FEATURES
            }
            with open(save_dir / "metadata.pkl", 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Models saved successfully to {save_dir}")
            return str(save_dir)
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}", exc_info=True)
            raise
    
    def load_models(self, version: str) -> None:
        """
        Load models and scalers from disk.
        
        Args:
            version: Version string or timestamp of models to load
        """
        load_dir = self.model_dir / f"v{version}"
        
        if not load_dir.exists():
            raise ValueError(f"Model version {version} not found at {load_dir}")
        
        try:
            # Load scaler
            self.scaler = joblib.load(load_dir / "scaler.pkl")
            
            # Load classifiers
            self.rf_classifier = joblib.load(load_dir / "rf_classifier.pkl")
            self.xgb_classifier = joblib.load(load_dir / "xgb_classifier.pkl")
            self.lgb_classifier = joblib.load(load_dir / "lgb_classifier.pkl")
            
            # Load regressors
            self.rf_regressor = joblib.load(load_dir / "rf_regressor.pkl")
            self.xgb_regressor = joblib.load(load_dir / "xgb_regressor.pkl")
            self.lgb_regressor = joblib.load(load_dir / "lgb_regressor.pkl")
            
            # Load metrics
            with open(load_dir / "metrics.pkl", 'rb') as f:
                self.metrics = pickle.load(f)
            
            # Load metadata
            with open(load_dir / "metadata.pkl", 'rb') as f:
                metadata = pickle.load(f)
                self.model_version = metadata['model_version']
            
            # Reinitialize SHAP explainers
            self.shap_explainer_clf = shap.TreeExplainer(self.xgb_classifier)
            self.shap_explainer_reg = shap.TreeExplainer(self.xgb_regressor)
            
            logger.info(f"Models loaded successfully from {load_dir}")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}", exc_info=True)
            raise
    
    def get_metrics(self) -> ModelMetrics:
        """
        Get current model performance metrics.
        
        Returns:
            ModelMetrics object with current statistics
        """
        return self.metrics
    
    # Private helper methods
    
    def _validate_features(self, X: pd.DataFrame) -> None:
        """Validate that input features match expected schema."""
        missing_features = set(self.EXPECTED_FEATURES) - set(X.columns)
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")
        
        extra_features = set(X.columns) - set(self.EXPECTED_FEATURES)
        if extra_features:
            logger.warning(f"Extra features will be ignored: {extra_features}")
    
    def _models_trained(self) -> bool:
        """Check if all models are trained."""
        return all([
            self.scaler is not None,
            self.rf_classifier is not None,
            self.xgb_classifier is not None,
            self.lgb_classifier is not None,
            self.rf_regressor is not None,
            self.xgb_regressor is not None,
            self.lgb_regressor is not None
        ])
    
    def _get_ensemble_predictions(self, X: pd.DataFrame) -> np.ndarray:
        """Get ensemble predictions from all classifiers."""
        rf_pred = self.rf_classifier.predict_proba(X)
        xgb_pred = self.xgb_classifier.predict_proba(X)
        lgb_pred = self.lgb_classifier.predict_proba(X)
        
        # Average predictions from all models
        ensemble_pred = (rf_pred + xgb_pred + lgb_pred) / 3
        return ensemble_pred
    
    def _predict_critical_violation(self, X: pd.DataFrame) -> float:
        """Predict probability of critical violation using ensemble."""
        rf_prob = self.rf_classifier.predict_proba(X)[0, 1]
        xgb_prob = self.xgb_classifier.predict_proba(X)[0, 1]
        lgb_prob = self.lgb_classifier.predict_proba(X)[0, 1]
        
        # Weighted average (XGBoost gets slightly higher weight)
        ensemble_prob = (0.3 * rf_prob + 0.4 * xgb_prob + 0.3 * lgb_prob)
        return float(ensemble_prob)
    
    def _predict_days_until_violation(self, X: pd.DataFrame) -> float:
        """Predict days until next violation using ensemble."""
        rf_days = self.rf_regressor.predict(X)[0]
        xgb_days = self.xgb_regressor.predict(X)[0]
        lgb_days = self.lgb_regressor.predict(X)[0]
        
        # Weighted average (XGBoost gets slightly higher weight)
        ensemble_days = (0.3 * rf_days + 0.4 * xgb_days + 0.3 * lgb_days)
        
        # Ensure non-negative
        return float(max(0, ensemble_days))
    
    def _calculate_risk_score(self, critical_proba: float, days_pred: float) -> float:
        """Calculate overall risk score (0-100) from predictions."""
        # Risk increases with higher critical probability
        prob_component = critical_proba * 70  # Max 70 points from probability
        
        # Risk increases with shorter time until violation
        # Inverse relationship: fewer days = higher risk
        if days_pred <= 0:
            time_component = 30
        elif days_pred >= 365:
            time_component = 0
        else:
            time_component = 30 * (1 - days_pred / 365)
        
        risk_score = prob_component + time_component
        return float(np.clip(risk_score, 0, 100))
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Map risk score to risk level category."""
        if risk_score < self.RISK_THRESHOLDS['MINIMAL']:
            return 'MINIMAL'
        elif risk_score < self.RISK_THRESHOLDS['LOW']:
            return 'LOW'
        elif risk_score < self.RISK_THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
        elif risk_score < self.RISK_THRESHOLDS['HIGH']:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def _get_recommendation(
        self,
        risk_level: str,
        critical_proba: float,
        days_pred: float
    ) -> str:
        """Generate actionable recommendation based on risk assessment."""
        # Format days prediction based on timeframe
        if days_pred < 30:
            time_desc = f"within {days_pred:.0f} days"
        elif days_pred < 90:
            time_desc = f"in ~{days_pred:.0f} days ({days_pred/30:.1f} months)"
        else:
            time_desc = f"in ~{days_pred/30:.1f} months"
        
        if risk_level == 'CRITICAL':
            return (
                f"IMMEDIATE ACTION REQUIRED: {critical_proba:.1%} probability of critical violation "
                f"{time_desc}. Schedule emergency inspection and address all open violations."
            )
        elif risk_level == 'HIGH':
            return (
                f"High risk detected ({critical_proba:.1%} critical violation probability). "
                f"Next violation expected {time_desc}. Schedule inspection within 7 days and review compliance status."
            )
        elif risk_level == 'MEDIUM':
            return (
                f"Moderate risk level. Next violation expected {time_desc}. "
                "Schedule routine inspection within 30 days."
            )
        elif risk_level == 'LOW':
            return (
                f"Low risk. Next violation not expected for {days_pred/30:.1f} months. "
                "Continue routine monitoring and maintain compliance protocols."
            )
        else:  # MINIMAL
            return (
                f"Minimal risk detected. Property is in good standing (next violation {time_desc}). "
                "Continue standard quarterly inspections."
            )
    
    def _calculate_confidence(self, X: pd.DataFrame) -> float:
        """
        Calculate prediction confidence based on model agreement.
        
        Higher confidence when all models agree, lower when they disagree.
        """
        # Get predictions from all classifiers
        rf_prob = self.rf_classifier.predict_proba(X)[0, 1]
        xgb_prob = self.xgb_classifier.predict_proba(X)[0, 1]
        lgb_prob = self.lgb_classifier.predict_proba(X)[0, 1]
        
        # Calculate standard deviation of predictions
        std = np.std([rf_prob, xgb_prob, lgb_prob])
        
        # Convert to confidence score (lower std = higher confidence)
        # Max std is 0.5 (when one predicts 0 and another 1)
        confidence = 1.0 - (std * 2)  # Scale to [0, 1]
        
        return float(np.clip(confidence, 0, 1))
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get average feature importance across models."""
        # Get importance from each model
        rf_importance = self.rf_classifier.feature_importances_
        xgb_importance = self.xgb_classifier.feature_importances_
        lgb_importance = self.lgb_classifier.feature_importances_
        
        # Average across models
        avg_importance = (rf_importance + xgb_importance + lgb_importance) / 3
        
        # Normalize to sum to 1
        avg_importance = avg_importance / avg_importance.sum()
        
        # Create dictionary
        feature_dict = {
            feature: float(importance)
            for feature, importance in zip(self.EXPECTED_FEATURES, avg_importance)
        }
        
        # Sort by importance
        return dict(sorted(feature_dict.items(), key=lambda x: x[1], reverse=True))
    
    def _calculate_shap_values(self, X: pd.DataFrame) -> Dict[str, float]:
        """Calculate SHAP values for model explainability."""
        try:
            # Calculate SHAP values using XGBoost classifier
            shap_values = self.shap_explainer_clf.shap_values(X)
            
            # Convert to dictionary
            if isinstance(shap_values, list):
                # Binary classification returns list
                shap_values = shap_values[1]  # Use positive class
            
            shap_dict = {
                feature: float(shap_values[0, i])
                for i, feature in enumerate(self.EXPECTED_FEATURES)
            }
            
            # Sort by absolute impact
            return dict(sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True))
            
        except Exception as e:
            logger.warning(f"Error calculating SHAP values: {str(e)}")
            return {feature: 0.0 for feature in self.EXPECTED_FEATURES}
    
    def _update_metrics(self, result: PredictionResult) -> None:
        """Update model metrics and drift detection data."""
        self.metrics.prediction_count += 1
        
        # Update running average of confidence
        n = self.metrics.prediction_count
        self.metrics.avg_confidence = (
            (self.metrics.avg_confidence * (n - 1) + result.confidence) / n
        )
        
        # Store recent predictions for drift detection
        self.recent_predictions.append(result.risk_score)
        
        # Keep only last 1000 predictions
        if len(self.recent_predictions) > 1000:
            self.recent_predictions = self.recent_predictions[-1000:]
        
        # Check for drift every 100 predictions
        if self.metrics.prediction_count % 100 == 0:
            self.detect_drift()
