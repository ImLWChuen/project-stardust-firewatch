"""Application and pipeline environment configuration."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized settings resolved from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Project Stardust"
    VERSION: str = "0.1.0"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    DATABASE_URL: str = "postgresql://stardust:stardust_password@localhost:5432/stardust_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    FIRMS_MAP_KEY: str = Field(default="", repr=False)
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"

    DATA_RAW_DIR: str = "./data/raw"
    DATA_INTERIM_DIR: str = "./data/interim"
    DATA_PROCESSED_DIR: str = "./data/processed"


settings = Settings()
