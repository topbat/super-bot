from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SUPERBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./data/superbot.db"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "superbot-artifacts"
    s3_access_key_ref: str = "env:SUPERBOT_S3_ACCESS_KEY"
    s3_secret_key_ref: str = "env:SUPERBOT_S3_SECRET_KEY"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8420, ge=1, le=65535)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()

