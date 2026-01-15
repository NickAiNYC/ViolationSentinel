# AI Risk Predictor - Technical Documentation

## Overview

The ViolationSentinel AI Risk Predictor is an enterprise-grade machine learning system for predicting property violation risks using ensemble learning, SHAP explainability, and statistical drift detection.

## Architecture

### Ensemble Learning Strategy

The predictor uses three state-of-the-art machine learning algorithms:

1. **Random Forest** (30% weight)
   - Robust to outliers
   - Handles non-linear relationships
   - Provides feature importance

2. **XGBoost** (40% weight)
   - Gradient boosting for high accuracy
   - Efficient with large datasets
   - Supports SHAP natively

3. **LightGBM** (30% weight)
   - Fast training and prediction
   - Memory efficient
   - Handles categorical features well

### Feature Scaling

Uses **RobustScaler** instead of StandardScaler:
- More resistant to outliers
- Uses median and IQR instead of mean and std
- Critical for real-world property data with extreme values

### Cross-Validation

Implements **TimeSeriesSplit** for temporal data:
- Respects time-based ordering
- Prevents data leakage
- More realistic evaluation for violation predictions

## Features

### Input Features (11 total)

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| `property_age` | Integer | 1-150 | Age of building in years |
| `violation_history_count` | Integer | 0-100 | Total historical violations |
| `days_since_last_violation` | Integer | 1-3650 | Days since most recent violation |
| `neighborhood_risk_score` | Float | 0-1 | Normalized neighborhood risk |
| `total_units` | Integer | 1-1000 | Number of residential units |
| `complaint_frequency` | Float | 0-100 | Average complaints per month |
| `owner_compliance_score` | Float | 0-1 | Historical compliance rating |
| `seasonal_factor` | Float | 0-1 | Seasonal adjustment factor |
| `economic_zone_risk` | Float | 0-1 | Economic risk indicator |
| `flood_zone_risk` | Float | 0-1 | Flood zone risk level |
| `construction_activity_nearby` | Binary | 0/1 | Nearby construction flag |

## Predictions

### Output Structure

```python
@dataclass
class PredictionResult:
    property_id: str                          # Property identifier
    risk_score: float                         # Overall risk (0-100)
    risk_level: str                           # MINIMAL/LOW/MEDIUM/HIGH/CRITICAL
    critical_violation_probability: float     # P(critical violation) [0-1]
    days_until_next_violation: float          # Predicted days until next violation
    recommended_action: str                   # Actionable recommendation
    confidence: float                         # Prediction confidence [0-1]
    feature_importance: Dict[str, float]      # Feature importance scores
    shap_values: Dict[str, float]            # SHAP explainability values
    prediction_timestamp: datetime            # When prediction was made
    model_version: str                        # Model version used
```

### Risk Level Thresholds

- **MINIMAL**: 0-20
- **LOW**: 20-40
- **MEDIUM**: 40-60
- **HIGH**: 60-80
- **CRITICAL**: 80-100

### Risk Score Calculation

```python
risk_score = (critical_probability * 70) + (time_urgency * 30)

where:
  time_urgency = 30 * (1 - days_pred / 365)  # Normalized to [0, 30]
```

## Explainability

### Feature Importance

Average importance across all three models, normalized to sum to 1.0:

```python
importance = (RF_importance + XGB_importance + LGB_importance) / 3
```

### SHAP Values

Uses TreeExplainer from XGBoost model:
- Shows how each feature contributes to the prediction
- Positive values increase risk, negative values decrease risk
- Sorted by absolute impact

Example:
```python
shap_values = {
    'violation_history_count': +0.15,  # Increases risk
    'owner_compliance_score': -0.08,   # Decreases risk
    'neighborhood_risk_score': +0.12,  # Increases risk
    ...
}
```

## Model Drift Detection

### Kolmogorov-Smirnov Test

Statistical test comparing baseline predictions to recent predictions:

```python
drift_detected = p_value < threshold (default: 0.05)
```

- **Baseline**: First 1000 predictions after training
- **Recent**: Last 1000 predictions
- **Frequency**: Checked every 100 predictions

### When Drift is Detected

1. Log warning with KS statistic and p-value
2. Set `metrics.drift_detected = True`
3. Store `metrics.drift_score = KS_statistic`
4. Recommend model retraining

## Confidence Scoring

Confidence based on model agreement:

```python
predictions = [RF_prob, XGB_prob, LGB_prob]
std = standard_deviation(predictions)
confidence = 1.0 - (std * 2)  # Scale to [0, 1]
```

- **High confidence**: All models agree (low std)
- **Low confidence**: Models disagree (high std)

## Model Persistence

### Saving Models

```python
predictor.save_models(version="v1.0")
```

Saves:
- `scaler.pkl` - RobustScaler
- `rf_classifier.pkl` - Random Forest classifier
- `xgb_classifier.pkl` - XGBoost classifier
- `lgb_classifier.pkl` - LightGBM classifier
- `rf_regressor.pkl` - Random Forest regressor
- `xgb_regressor.pkl` - XGBoost regressor
- `lgb_regressor.pkl` - LightGBM regressor
- `metrics.pkl` - Model metrics
- `metadata.pkl` - Version and feature info

### Loading Models

```python
predictor.load_models(version="v1.0")
```

Automatically reinitializes SHAP explainers after loading.

## Usage Examples

### Basic Training and Prediction

```python
from ai.risk_predictor import RiskPredictor
import pandas as pd

# Initialize predictor
predictor = RiskPredictor(model_dir="models/ai")

# Train models
X = pd.DataFrame(...)  # Property features
y_critical = pd.Series(...)  # Binary target
y_days = pd.Series(...)  # Days until violation

cv_scores = predictor.train(X, y_critical, y_days, cv_splits=5)

# Make prediction
features = {
    'property_age': 50,
    'violation_history_count': 5,
    ...
}

result = predictor.predict(features, property_id="PROP-001")
print(f"Risk Score: {result.risk_score}")
print(f"Risk Level: {result.risk_level}")
```

### Batch Prediction

```python
# Predict for multiple properties
property_ids = ["PROP-001", "PROP-002", ...]
results = predictor.predict_batch(X_test, property_ids)

# Analyze portfolio risk
high_risk = [r for r in results if r.risk_level in ['HIGH', 'CRITICAL']]
print(f"High risk properties: {len(high_risk)}")
```

### Monitor Model Performance

```python
# Check for drift
drift_detected, p_value = predictor.detect_drift()
if drift_detected:
    print("Model retraining recommended")

# Get metrics
metrics = predictor.get_metrics()
print(f"Total predictions: {metrics.prediction_count}")
print(f"Average confidence: {metrics.avg_confidence:.2%}")
```

## Performance Considerations

### Training Time

- 500 samples: ~10 seconds
- 5,000 samples: ~60 seconds
- 50,000 samples: ~10 minutes

(On standard CPU, may vary)

### Prediction Time

- Single prediction: ~50ms
- Batch (100 properties): ~2 seconds
- Batch (1000 properties): ~15 seconds

### Memory Usage

- Model storage: ~50MB per version
- Runtime memory: ~200MB
- Scales linearly with training data size

## Production Deployment

### Recommended Setup

1. **Training Pipeline**
   - Schedule weekly retraining
   - Use 6+ months of historical data
   - Validate on most recent 2 months
   - Save with timestamp version

2. **Prediction Service**
   - Load latest model on startup
   - Cache predictions for 24 hours
   - Log all predictions for drift detection
   - Monitor confidence scores

3. **Monitoring**
   - Track drift metrics daily
   - Alert when confidence < 0.7
   - Retrain when drift detected
   - Version control all models

### API Integration Example

```python
from fastapi import FastAPI
from ai.risk_predictor import RiskPredictor

app = FastAPI()
predictor = RiskPredictor()
predictor.load_models(version="latest")

@app.post("/predict")
async def predict_risk(features: dict):
    result = predictor.predict(features)
    return {
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "confidence": result.confidence,
        "recommendation": result.recommended_action
    }
```

## Testing

### Run Tests

```bash
pytest test_ai_predictor.py -v
```

### Test Coverage

- Model training and validation
- Single and batch predictions
- Feature validation
- Risk level mapping
- Drift detection
- Model persistence
- SHAP value calculation
- Feature importance
- Metrics tracking

## Error Handling

### Common Errors

1. **ValueError: Missing required features**
   - Solution: Ensure all 11 features are present

2. **ValueError: Models must be trained before prediction**
   - Solution: Call `train()` before `predict()`

3. **ValueError: Model version not found**
   - Solution: Check version string and model directory

### Logging

All operations are logged with appropriate levels:
- `INFO`: Training progress, predictions
- `WARNING`: Drift detection, missing data
- `ERROR`: Training failures, prediction errors

## Future Enhancements

1. **Deep Learning Integration**
   - Neural network ensemble member
   - LSTM for time series patterns

2. **AutoML Features**
   - Automated hyperparameter tuning
   - Feature engineering pipeline

3. **Real-time Updates**
   - Online learning capabilities
   - Incremental model updates

4. **Advanced Explainability**
   - Counterfactual explanations
   - Anchor explanations

## References

- XGBoost: Chen & Guestrin (2016)
- LightGBM: Ke et al. (2017)
- SHAP: Lundberg & Lee (2017)
- TimeSeriesSplit: Bergmeir & Benítez (2012)

## Support

For issues, questions, or contributions:
- Documentation: `/docs/AI_RISK_PREDICTOR.md`
- Examples: `demo_ai_predictor.py`
- Tests: `test_ai_predictor.py`
- Code: `ai/risk_predictor.py`
