from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DATABASE_URL: str = "sqlite:///./dev.db"
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "0.1.0"
    DATA_SOURCE: str = "yfinance"
    FIXTURES_DIR: str = "data/fixtures"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
