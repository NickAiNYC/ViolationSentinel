"""
Core configuration management
Supports multiple environments with secure secret management
"""

from typing import List, Optional, Union
from pydantic import AnyHttpUrl, Field, validator
from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Base
    PROJECT_NAME: str = "ViolationSentinel"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://app.violationsentinel.com"
    ]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/violationsentinel",
        env="DATABASE_URL"
    )
    TIMESCALEDB_ENABLED: bool = True
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    # Redis Cache
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CACHE_TTL: int = 3600  # 1 hour
    
    # ElasticSearch
    ELASTICSEARCH_URL: str = Field(
        default="http://localhost:9200",
        env="ELASTICSEARCH_URL"
    )
    ES_INDEX_PREFIX: str = "violationsentinel"
    
    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    # Rate Limiting
    RATE_LIMIT: int = 100  # requests per minute
    
    # Multi-tenant
    TENANT_HEADER: str = "X-Tenant-ID"
    
    # External APIs
    NYC_OPEN_DATA_TOKEN: Optional[str] = Field(default=None, env="NYC_OPEN_DATA_TOKEN")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_ENABLED: bool = True
    
    # Webhooks
    SLACK_WEBHOOK_URL: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    TEAMS_WEBHOOK_URL: Optional[str] = Field(default=None, env="TEAMS_WEBHOOK_URL")
    
    # Payment Processing
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    
    # OCR
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    
    # ML Models
    ML_MODEL_PATH: str = "./models"
    BERT_MODEL: str = "bert-base-uncased"
    
    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
