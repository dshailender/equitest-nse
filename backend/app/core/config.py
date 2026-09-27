import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DATABASE_URL: str = "sqlite:///./dev.db"
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "0.1.0"
    DATA_SOURCE: str = "yfinance"
    FIXTURES_DIR: str = "data/fixtures"
    REPO_ROOT: str | None = None
    BACKTEST_STORAGE_PATH: str = "data/backtests"
    MAX_BACKTEST_RUNS: int = 5
    MAX_BACKTEST_SWEEPS: int = 2
    BACKTEST_RETENTION_ENABLED: bool = True
    YFINANCE_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_repo_root() -> Path:
    """Resolves repo root from REPO_ROOT env var, settings, or safe parent inference."""
    env_root = os.environ.get("REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()

    try:
        s = get_settings()
        if s.REPO_ROOT:
            return Path(s.REPO_ROOT).resolve()
    except Exception:
        pass

    curr = Path(__file__).resolve()
    # Host layout: <repo_root>/backend/app/core/config.py -> parents[3]
    if len(curr.parents) >= 4 and (curr.parents[3] / "backend" / "app").is_dir():
        return curr.parents[3]
    # Container layout: /app/app/core/config.py -> parents[2] (/app)
    if len(curr.parents) >= 3 and (curr.parents[2] / "app" / "core").is_dir():
        return curr.parents[2]
    if len(curr.parents) >= 4:
        return curr.parents[3]
    return curr.parents[2]


def get_fixtures_dir() -> Path:
    """Returns the resolved Path to the fixtures directory."""
    env_val = os.environ.get("FIXTURES_DIR")
    if env_val:
        p = Path(env_val)
        return p if p.is_absolute() else (get_repo_root() / p).resolve()
    try:
        s = get_settings()
        if s.FIXTURES_DIR:
            p = Path(s.FIXTURES_DIR)
            return p if p.is_absolute() else (get_repo_root() / p).resolve()
    except Exception:
        pass
    return (get_repo_root() / "data" / "fixtures").resolve()


def get_backtests_dir() -> Path:
    """Returns the resolved Path to the backtest persistence directory."""
    env_val = os.environ.get("BACKTEST_STORAGE_PATH")
    if env_val:
        p = Path(env_val)
        return p if p.is_absolute() else (get_repo_root() / p).resolve()
    try:
        s = get_settings()
        if s.BACKTEST_STORAGE_PATH:
            p = Path(s.BACKTEST_STORAGE_PATH)
            return p if p.is_absolute() else (get_repo_root() / p).resolve()
    except Exception:
        pass
    return (get_repo_root() / "data" / "backtests").resolve()


def get_reports_dir() -> Path:
    """Returns the resolved Path to the reports directory."""
    env_val = os.environ.get("REPORTS_DIR")
    if env_val:
        p = Path(env_val)
        return p if p.is_absolute() else (get_repo_root() / p).resolve()
    return (get_repo_root() / "data" / "reports").resolve()
