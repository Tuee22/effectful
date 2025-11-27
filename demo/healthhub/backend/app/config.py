"""Application configuration with Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "HealthHub Medical Center"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "healthhub_db"
    postgres_user: str = "healthhub"
    postgres_password: str = "healthhub_secure_pass"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Pulsar
    pulsar_url: str = "pulsar://localhost:6650"
    pulsar_admin_url: str = "http://localhost:8080"

    # MinIO S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "healthhub_minio"
    minio_secret_key: str = "healthhub_minio_secret"
    minio_bucket: str = "healthhub-medical-docs"
    minio_secure: bool = False

    # JWT Authentication
    jwt_secret_key: str = "change_this_secret_key_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8850"]
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


# Global settings instance
settings = Settings()
