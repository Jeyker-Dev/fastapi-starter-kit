from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(min_length=1)
    jwt_secret: SecretStr = Field(min_length=32)
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings once at startup."""
    return Settings()
