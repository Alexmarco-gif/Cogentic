"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Cogent API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    
    # Database (Neon PostgreSQL)
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    
    # Auth0
    auth0_domain: str
    auth0_audience: str
    auth0_m2m_client_id: str
    auth0_m2m_client_secret: str
    auth0_webhook_secret: str | None = None  # Optional: for webhook signature verification
    
    # Security
    secret_key: str
    
    # Observability (optional)
    sentry_dsn: str | None = None
    logtail_token: str | None = None
    posthog_api_key: str | None = None
    posthog_host: str = "https://app.posthog.com"
    
    # CORS origins
    cors_origins: str = "http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton"""
    return Settings()
