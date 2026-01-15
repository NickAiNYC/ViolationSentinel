# Model Training Script Documentation

## Overview

`scripts/train_models.py` is a production-ready script for training ViolationSentinel's AI risk prediction models on historical violation data. It provides comprehensive data loading, feature engineering, model training, evaluation, and persistence capabilities.

## Features

### Data Loading
- **CSV Support**: Load data from CSV files
- **JSON Support**: Load data from JSON files  
- **PostgreSQL Support**: Load data directly from database
- **Validation**: Comprehensive data quality checks before training

### Feature Engineering
- **Temporal Features**: Month, quarter, season, day of week
- **Interaction Features**: Age-violation interactions, risk ratios
- **Aggregation Features**: Group-based statistics
- **Polynomial Features**: Non-linear transformations
- **Configurable**: Enable/disable feature types via CLI

### Model Training
- **Ensemble Learning**: RandomForest, XGBoost, LightGBM
- **Cross-Validation**: TimeSeriesSplit for temporal data
- **Dual Task**: Classification (critical violation) + Regression (days until violation)
- **Progress Tracking**: tqdm progress bars

### Evaluation
- **Classification Metrics**: Accuracy, Precision, Recall, F1-Score, ROC-AUC
- **Regression Metrics**: MAE, RMSE, R²
- **Feature Importance**: Extract and save feature rankings
- **Comprehensive Reports**: Detailed training reports

### Model Persistence
- **Versioning**: Timestamped model versions
- **Complete Save**: Models, scaler, feature engineer, metrics
- **Production Ready**: Easy loading for inference

### Logging
- **Dual Output**: Console + file logging
- **Configurable**: INFO or DEBUG levels
- **Timestamped**: Unique log file per run

## Installation

```bash
# Install dependencies
pip install -r requirements-v1.txt

# Verify installation
python -c "import sklearn, xgboost, lightgbm, shap; print('✓ All dependencies installed')"
```

## Usage

### Basic Usage (CSV)

```bash
python scripts/train_models.py \
    --data-path data/violations.csv
```

### Advanced Usage (All Options)

```bash
python scripts/train_models.py \
    --data-path data/violations.csv \
    --use-temporal \
    --use-interactions \
    --use-aggregations \
    --use-polynomial \
    --polynomial-degree 2 \
    --scaler-type robust \
    --cv-splits 5 \
    --model-version 2.1.0 \
    --model-dir models/ai \
    --report-dir reports \
    --log-dir logs \
    --verbose
```

### Database Loading

```bash
python scripts/train_models.py \
    --db-connection "postgresql://user:pass@localhost/violations" \
    --db-query "SELECT * FROM violations WHERE created_at > '2024-01-01'"
```

### JSON Loading

```bash
python scripts/train_models.py \
    --data-path data/violations.json
```

## Command-Line Arguments

### Data Source (Required, Mutually Exclusive)

| Argument | Type | Description |
|----------|------|-------------|
| `--data-path` | str | Path to CSV or JSON file |
| `--db-connection` | str | PostgreSQL connection string |
| `--db-query` | str | Custom SQL query (default: SELECT * FROM violations) |

### Feature Engineering

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-temporal` | flag | True | Enable temporal features (month, season, etc.) |
| `--use-interactions` | flag | True | Enable interaction features (age×violations, etc.) |
| `--use-aggregations` | flag | True | Enable group-based aggregations |
| `--use-polynomial` | flag | False | Enable polynomial features |
| `--polynomial-degree` | int | 2 | Polynomial feature degree |
| `--scaler-type` | str | robust | Scaling method: 'robust' or 'standard' |

### Training

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--cv-splits` | int | 5 | Number of cross-validation folds |
| `--model-version` | str | auto | Version string (e.g., "2.1.0") |

### Output

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--model-dir` | str | models/ai | Directory for saved models |
| `--report-dir` | str | reports | Directory for training reports |
| `--log-dir` | str | logs | Directory for log files |
| `--verbose` | flag | False | Enable DEBUG-level logging |

## Required Data Format

### Input DataFrame Columns

**Features (Required)**:
- `property_age` (int): Building age in years
- `violation_history_count` (int): Total historical violations
- `days_since_last_violation` (int): Days since last violation
- `neighborhood_risk_score` (float): Area risk score (0-1)
- `total_units` (int): Number of units in building
- `complaint_frequency` (float): Average complaints per month
- `owner_compliance_score` (float): Historical compliance (0-1)
- `seasonal_factor` (float): Seasonal adjustment (0-1)
- `economic_zone_risk` (float): Economic risk indicator (0-1)
- `flood_zone_risk` (float): Flood zone level (0-1)
- `construction_activity_nearby` (int): Binary indicator (0/1)

**Targets (Required)**:
- `is_critical_violation` (int): Binary label (0/1)
- `days_until_next_violation` (int): Days until next violation

**Optional Columns** (for enhanced feature engineering):
- `inspection_date` (datetime): Date of inspection
- `building_class` (str): Building classification
- `neighborhood` (str): Neighborhood name

### Example CSV Format

```csv
property_age,violation_history_count,days_since_last_violation,neighborhood_risk_score,total_units,complaint_frequency,owner_compliance_score,seasonal_factor,economic_zone_risk,flood_zone_risk,construction_activity_nearby,is_critical_violation,days_until_next_violation
50,12,45,0.65,24,2.3,0.75,0.8,0.4,0.2,1,1,30
35,5,120,0.42,10,0.8,0.90,0.6,0.3,0.1,0,0,180
```

## Output Files

### Models

Saved to `{model_dir}/risk_predictor_v{version}_{timestamp}.pkl`:
- 6 trained models (3 classifiers + 3 regressors)
- Fitted RobustScaler
- Model metadata

### Feature Engineer

Saved to `{model_dir}/feature_engineer_{model_name}.pkl`:
- Fitted feature engineering pipeline
- Categorical encoders
- Scaler

### Metrics

Saved to `{model_dir}/metrics_{model_name}.json`:
```json
{
  "classification": {
    "accuracy": 0.8945,
    "precision": 0.8621,
    "recall": 0.8805,
    "f1_score": 0.8712,
    "roc_auc": 0.9234
  },
  "regression": {
    "mae": 32.45,
    "rmse": 45.67,
    "r2_score": 0.7823
  }
}
```

### Feature Importance

Saved to `{model_dir}/feature_importance_{model_name}.json`:
```json
{
  "violation_history_count": 0.2345,
  "property_age": 0.1876,
  "days_since_last_violation": 0.1543,
  ...
}
```

### Training Report

Saved to `{report_dir}/training_report_{timestamp}.txt`:
```
================================================================================
ViolationSentinel Model Training Report
================================================================================

Timestamp: 2026-01-15 22:00:00
Model Version: 1.0.0
Cross-validation Splits: 5

--------------------------------------------------------------------------------
CLASSIFICATION METRICS
--------------------------------------------------------------------------------
  accuracy            : 0.8945
  precision           : 0.8621
  recall              : 0.8805
  f1_score            : 0.8712
  roc_auc             : 0.9234

--------------------------------------------------------------------------------
REGRESSION METRICS
--------------------------------------------------------------------------------
  mae                 : 32.45
  rmse                : 45.67
  r2_score            : 0.7823

--------------------------------------------------------------------------------
TOP 10 MOST IMPORTANT FEATURES
--------------------------------------------------------------------------------
   1. violation_history_count              : 0.2345
   2. property_age                         : 0.1876
   3. days_since_last_violation            : 0.1543
  ...
```

### Logs

Saved to `{log_dir}/training_{timestamp}.log`:
```
2026-01-15 22:00:00 - INFO - Logging initialized
2026-01-15 22:00:01 - INFO - Loading data...
2026-01-15 22:00:02 - INFO - Loaded 5000 records with 13 columns
2026-01-15 22:00:02 - INFO - Validating data quality...
...
```

## Error Handling

### Exit Codes

- **0**: Success
- **1**: General error (data loading, training, etc.)
- **130**: Keyboard interrupt (Ctrl+C)

### Common Errors

**Missing Data File**:
```
ERROR - Data file not found: data/violations.csv
```
**Solution**: Verify file path and existence

**Missing Columns**:
```
ERROR - Missing required features: ['property_age', 'total_units']
```
**Solution**: Ensure all required columns are in the dataset

**Database Connection Failed**:
```
ERROR - Failed to load data: connection refused
```
**Solution**: Verify database connection string and credentials

## Performance Benchmarks

### Training Time (5-fold CV)

| Dataset Size | Temporal | Interactions | Polynomial | Time |
|--------------|----------|--------------|------------|------|
| 500 samples  | ✓ | ✓ | ✗ | ~15s |
| 5,000 samples | ✓ | ✓ | ✗ | ~90s |
| 50,000 samples | ✓ | ✓ | ✗ | ~15min |
| 500 samples  | ✓ | ✓ | ✓ | ~25s |

### Memory Usage

- **Base**: ~200MB
- **With 10k samples**: ~500MB
- **With polynomial features**: ~1GB

## Best Practices

### Data Preparation
1. **Clean data**: Remove duplicates, handle outliers
2. **Balance targets**: Ensure reasonable class balance
3. **Temporal ordering**: Sort by date before saving
4. **Quality checks**: Verify no negative values where inappropriate

### Feature Engineering
1. **Start simple**: Use temporal + interactions first
2. **Add complexity**: Enable polynomial only if needed
3. **Monitor features**: Check feature_importance.json after training
4. **Scale appropriately**: Use 'robust' for NYC data (has outliers)

### Training
1. **Cross-validation**: Use at least 5 folds for reliable estimates
2. **Version control**: Always specify --model-version
3. **Monitor logs**: Check logs for warnings
4. **Validate results**: Review training report carefully

### Production Deployment
1. **Save everything**: Models + feature engineer + scaler
2. **Document version**: Note model version in deployment docs
3. **Track performance**: Monitor predictions vs actuals
4. **Retrain regularly**: Monthly or when drift detected

## Integration Examples

### Load Trained Model

```python
from ai.risk_predictor import RiskPredictor
from ai.feature_engineering import FeatureEngineer
import joblib
import pandas as pd

# Load feature engineer
fe = joblib.load('models/ai/feature_engineer_risk_predictor_v1.0.0_20260115.pkl')

# Load predictor
predictor = RiskPredictor(model_dir='models/ai')
predictor.load_models('risk_predictor_v1.0.0_20260115')

# Prepare new data
new_data = pd.DataFrame([{
    'property_age': 50,
    'violation_history_count': 12,
    ...
}])

X_engineered = fe.transform(new_data)

# Predict
result = predictor.predict(X_engineered[0])
print(f"Risk Score: {result.risk_score}/100")
print(f"Risk Level: {result.risk_level}")
```

### Automated Training Pipeline

```bash
#!/bin/bash
# daily_model_training.sh

# Set variables
DATE=$(date +%Y%m%d)
VERSION="2.0.0"

# Run training
python scripts/train_models.py \
    --data-path data/violations_${DATE}.csv \
    --model-version ${VERSION} \
    --cv-splits 5 \
    --verbose

# Check exit code
if [ $? -eq 0 ]; then
    echo "Training successful"
    # Deploy model
    cp models/ai/risk_predictor_v${VERSION}_* production/models/
else
    echo "Training failed"
    exit 1
fi
```

## Troubleshooting

### Issue: Low ROC-AUC (<0.7)
**Possible Causes**:
- Insufficient data
- Poor feature quality
- Imbalanced classes

**Solutions**:
- Collect more data (aim for >1000 samples)
- Enable --use-polynomial
- Check class balance in logs

### Issue: High RMSE (>100 days)
**Possible Causes**:
- High variance in target
- Outliers in data
- Missing important features

**Solutions**:
- Use --scaler-type robust
- Remove outliers (days > 730)
- Add domain-specific features

### Issue: Training crashes (OOM)
**Possible Causes**:
- Dataset too large
- Polynomial features with many columns

**Solutions**:
- Disable --use-polynomial
- Reduce --cv-splits to 3
- Sample large datasets

## Testing

Run the test suite:

```bash
python test_train_models.py
```

Expected output:
```
Running training script tests...
============================================================
✓ test_data_validation passed
✓ test_data_validation_missing_columns passed
✓ test_feature_preparation passed (features: 17)
✓ test_data_loading_csv passed
✓ test_data_loading_json passed
✓ test_end_to_end_training passed
============================================================
✅ All training script tests passed!
============================================================
```

## Support

For issues or questions:
1. Check this documentation
2. Review logs in `logs/training_*.log`
3. Consult training report in `reports/training_report_*.txt`
4. Open GitHub issue with full error logs

## Changelog

### v1.0.0 (2026-01-15)
- Initial release
- CSV/JSON/PostgreSQL support
- Ensemble learning (RF, XGBoost, LightGBM)
- Comprehensive metrics and reporting
- Production-ready error handling
