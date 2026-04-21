"""Application configuration using Pydantic Settings"""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Cogent"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    environment: str = "development"
    debug: bool = False

    # Database (Azure PostgreSQL Flexible Server)
    database_url: str
    database_read_url: str | None = None  # Read replica URL (falls back to primary)
    # Pool defaults tuned for 4 Gunicorn workers with async concurrency.
    # Override via DATABASE_POOL_SIZE / DATABASE_MAX_OVERFLOW env vars.
    database_pool_size: int = 20
    database_max_overflow: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10

    # Auth0
    auth0_domain: str
    auth0_audience: str
    auth0_m2m_client_id: str
    auth0_m2m_client_secret: str
    auth0_webhook_secret: str | None = (
        None  # Optional: for webhook signature verification
    )

    # Security
    secret_key: str

    # Request limits
    max_request_body_bytes: int = 10_485_760  # 10 MB default
    metrics_allowed_ips: str = (
        ""  # Comma-separated IPs allowed to access /metrics (empty = unrestricted)
    )

    @property
    def metrics_allowed_ips_list(self) -> list[str]:
        """Parse metrics IP allowlist from comma-separated string."""
        if not self.metrics_allowed_ips:
            return []
        return [ip.strip() for ip in self.metrics_allowed_ips.split(",") if ip.strip()]

    # Observability (optional)
    sentry_dsn: str | None = None
    logtail_token: str | None = None
    posthog_api_key: str | None = None
    posthog_host: str = "https://app.posthog.com"

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    openai_embedding_batch_size: int = 100
    openai_embedding_rpm_limit: int = 3000  # requests per minute
    openai_max_concurrent_requests: int = 100  # Concurrent requests to OpenAI API

    # ML / ONNX
    ml_models_dir: str = "backend/ml/models"
    ml_model_max_versions: int = 3
    ml_semantic_dedup_threshold: float = 0.95
    ml_entity_similarity_threshold: float = 0.75
    ml_entity_min_confidence: float = 0.70  # Min confidence to link entity to signal
    ml_models_required: list[str] = [
        "anomaly_detector",
        "trending_scorer",
        "confidence_calibrator",
    ]
    # Set ML_VALIDATE_ON_STARTUP=true in production to fail fast if ONNX models
    # are missing from ml_models_dir / Azure Blob before the first request hits them.
    ml_validate_on_startup: bool = False
    ml_inference_timeout_ms: int = 100  # Max inference time per model
    ml_embedding_cache_enabled: bool = True  # Cache OpenAI embeddings in Redis
    ml_embedding_cache_ttl_days: int = 7  # Time-to-live for cached embeddings

    # Azure Blob (prod model storage)
    azure_blob_connection_string: str | None = None
    azure_blob_model_container: str = "ml-models"

    # Email (Resend)
    resend_api_key: str | None = None  # Set via RESEND_API_KEY env var
    resend_from_email: str = "Cogent <notifications@cogent.ai>"  # Verified sender

    # Payments (Paystack)
    paystack_public_key: str | None = None
    paystack_secret_key: str | None = None
    paystack_base_url: str = "https://api.paystack.co"

    # Web Search (SerpApi)
    web_search_provider: str = "serpapi"  # "serpapi" or "none"
    serpapi_api_key: str = ""  # Set via SERPAPI_API_KEY env var
    serpapi_timeout_seconds: float = 15.0  # HTTP timeout for SerpApi requests
    serpapi_max_concurrent_requests: int = 5  # Max parallel SerpApi calls
    web_search_max_results: int = 10  # Default max results per search
    web_search_cache_ttl: int = 900  # Cache TTL in seconds (15 min)
    web_search_default_country: str = ""  # Default country code (e.g. "ng")
    web_search_default_language: str = "en"  # Default language code

    # Signal source providers
    newsapi_api_key: str = ""
    ngx_market_data_api_key: str = ""
    ngx_market_data_base_url: str = ""
    x_bearer_token: str = ""

    # Neo4j (causal knowledge graph)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # Set via NEO4J_PASSWORD env var in production

    # Startup behaviour
    # Defaults to False so local dev works without every service running.
    # Production / staging set these to True explicitly via env vars.
    require_healthy_db_on_startup: bool = False
    require_healthy_redis_on_startup: bool = False
    bootstrap_catalog_on_startup: bool = True

    # CORS origins
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        if isinstance(self.cors_origins, str):
            return [
                origin.strip()
                for origin in self.cors_origins.split(",")
                if origin.strip()
            ]
        return list(self.cors_origins)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        """Coerce common deployment/debug markers into a boolean."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "staging"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    def model_post_init(self, __context: object) -> None:
        if (
            "environment" not in self.__pydantic_fields_set__
            and "app_env" in self.__pydantic_fields_set__
        ):
            self.environment = self.app_env

        is_prod = self.environment in ("production", "staging")

        if is_prod and self.debug:
            raise ValueError(
                "DEBUG must not be True in production/staging. "
                "Set DEBUG=false in your environment."
            )

        if is_prod and not self.neo4j_password and "localhost" not in self.neo4j_uri:
            raise ValueError(
                "NEO4J_PASSWORD must be set when NEO4J_URI points to a remote host "
                f"(current: {self.neo4j_uri}). Set NEO4J_PASSWORD in your environment."
            )

        if is_prod and not self.sentry_dsn:
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "SENTRY_DSN is not set in %s environment — errors will not be tracked remotely.",
                self.environment,
            )

        if is_prod and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set in production. "
                "All AI/embedding features will fail without it."
            )

        if is_prod and not self.newsapi_api_key:
            raise ValueError(
                "NEWSAPI_API_KEY must be set in production/staging. "
                "NewsAPI-backed signal contracts depend on it."
            )

        if is_prod and not self.ngx_market_data_api_key:
            raise ValueError(
                "NGX_MARKET_DATA_API_KEY must be set in production/staging. "
                "NGX market data contracts depend on it."
            )

        if is_prod and not self.ngx_market_data_base_url:
            raise ValueError(
                "NGX_MARKET_DATA_BASE_URL must be set in production/staging. "
                "Use the official NGX market data endpoint for your subscription."
            )

        if is_prod and not self.x_bearer_token:
            raise ValueError(
                "X_BEARER_TOKEN must be set in production/staging. "
                "X-backed social contracts depend on it."
            )

        if is_prod and "localhost" in self.cors_origins:
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "CORS_ORIGINS contains localhost in %s — set production frontend domain(s).",
                self.environment,
            )

        if is_prod and not self.require_healthy_db_on_startup:
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "REQUIRE_HEALTHY_DB_ON_STARTUP is False in %s — app may serve 500s against dead DB.",
                self.environment,
            )

        if is_prod and not self.metrics_allowed_ips:
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "METRICS_ALLOWED_IPS is not set in %s — /metrics endpoint is publicly accessible. "
                "Set it to the IP(s) of your Prometheus scraper.",
                self.environment,
            )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton"""
    return Settings()
