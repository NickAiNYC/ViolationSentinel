"""
ViolationSentinel Model Monitoring System

Production-grade monitoring for AI risk prediction models.
Tracks predictions, detects drift, monitors performance, and triggers retraining alerts.

Author: ViolationSentinel Team
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from scipy import stats
import asyncpg
import redis.asyncio as aioredis
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """Record of a single prediction."""
    property_id: str
    model_version: str
    timestamp: datetime
    risk_score: float
    risk_level: str
    critical_probability: float
    days_until_violation: float
    confidence: float
    features: Dict[str, float]
    feature_importance: Dict[str, float]


@dataclass
class OutcomeRecord:
    """Record of actual outcome."""
    property_id: str
    timestamp: datetime
    actual_critical: bool
    actual_days: Optional[float]
    matched_prediction_id: Optional[int]


@dataclass
class DriftResult:
    """Result of drift detection analysis."""
    drift_detected: bool
    drift_type: str  # 'feature', 'prediction', 'importance'
    ks_statistic: float
    p_value: float
    message: str
    severity: str  # 'low', 'medium', 'high'
    recommendation: str


class ModelMonitor:
    """
    Production model monitoring system.
    
    Tracks predictions, monitors performance, detects drift,
    and triggers alerts when model degradation is detected.
    """
    
    def __init__(
        self,
        db_url: str,
        redis_url: str = "redis://localhost:6379",
        accuracy_threshold: float = 0.85,
        drift_threshold: float = 0.05,
        alert_email: Optional[str] = None,
        sendgrid_api_key: Optional[str] = None
    ):
        """
        Initialize model monitor.
        
        Args:
            db_url: PostgreSQL connection string
            redis_url: Redis connection string
            accuracy_threshold: Alert if accuracy drops below this
            drift_threshold: Alert if p-value < this
            alert_email: Email for alerts
            sendgrid_api_key: SendGrid API key for emails
        """
        self.db_url = db_url
        self.redis_url = redis_url
        self.accuracy_threshold = accuracy_threshold
        self.drift_threshold = drift_threshold
        self.alert_email = alert_email
        self.sendgrid_api_key = sendgrid_api_key
        
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[aioredis.Redis] = None
        
        # Prometheus metrics
        self.predictions_counter = Counter(
            'violation_predictions_total',
            'Total predictions made',
            ['model_version', 'risk_level']
        )
        self.accuracy_gauge = Gauge(
            'violation_model_accuracy',
            'Current model accuracy',
            ['window']
        )
        self.drift_score_gauge = Gauge(
            'violation_model_drift_score',
            'Current drift score (KS statistic)'
        )
        self.prediction_latency = Histogram(
            'violation_prediction_latency_seconds',
            'Prediction processing time'
        )
        
        logger.info("ModelMonitor initialized")
    
    async def setup_database(self):
        """Create database tables if they don't exist."""
        self.db_pool = await asyncpg.create_pool(self.db_url)
        self.redis = await aioredis.from_url(self.redis_url)
        
        async with self.db_pool.acquire() as conn:
            # Predictions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_predictions (
                    id SERIAL PRIMARY KEY,
                    property_id VARCHAR(100) NOT NULL,
                    model_version VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    risk_score FLOAT NOT NULL,
                    risk_level VARCHAR(20) NOT NULL,
                    critical_probability FLOAT NOT NULL,
                    days_until_violation FLOAT,
                    confidence FLOAT NOT NULL,
                    features JSONB NOT NULL,
                    feature_importance JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_predictions_property 
                ON model_predictions(property_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_predictions_timestamp 
                ON model_predictions(timestamp DESC);
            """)
            
            # Outcomes table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_outcomes (
                    id SERIAL PRIMARY KEY,
                    property_id VARCHAR(100) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    actual_critical BOOLEAN NOT NULL,
                    actual_days FLOAT,
                    matched_prediction_id INTEGER REFERENCES model_predictions(id),
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_outcomes_property 
                ON model_outcomes(property_id, timestamp DESC);
            """)
            
            # Metrics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id SERIAL PRIMARY KEY,
                    window_type VARCHAR(20) NOT NULL,
                    calculated_at TIMESTAMP NOT NULL,
                    accuracy FLOAT,
                    precision_score FLOAT,
                    recall FLOAT,
                    f1_score FLOAT,
                    roc_auc FLOAT,
                    mae FLOAT,
                    rmse FLOAT,
                    r2_score FLOAT,
                    sample_size INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_metrics_calculated 
                ON model_metrics(calculated_at DESC);
            """)
            
            # Drift events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS drift_events (
                    id SERIAL PRIMARY KEY,
                    detected_at TIMESTAMP NOT NULL,
                    drift_type VARCHAR(50) NOT NULL,
                    ks_statistic FLOAT NOT NULL,
                    p_value FLOAT NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    recommendation TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_drift_detected 
                ON drift_events(detected_at DESC);
            """)
        
        logger.info("Database tables created successfully")
    
    async def add_prediction(
        self,
        property_id: str,
        prediction_result: Any,  # PredictionResult from risk_predictor
        features: Dict[str, float]
    ) -> int:
        """
        Add a prediction to tracking.
        
        Args:
            property_id: Unique property identifier
            prediction_result: Result from RiskPredictor.predict()
            features: Input features used for prediction
        
        Returns:
            prediction_id: Database ID of stored prediction
        """
        start_time = datetime.now()
        
        try:
            async with self.db_pool.acquire() as conn:
                prediction_id = await conn.fetchval("""
                    INSERT INTO model_predictions (
                        property_id, model_version, timestamp,
                        risk_score, risk_level, critical_probability,
                        days_until_violation, confidence,
                        features, feature_importance
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                """,
                    property_id,
                    prediction_result.model_version,
                    datetime.now(),
                    prediction_result.risk_score,
                    prediction_result.risk_level,
                    prediction_result.critical_violation_probability,
                    prediction_result.days_until_next_violation,
                    prediction_result.confidence,
                    json.dumps(features),
                    json.dumps(prediction_result.feature_importance)
                )
            
            # Cache in Redis (1 hour TTL)
            cache_key = f"prediction:{property_id}:{prediction_id}"
            await self.redis.setex(
                cache_key,
                3600,
                json.dumps({
                    'id': prediction_id,
                    'risk_score': prediction_result.risk_score,
                    'risk_level': prediction_result.risk_level,
                    'timestamp': datetime.now().isoformat()
                })
            )
            
            # Update Prometheus metrics
            self.predictions_counter.labels(
                model_version=prediction_result.model_version,
                risk_level=prediction_result.risk_level
            ).inc()
            
            latency = (datetime.now() - start_time).total_seconds()
            self.prediction_latency.observe(latency)
            
            logger.debug(f"Prediction {prediction_id} added for property {property_id}")
            return prediction_id
            
        except Exception as e:
            logger.error(f"Error adding prediction: {e}")
            raise
    
    async def add_outcome(
        self,
        property_id: str,
        actual_critical: bool,
        actual_days: Optional[float] = None,
        outcome_timestamp: Optional[datetime] = None
    ) -> int:
        """
        Add actual outcome and match to prediction.
        
        Args:
            property_id: Property identifier
            actual_critical: Whether critical violation occurred
            actual_days: Actual days until violation (if occurred)
            outcome_timestamp: When outcome was observed (default: now)
        
        Returns:
            outcome_id: Database ID of stored outcome
        """
        if outcome_timestamp is None:
            outcome_timestamp = datetime.now()
        
        try:
            async with self.db_pool.acquire() as conn:
                # Find matching prediction (within 90 days before outcome)
                prediction_id = await conn.fetchval("""
                    SELECT id FROM model_predictions
                    WHERE property_id = $1
                    AND timestamp <= $2
                    AND timestamp >= $2 - INTERVAL '90 days'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, property_id, outcome_timestamp)
                
                # Insert outcome
                outcome_id = await conn.fetchval("""
                    INSERT INTO model_outcomes (
                        property_id, timestamp, actual_critical,
                        actual_days, matched_prediction_id
                    ) VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """,
                    property_id,
                    outcome_timestamp,
                    actual_critical,
                    actual_days,
                    prediction_id
                )
            
            logger.debug(f"Outcome {outcome_id} added for property {property_id}")
            
            # Trigger metrics recalculation
            await self.calculate_metrics(window='7d')
            
            return outcome_id
            
        except Exception as e:
            logger.error(f"Error adding outcome: {e}")
            raise
    
    async def get_performance_metrics(
        self,
        window: str = '30d'
    ) -> Dict[str, Any]:
        """
        Calculate current performance metrics.
        
        Args:
            window: Time window ('7d', '30d', 'all')
        
        Returns:
            Dict with classification and regression metrics
        """
        # Check cache first
        cache_key = f"metrics:{window}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        try:
            async with self.db_pool.acquire() as conn:
                # Determine time cutoff
                if window == 'all':
                    cutoff = datetime(2000, 1, 1)
                else:
                    days = int(window.rstrip('d'))
                    cutoff = datetime.now() - timedelta(days=days)
                
                # Fetch predictions with outcomes
                rows = await conn.fetch("""
                    SELECT 
                        p.risk_score,
                        p.critical_probability,
                        p.days_until_violation,
                        o.actual_critical,
                        o.actual_days
                    FROM model_predictions p
                    INNER JOIN model_outcomes o 
                    ON p.id = o.matched_prediction_id
                    WHERE p.timestamp >= $1
                """, cutoff)
                
                if not rows:
                    logger.warning(f"No data for window {window}")
                    return {'classification': {}, 'regression': {}, 'sample_size': 0}
                
                # Extract data
                predicted_critical = [r['critical_probability'] > 0.5 for r in rows]
                actual_critical = [r['actual_critical'] for r in rows]
                predicted_days = [r['days_until_violation'] for r in rows if r['days_until_violation']]
                actual_days = [r['actual_days'] for r in rows if r['actual_days']]
                
                # Classification metrics
                tp = sum(p and a for p, a in zip(predicted_critical, actual_critical))
                tn = sum(not p and not a for p, a in zip(predicted_critical, actual_critical))
                fp = sum(p and not a for p, a in zip(predicted_critical, actual_critical))
                fn = sum(not p and a for p, a in zip(predicted_critical, actual_critical))
                
                accuracy = (tp + tn) / len(rows) if rows else 0
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                # Regression metrics
                if predicted_days and actual_days:
                    mae = np.mean(np.abs(np.array(predicted_days) - np.array(actual_days)))
                    rmse = np.sqrt(np.mean((np.array(predicted_days) - np.array(actual_days)) ** 2))
                    
                    ss_res = np.sum((np.array(actual_days) - np.array(predicted_days)) ** 2)
                    ss_tot = np.sum((np.array(actual_days) - np.mean(actual_days)) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                else:
                    mae, rmse, r2 = None, None, None
                
                metrics = {
                    'classification': {
                        'accuracy': accuracy,
                        'precision': precision,
                        'recall': recall,
                        'f1_score': f1,
                        'true_positives': tp,
                        'true_negatives': tn,
                        'false_positives': fp,
                        'false_negatives': fn
                    },
                    'regression': {
                        'mae': mae,
                        'rmse': rmse,
                        'r2_score': r2
                    },
                    'sample_size': len(rows),
                    'window': window,
                    'calculated_at': datetime.now().isoformat()
                }
                
                # Cache for 5 minutes
                await self.redis.setex(cache_key, 300, json.dumps(metrics))
                
                # Update Prometheus
                self.accuracy_gauge.labels(window=window).set(accuracy)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            raise
    
    async def calculate_metrics(self, window: str = '7d'):
        """Calculate and store metrics in database."""
        metrics = await self.get_performance_metrics(window)
        
        if metrics['sample_size'] > 0:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO model_metrics (
                        window_type, calculated_at, accuracy, precision_score,
                        recall, f1_score, mae, rmse, r2_score, sample_size
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    window,
                    datetime.now(),
                    metrics['classification']['accuracy'],
                    metrics['classification']['precision'],
                    metrics['classification']['recall'],
                    metrics['classification']['f1_score'],
                    metrics['regression'].get('mae'),
                    metrics['regression'].get('rmse'),
                    metrics['regression'].get('r2_score'),
                    metrics['sample_size']
                )
    
    async def detect_drift(
        self,
        baseline_days: int = 90,
        recent_days: int = 7
    ) -> DriftResult:
        """
        Detect model drift using Kolmogorov-Smirnov test.
        
        Args:
            baseline_days: Days for baseline distribution
            recent_days: Days for recent distribution
        
        Returns:
            DriftResult with detection details
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get baseline predictions
                baseline_cutoff = datetime.now() - timedelta(days=baseline_days)
                recent_cutoff = datetime.now() - timedelta(days=recent_days)
                
                baseline_scores = await conn.fetch("""
                    SELECT risk_score FROM model_predictions
                    WHERE timestamp >= $1 AND timestamp < $2
                """, baseline_cutoff, recent_cutoff)
                
                recent_scores = await conn.fetch("""
                    SELECT risk_score FROM model_predictions
                    WHERE timestamp >= $1
                """, recent_cutoff)
                
                if len(baseline_scores) < 30 or len(recent_scores) < 30:
                    logger.warning("Insufficient data for drift detection")
                    return DriftResult(
                        drift_detected=False,
                        drift_type='prediction',
                        ks_statistic=0.0,
                        p_value=1.0,
                        message="Insufficient data for drift detection",
                        severity='low',
                        recommendation="Continue monitoring"
                    )
                
                # Perform KS test
                baseline_data = [r['risk_score'] for r in baseline_scores]
                recent_data = [r['risk_score'] for r in recent_scores]
                
                ks_stat, p_value = stats.ks_2samp(baseline_data, recent_data)
                
                drift_detected = p_value < self.drift_threshold
                
                # Determine severity
                if p_value < 0.01:
                    severity = 'high'
                elif p_value < 0.05:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                # Create result
                if drift_detected:
                    message = f"Significant drift detected (p={p_value:.4f})"
                    recommendation = "Model retraining recommended within 7 days"
                    
                    # Log drift event
                    await conn.execute("""
                        INSERT INTO drift_events (
                            detected_at, drift_type, ks_statistic,
                            p_value, severity, message, recommendation
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        datetime.now(), 'prediction', ks_stat,
                        p_value, severity, message, recommendation
                    )
                    
                    # Send alert
                    await self._send_drift_alert(message, severity, recommendation)
                else:
                    message = f"No significant drift (p={p_value:.4f})"
                    recommendation = "Continue normal monitoring"
                
                # Update Prometheus
                self.drift_score_gauge.set(ks_stat)
                
                return DriftResult(
                    drift_detected=drift_detected,
                    drift_type='prediction',
                    ks_statistic=ks_stat,
                    p_value=p_value,
                    message=message,
                    severity=severity,
                    recommendation=recommendation
                )
                
        except Exception as e:
            logger.error(f"Error detecting drift: {e}")
            raise
    
    async def generate_weekly_report(self) -> str:
        """
        Generate and send weekly performance report.
        
        Returns:
            Report text
        """
        try:
            # Get metrics for different windows
            metrics_7d = await self.get_performance_metrics('7d')
            metrics_30d = await self.get_performance_metrics('30d')
            
            # Detect drift
            drift_result = await self.detect_drift()
            
            # Build report
            report = f"""
ViolationSentinel Model Performance Report
==========================================

Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

7-DAY METRICS
-------------
Sample Size: {metrics_7d['sample_size']}
Accuracy: {metrics_7d['classification']['accuracy']:.1%}
Precision: {metrics_7d['classification']['precision']:.3f}
Recall: {metrics_7d['classification']['recall']:.3f}
F1 Score: {metrics_7d['classification']['f1_score']:.3f}

MAE (days): {metrics_7d['regression'].get('mae', 'N/A')}
RMSE (days): {metrics_7d['regression'].get('rmse', 'N/A')}
R² Score: {metrics_7d['regression'].get('r2_score', 'N/A')}

30-DAY METRICS
--------------
Sample Size: {metrics_30d['sample_size']}
Accuracy: {metrics_30d['classification']['accuracy']:.1%}
Precision: {metrics_30d['classification']['precision']:.3f}
Recall: {metrics_30d['classification']['recall']:.3f}

DRIFT ANALYSIS
--------------
Drift Detected: {drift_result.drift_detected}
Severity: {drift_result.severity.upper()}
KS Statistic: {drift_result.ks_statistic:.4f}
P-Value: {drift_result.p_value:.4f}
Message: {drift_result.message}

RECOMMENDATIONS
---------------
{drift_result.recommendation}

{'⚠️ ACTION REQUIRED: ' + self._check_retraining_needed(metrics_7d, drift_result) if self._check_retraining_needed(metrics_7d, drift_result) else '✅ Model performing within acceptable parameters'}

---
Automated report from ViolationSentinel Model Monitoring
            """
            
            # Send via email if configured
            if self.alert_email and self.sendgrid_api_key:
                await self._send_email(
                    subject="📊 ViolationSentinel Weekly Model Report",
                    body=report
                )
            
            logger.info("Weekly report generated")
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
    
    def _check_retraining_needed(
        self,
        metrics: Dict[str, Any],
        drift: DriftResult
    ) -> str:
        """Check if retraining is needed."""
        issues = []
        
        if metrics['classification']['accuracy'] < self.accuracy_threshold:
            issues.append(f"Accuracy below threshold ({metrics['classification']['accuracy']:.1%} < {self.accuracy_threshold:.1%})")
        
        if drift.drift_detected and drift.severity in ['medium', 'high']:
            issues.append(f"{drift.severity.capitalize()} drift detected")
        
        if issues:
            return "Model retraining recommended. Issues: " + "; ".join(issues)
        return ""
    
    async def _send_drift_alert(
        self,
        message: str,
        severity: str,
        recommendation: str
    ):
        """Send alert email for drift detection."""
        if not self.alert_email or not self.sendgrid_api_key:
            logger.warning("Alert email not configured")
            return
        
        alert_text = f"""
🚨 ViolationSentinel Model Drift Alert

SEVERITY: {severity.upper()}
DETECTED AT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

MESSAGE: {message}

RECOMMENDATION: {recommendation}

ACTION REQUIRED:
- Review recent model performance
- Check for data quality issues
- Consider model retraining
- Investigate feature distribution changes

---
Automated alert from ViolationSentinel Model Monitoring
        """
        
        await self._send_email(
            subject=f"🚨 Model Drift Alert - {severity.upper()} Severity",
            body=alert_text
        )
    
    async def _send_email(self, subject: str, body: str):
        """Send email via SendGrid."""
        try:
            # Placeholder for SendGrid integration
            # In production, use sendgrid library
            logger.info(f"Email sent: {subject}")
            logger.debug(f"Email body:\n{body}")
            
            # TODO: Implement actual SendGrid API call
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            # message = Mail(
            #     from_email='alerts@violationsentinel.com',
            #     to_emails=self.alert_email,
            #     subject=subject,
            #     plain_text_content=body
            # )
            # sg = SendGridAPIClient(self.sendgrid_api_key)
            # response = sg.send(message)
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    async def start_monitoring(self, port: int = 9090):
        """
        Start monitoring service.
        
        Args:
            port: Port for Prometheus metrics server
        """
        logger.info(f"Starting model monitoring on port {port}")
        start_http_server(port)
        
        while True:
            try:
                # Calculate metrics every hour
                await self.calculate_metrics('7d')
                await self.calculate_metrics('30d')
                
                # Check for drift daily
                drift_result = await self.detect_drift()
                if drift_result.drift_detected:
                    logger.warning(f"Drift detected: {drift_result.message}")
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def close(self):
        """Clean up resources."""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis:
            await self.redis.close()
        logger.info("ModelMonitor closed")


# Example usage
async def main():
    """Example usage of ModelMonitor."""
    import os
    
    monitor = ModelMonitor(
        db_url=os.getenv('MONITOR_DB_URL', 'postgresql://localhost/violations'),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
        accuracy_threshold=0.85,
        alert_email=os.getenv('ALERT_EMAIL'),
        sendgrid_api_key=os.getenv('SENDGRID_API_KEY')
    )
    
    # Setup database
    await monitor.setup_database()
    
    # Example: Add prediction
    from dataclasses import dataclass
    
    @dataclass
    class MockPrediction:
        risk_score: float = 75.0
        risk_level: str = "HIGH"
        critical_violation_probability: float = 0.68
        days_until_next_violation: float = 45.0
        confidence: float = 0.87
        feature_importance: dict = None
        model_version: str = "1.0.0"
        
        def __post_init__(self):
            if self.feature_importance is None:
                self.feature_importance = {
                    'violation_history': 0.3,
                    'property_age': 0.2,
                    'neighborhood_risk': 0.15
                }
    
    pred = MockPrediction()
    features = {
        'property_age': 50,
        'violation_history_count': 8,
        'neighborhood_risk_score': 0.7
    }
    
    pred_id = await monitor.add_prediction('PROP-001', pred, features)
    print(f"Prediction added: {pred_id}")
    
    # Get metrics
    metrics = await monitor.get_performance_metrics('7d')
    print(f"Metrics: {metrics}")
    
    # Check drift
    drift = await monitor.detect_drift()
    print(f"Drift: {drift.message}")
    
    # Generate report
    report = await monitor.generate_weekly_report()
    print(report)
    
    await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
