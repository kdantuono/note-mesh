"""
App configuration - using pydantic settings for env vars
TODO: might need to split this if it gets too big
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings - loads from .env file"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # basic app stuff
    app_name: str = Field(default="NoteMesh API")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)  # set to True for dev

    # server config
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)

    # DB settings
    database_url: str = Field(
        default="postgresql+asyncpg://notemesh:password@localhost:5432/notemesh"
    )
    database_echo: bool = Field(default=False)  # useful for debugging

    # Redis
    redis_url: str = Field(default="redis://:devpassword@localhost:6379/0", description="Redis connection URL")
    redis_max_connections: int = Field(default=10, description="Redis connection pool size")

    # JWT
    secret_key: str = Field(
        default="your-secret-key-change-in-production", description="JWT secret key"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=15, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")

    # Pagination
    default_page_size: int = Field(default=20, description="Default pagination size")
    max_page_size: int = Field(default=100, description="Maximum pagination size")

    # Rate limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window_minutes: int = Field(default=1, description="Rate limit time window")

    # File upload
    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    allowed_file_extensions: list[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".md"],
        description="Allowed file extensions",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format"
    )

    # Environment
    environment: str = Field(default="development", description="Environment name")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
