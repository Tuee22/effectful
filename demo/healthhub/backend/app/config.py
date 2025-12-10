"""Application configuration with Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Doctrine 7: Configuration Lifecycle Management
    - Pydantic BaseSettings for environment variable loading
    - Created ONLY in FastAPI lifespan context manager
    - Immutable after creation (frozen via model_config)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,  # Immutability via Pydantic
    )

    # Application
    app_name: str = "HealthHub Medical Center"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"

    # Database
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # Redis
    redis_host: str
    redis_port: int
    redis_db: int = 0

    # Pulsar
    pulsar_url: str
    pulsar_admin_url: str

    # MinIO S3
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False

    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    jwt_refresh_token_expire_days: int

    # CORS
    cors_origins: list[str] = ["http://localhost:8851"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
