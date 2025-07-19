"""
Configuration management for CloudArb platform.
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field, validator


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="cloudarb", env="DB_NAME")
    user: str = Field(default="cloudarb", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")

    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")

    @property
    def url(self) -> str:
        """Get Redis URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")

    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v


class CloudProviderSettings(BaseSettings):
    """Cloud provider API configuration."""

    # AWS Configuration
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")

    # GCP Configuration
    gcp_project_id: Optional[str] = Field(default=None, env="GCP_PROJECT_ID")
    gcp_credentials_file: Optional[str] = Field(default=None, env="GCP_CREDENTIALS_FILE")

    # Azure Configuration
    azure_subscription_id: Optional[str] = Field(default=None, env="AZURE_SUBSCRIPTION_ID")
    azure_tenant_id: Optional[str] = Field(default=None, env="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, env="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, env="AZURE_CLIENT_SECRET")

    # Lambda Labs Configuration
    lambda_api_key: Optional[str] = Field(default=None, env="LAMBDA_API_KEY")

    # RunPod Configuration
    runpod_api_key: Optional[str] = Field(default=None, env="RUNPOD_API_KEY")


class OptimizationSettings(BaseSettings):
    """Optimization engine configuration."""

    solver_timeout_seconds: int = Field(default=30, env="SOLVER_TIMEOUT_SECONDS")
    max_iterations: int = Field(default=10000, env="MAX_ITERATIONS")
    tolerance: float = Field(default=1e-6, env="SOLVER_TOLERANCE")
    enable_spot_instances: bool = Field(default=True, env="ENABLE_SPOT_INSTANCES")
    risk_tolerance: float = Field(default=0.1, env="RISK_TOLERANCE")
    max_providers_per_optimization: int = Field(default=5, env="MAX_PROVIDERS_PER_OPTIMIZATION")


class MLSettings(BaseSettings):
    """Machine learning configuration."""

    model_storage_path: str = Field(default="/app/models", env="MODEL_STORAGE_PATH")
    forecast_horizon_hours: int = Field(default=4, env="FORECAST_HORIZON_HOURS")
    retrain_interval_hours: int = Field(default=24, env="RETRAIN_INTERVAL_HOURS")
    confidence_level: float = Field(default=0.95, env="CONFIDENCE_LEVEL")
    min_training_samples: int = Field(default=1000, env="MIN_TRAINING_SAMPLES")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""

    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")


class Settings(BaseSettings):
    """Main application settings."""

    # Application
    app_name: str = Field(default="CloudArb", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")

    # Rate limiting
    rate_limit_requests: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")

    # Database
    database: DatabaseSettings = DatabaseSettings()

    # Redis
    redis: RedisSettings = RedisSettings()

    # Security
    security: SecuritySettings = SecuritySettings()

    # Cloud providers
    cloud_providers: CloudProviderSettings = CloudProviderSettings()

    # Optimization
    optimization: OptimizationSettings = OptimizationSettings()

    # Machine learning
    ml: MLSettings = MLSettings()

    # Monitoring
    monitoring: MonitoringSettings = MonitoringSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings