"""
Example usage of the ViolationSentinel AI Risk Predictor.

This script demonstrates:
1. Training the ensemble model
2. Making single and batch predictions
3. Model explainability with SHAP
4. Drift detection
5. Model persistence
"""

import pandas as pd
import numpy as np
from ai.risk_predictor import RiskPredictor


def generate_sample_data():
    """Generate realistic sample property data for demonstration."""
    np.random.seed(42)
    n_samples = 500
    
    # Generate synthetic property features
    X = pd.DataFrame({
        'property_age': np.random.randint(5, 100, n_samples),
        'violation_history_count': np.random.poisson(3, n_samples),
        'days_since_last_violation': np.random.randint(1, 730, n_samples),
        'neighborhood_risk_score': np.random.beta(2, 5, n_samples),
        'total_units': np.random.randint(1, 200, n_samples),
        'complaint_frequency': np.random.exponential(2, n_samples),
        'owner_compliance_score': np.random.beta(5, 2, n_samples),
        'seasonal_factor': np.random.uniform(0, 1, n_samples),
        'economic_zone_risk': np.random.beta(2, 3, n_samples),
        'flood_zone_risk': np.random.beta(1, 4, n_samples),
        'construction_activity_nearby': np.random.binomial(1, 0.3, n_samples)
    })
    
    # Generate correlated targets
    # Critical violations are more likely with:
    # - High violation history
    # - Low compliance score
    # - High neighborhood risk
    critical_score = (
        X['violation_history_count'] * 0.3 +
        (1 - X['owner_compliance_score']) * 0.4 +
        X['neighborhood_risk_score'] * 0.3 +
        np.random.normal(0, 0.1, n_samples)
    )
    y_critical = (critical_score > 0.5).astype(int)
    
    # Days until violation inversely related to risk factors
    y_days = (
        365 - 
        X['violation_history_count'] * 15 -
        X['neighborhood_risk_score'] * 200 +
        X['owner_compliance_score'] * 200 -
        X['complaint_frequency'] * 10 +
        np.random.normal(0, 30, n_samples)
    ).clip(1, 730)
    
    return X, y_critical, y_days


def main():
    """Main demonstration function."""
    print("=" * 80)
    print("ViolationSentinel AI Risk Predictor - Demo")
    print("=" * 80)
    print()
    
    # Step 1: Generate sample data
    print("Step 1: Generating sample property data...")
    X, y_critical, y_days = generate_sample_data()
    print(f"  ✓ Generated {len(X)} property records")
    print(f"  ✓ Features: {list(X.columns)}")
    print()
    
    # Step 2: Train the model
    print("Step 2: Training ensemble models...")
    predictor = RiskPredictor(model_dir="models/ai")
    
    # Split into train/test
    train_size = int(0.8 * len(X))
    X_train, X_test = X[:train_size], X[train_size:]
    y_critical_train, y_critical_test = y_critical[:train_size], y_critical[train_size:]
    y_days_train, y_days_test = y_days[:train_size], y_days[train_size:]
    
    cv_scores = predictor.train(
        X_train,
        y_critical_train,
        y_days_train,
        cv_splits=5
    )
    
    print("  ✓ Training completed!")
    print("\n  Cross-validation scores:")
    for metric, score in cv_scores.items():
        print(f"    - {metric}: {score:.4f}")
    print()
    
    # Step 3: Make a single prediction
    print("Step 3: Making a single property prediction...")
    sample_property = {
        'property_age': 45,
        'violation_history_count': 8,
        'days_since_last_violation': 45,
        'neighborhood_risk_score': 0.72,
        'total_units': 35,
        'complaint_frequency': 3.5,
        'owner_compliance_score': 0.55,
        'seasonal_factor': 0.6,
        'economic_zone_risk': 0.65,
        'flood_zone_risk': 0.3,
        'construction_activity_nearby': 1
    }
    
    result = predictor.predict(sample_property, property_id="DEMO-001")
    
    print(f"  Property ID: {result.property_id}")
    print(f"  Risk Score: {result.risk_score:.2f}/100")
    print(f"  Risk Level: {result.risk_level}")
    print(f"  Critical Violation Probability: {result.critical_violation_probability:.2%}")
    print(f"  Days Until Next Violation: {result.days_until_next_violation:.0f}")
    print(f"  Confidence: {result.confidence:.2%}")
    print(f"\n  Recommendation: {result.recommended_action}")
    print()
    
    # Step 4: Show feature importance
    print("Step 4: Feature Importance Analysis...")
    print("  Top 5 most important features:")
    for i, (feature, importance) in enumerate(list(result.feature_importance.items())[:5], 1):
        print(f"    {i}. {feature}: {importance:.3f}")
    print()
    
    # Step 5: Show SHAP values
    print("Step 5: SHAP Values (Model Explainability)...")
    print("  Top 5 features by absolute SHAP impact:")
    for i, (feature, shap_val) in enumerate(list(result.shap_values.items())[:5], 1):
        direction = "increases" if shap_val > 0 else "decreases"
        print(f"    {i}. {feature}: {shap_val:+.3f} ({direction} risk)")
    print()
    
    # Step 6: Batch prediction
    print("Step 6: Batch prediction for portfolio...")
    property_ids = [f"PROP-{i:03d}" for i in range(10)]
    results = predictor.predict_batch(X_test.head(10), property_ids)
    
    print(f"  ✓ Predicted risk for {len(results)} properties")
    print("\n  Portfolio Summary:")
    risk_levels = pd.Series([r.risk_level for r in results]).value_counts()
    for level, count in risk_levels.items():
        print(f"    - {level}: {count} properties")
    
    avg_risk = np.mean([r.risk_score for r in results])
    print(f"\n  Average Risk Score: {avg_risk:.2f}/100")
    print()
    
    # Step 7: Drift detection
    print("Step 7: Model drift detection...")
    drift_detected, p_value = predictor.detect_drift()
    print(f"  Drift Detected: {drift_detected}")
    print(f"  P-value: {p_value:.4f}")
    print()
    
    # Step 8: Save model
    print("Step 8: Saving trained models...")
    save_path = predictor.save_models(version="demo_v1")
    print(f"  ✓ Models saved to: {save_path}")
    print()
    
    # Step 9: Get metrics
    print("Step 9: Model Performance Metrics...")
    metrics = predictor.get_metrics()
    print(f"  Total Predictions: {metrics.prediction_count}")
    print(f"  Average Confidence: {metrics.avg_confidence:.2%}")
    print(f"  Drift Detected: {metrics.drift_detected}")
    print(f"  Last Retrain: {metrics.last_retrain_date}")
    print()
    
    print("=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
