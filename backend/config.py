"""Application configuration using Pydantic Settings"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Cogent"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")
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
    auth0_webhook_secret: str | None = (
        None  # Optional: for webhook signature verification
    )

    # Security
    secret_key: str

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
    ml_validate_on_startup: bool = (
        False  # Set True in prod to fail fast on missing models
    )
    ml_inference_timeout_ms: int = 100  # Max inference time per model
    ml_embedding_cache_enabled: bool = True  # Cache OpenAI embeddings in Redis
    ml_embedding_cache_ttl_days: int = 7  # Time-to-live for cached embeddings

    # Azure Blob (prod model storage)
    azure_blob_connection_string: str | None = None
    azure_blob_model_container: str = "ml-models"

    # Neo4j (causal knowledge graph)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "cogent_neo4j_dev"

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

    def model_post_init(self, __context: object) -> None:
        if (
            "environment" not in self.__pydantic_fields_set__
            and "app_env" in self.__pydantic_fields_set__
        ):
            self.environment = self.app_env


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton"""
    return Settings()
