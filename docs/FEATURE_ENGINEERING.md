# Feature Engineering Documentation

## ViolationSentinel Feature Engineering Module

### Overview

The `FeatureEngineer` class provides comprehensive feature engineering capabilities for NYC property violation prediction. It transforms raw property data into ML-ready features that capture temporal patterns, interactions, and contextual information.

### Key Features

#### 1. **Temporal Features**
Extracts time-based patterns from date columns:
- `month`, `quarter`, `season` - Captures seasonality
- `is_winter`, `is_summer` - Critical for heating violations
- `day_of_week`, `is_weekend` - Inspection scheduling patterns
- `days_since_epoch` - Linear time trend

**Rationale**: Violations show strong seasonal patterns. Heat complaints spike in winter, certain violations increase in summer, and inspection patterns vary by day of week.

#### 2. **Interaction Features**
Creates combined features that capture multiplicative effects:
- `age_violation_interaction` - Old buildings with many violations are exponentially riskier
- `risk_compliance_ratio` - High neighborhood risk + poor compliance = danger
- `complaints_per_unit` - Normalizes complaint frequency by building size
- `violation_density` - Violations per year of building age
- `risk_age_product` - Older buildings in risky areas
- `compliance_units_ratio` - Compliance normalized by building size

**Rationale**: Risk factors don't just add—they multiply. A 100-year-old building with 50 violations is far riskier than the sum of those factors alone.

#### 3. **Aggregation Features**
Provides contextual comparison to peer properties:
- `avg_violations_by_[group]` - Average for this building class/neighborhood
- `median_risk_by_[group]` - Median risk score in peer group
- `max_complaints_by_[group]` - Worst case in group
- `std_compliance_by_[group]` - Variability in compliance

**Rationale**: A property's risk is relative. 10 violations may be normal for commercial buildings but extreme for residential.

#### 4. **Polynomial Features**
Captures non-linear relationships:
- Squares and interactions of key features
- Configurable degree (default: 2)
- Applied to: age, violations, risk scores, complaints

**Rationale**: Risk often increases exponentially. A building with 40 violations is more than 2x as risky as one with 20.

#### 5. **Missing Value Handling**
Intelligent imputation strategies:
- **Numerical**: Median (robust to outliers)
- **Categorical**: Mode (most frequent value)
- Preserves distributions

**Rationale**: NYC property data has gaps. Median imputation is more robust than mean when dealing with extreme values.

#### 6. **Categorical Encoding**
One-hot encoding for categorical variables:
- Building class (A/B/C residential, commercial, mixed)
- Neighborhood/borough
- Handles unseen categories gracefully

**Rationale**: ML models need numerical inputs. One-hot encoding preserves categorical relationships without imposing false ordinality.

#### 7. **Feature Scaling**
Two scaling options:
- **RobustScaler** (default): Uses median and IQR, handles outliers
- **StandardScaler**: Uses mean and std, faster but sensitive to outliers

**Rationale**: NYC property data has extreme outliers. RobustScaler prevents a few mega-buildings from skewing the entire feature space.

### Usage

#### Basic Usage

```python
from ai.feature_engineering import FeatureEngineer, FeatureConfig
import pandas as pd

# Load your data
df = pd.read_csv('property_data.csv')

# Initialize with default settings
engineer = FeatureEngineer()

# Fit on training data
X_train_transformed = engineer.fit_transform(df_train)

# Transform test data
X_test_transformed = engineer.transform(df_test)
```

#### Custom Configuration

```python
# Create custom configuration
config = FeatureConfig(
    use_temporal=True,          # Enable temporal features
    use_interactions=True,      # Enable interaction features
    use_aggregations=True,      # Enable aggregation features
    use_polynomial=True,        # Enable polynomial features
    polynomial_degree=2,        # Degree of polynomial
    scaler_type='robust',       # 'robust' or 'standard'
    handle_missing=True         # Enable missing value imputation
)

engineer = FeatureEngineer(config=config)
X_transformed = engineer.fit_transform(df)
```

#### sklearn Pipeline Integration

```python
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

# Create pipeline
pipeline = Pipeline([
    ('feature_engineer', FeatureEngineer()),
    ('classifier', RandomForestClassifier())
])

# Train pipeline
pipeline.fit(X_train, y_train)

# Predict
y_pred = pipeline.predict(X_test)
```

#### Save and Load

```python
# Fit and save
engineer = FeatureEngineer()
engineer.fit(X_train)
engineer.save('models/feature_engineer.pkl')

# Load later
loaded_engineer = FeatureEngineer.load('models/feature_engineer.pkl')
X_new_transformed = loaded_engineer.transform(X_new)
```

### Input Data Requirements

The FeatureEngineer expects a pandas DataFrame with the following columns (minimum):

**Required Numerical Features**:
- `property_age` - Building age in years
- `violation_history_count` - Total violations
- `days_since_last_violation` - Days since last violation
- `neighborhood_risk_score` - Risk score (0-1)
- `total_units` - Number of units
- `complaint_frequency` - Complaints per month
- `owner_compliance_score` - Compliance score (0-1)

**Optional Temporal Features**:
- `inspection_date` - Date of last inspection (for temporal features)

**Optional Categorical Features**:
- `building_class` - Building classification
- `neighborhood` - Neighborhood name

**Optional Additional Features**:
- `seasonal_factor`, `economic_zone_risk`, `flood_zone_risk`, `construction_activity_nearby`

### Output

The transformer returns a pandas DataFrame with:
- All original numerical features (scaled)
- Temporal features (if enabled): +8 features
- Interaction features (if enabled): +6 features
- Aggregation features (if enabled): +4-8 features per group column
- Polynomial features (if enabled): +N features (depends on degree)
- Encoded categorical features: +N features (depends on unique values)

**Typical output**: 50-200 features depending on configuration and input data.

### Performance Considerations

**Training Time**:
- 100 properties: < 1 second
- 1,000 properties: ~2 seconds
- 10,000 properties: ~10 seconds
- 100,000 properties: ~60 seconds

**Transform Time**:
- ~50% of training time
- Scales linearly with data size

**Memory Usage**:
- Approximately 2-3x input DataFrame size
- Polynomial features increase memory usage significantly

### Best Practices

1. **Always fit on training data only**
   ```python
   # Good
   engineer.fit(X_train)
   X_test_transformed = engineer.transform(X_test)
   
   # Bad - data leakage!
   engineer.fit(pd.concat([X_train, X_test]))
   ```

2. **Handle categorical variables carefully**
   ```python
   # Ensure test data doesn't have unseen categories
   # Or use handle_unknown='ignore' in encoder
   ```

3. **Monitor feature count**
   ```python
   # Check engineered feature count
   print(f"Features: {len(engineer.get_feature_names())}")
   
   # Too many features (>500)? Consider:
   # - Reducing polynomial degree
   # - Disabling some feature types
   # - Feature selection post-engineering
   ```

4. **Save fitted transformers for production**
   ```python
   # After training
   engineer.save('models/production_engineer_v1.pkl')
   
   # In production
   engineer = FeatureEngineer.load('models/production_engineer_v1.pkl')
   ```

5. **Use appropriate scaler**
   ```python
   # Data with outliers? Use RobustScaler (default)
   config = FeatureConfig(scaler_type='robust')
   
   # Clean data? StandardScaler is faster
   config = FeatureConfig(scaler_type='standard')
   ```

### Integration with AI Risk Predictor

The FeatureEngineer is designed to work seamlessly with the RiskPredictor:

```python
from ai.feature_engineering import FeatureEngineer
from ai.risk_predictor import RiskPredictor

# Step 1: Engineer features
engineer = FeatureEngineer()
X_train_engineered = engineer.fit_transform(X_train_raw)
X_test_engineered = engineer.transform(X_test_raw)

# Step 2: Train predictor
predictor = RiskPredictor()
predictor.train(X_train_engineered, y_critical, y_days)

# Step 3: Predict
results = predictor.predict_batch(X_test_engineered, property_ids)
```

### Troubleshooting

**Issue: "FeatureEngineer must be fitted before transform"**
- Solution: Call `fit()` or `fit_transform()` before `transform()`

**Issue: "Different number of features in transform"**
- Solution: Ensure test data has same base columns as training data

**Issue: "Memory error with large datasets"**
- Solution: Reduce polynomial degree or disable polynomial features

**Issue: "Slow performance"**
- Solution: Disable aggregations or reduce aggregation groups

**Issue: "NaN values in output"**
- Solution: Enable `handle_missing=True` in config

### API Reference

#### FeatureConfig

```python
@dataclass
class FeatureConfig:
    use_temporal: bool = True
    use_interactions: bool = True
    use_aggregations: bool = True
    use_polynomial: bool = True
    polynomial_degree: int = 2
    scaler_type: str = 'robust'
    handle_missing: bool = True
```

#### FeatureEngineer

**Methods**:

- `__init__(config: Optional[FeatureConfig] = None)` - Initialize
- `fit(X: pd.DataFrame, y=None) -> FeatureEngineer` - Fit to training data
- `transform(X: pd.DataFrame) -> pd.DataFrame` - Transform new data
- `fit_transform(X: pd.DataFrame, y=None) -> pd.DataFrame` - Fit and transform
- `save(filepath: str) -> None` - Save fitted transformer
- `load(filepath: str) -> FeatureEngineer` - Load fitted transformer (static)
- `get_feature_names() -> List[str]` - Get feature names after fitting
- `create_temporal_features(df, date_column) -> pd.DataFrame` - Create temporal features
- `create_interaction_features(df) -> pd.DataFrame` - Create interaction features
- `create_aggregation_features(df, group_columns) -> pd.DataFrame` - Create aggregation features
- `handle_missing_values(df, is_training) -> pd.DataFrame` - Handle missing values
- `create_polynomial_features(df, feature_columns) -> pd.DataFrame` - Create polynomial features
- `encode_categorical(df, categorical_columns) -> pd.DataFrame` - Encode categorical variables
- `scale_features(df, exclude_columns) -> pd.DataFrame` - Scale numerical features

### Testing

Run the test suite:

```bash
python test_feature_engineering.py
```

Expected output:
```
Running FeatureEngineer Tests
============================================================
test_aggregation_features ... ok
test_all_features_enabled ... ok
test_categorical_encoding ... ok
...
============================================================
✅ All tests passed!
```

### Version History

**v1.0.0** (2026-01-15)
- Initial release
- Temporal, interaction, aggregation features
- Polynomial features with configurable degree
- Missing value handling
- Categorical encoding
- Feature scaling (Standard and Robust)
- sklearn Pipeline compatibility
- Save/load functionality

### License

ViolationSentinel Enterprise PropTech Platform
Copyright (c) 2026
