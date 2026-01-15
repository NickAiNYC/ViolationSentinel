"""
Configuration Management
Environment-based configuration with secure defaults
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn


class Settings(BaseSettings):
    """Application Settings"""
    
    # Application
    APP_NAME: str = "ViolationSentinel"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/violation_sentinel"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    # Security
    BCRYPT_ROUNDS: int = 12
    API_KEY_LENGTH: int = 32
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # NYC Open Data
    NYC_APP_TOKEN: Optional[str] = os.getenv("NYC_APP_TOKEN")
    NYC_API_BATCH_SIZE: int = 1000
    NYC_API_RATE_LIMIT: int = 5  # requests per second
    
    # Data Ingestion
    INGESTION_SCHEDULE_CRON: str = "0 2 * * *"  # 2 AM daily
    DATA_RETENTION_DAYS: int = 2555  # 7 years
    
    # ML Models
    MODEL_STORAGE_PATH: str = "models/"
    MODEL_VERSION_PREFIX: str = "v"
    MODEL_DRIFT_THRESHOLD: float = 0.15
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Alerts
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "alerts@violationsentinel.com")
    
    # Webhooks
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_RETRY_COUNT: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
