"""Branding and institutional configuration for PDF reports (REQ-9.2)."""

import json
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import get_repo_root

logger = logging.getLogger(__name__)


class BrandingSettings(BaseSettings):
    """Institutional branding configuration for PDF reports.

    Can be configured via environment variables (BRANDING_*) or by mounting
    `backend/branding.json`.
    """

    firm_name: str = "Backtesting Framework"
    logo_path: str | None = None
    disclaimer_text: str = (
        "For research use only. Past performance does not guarantee future results."
    )
    primary_color: str = "#1f2937"
    footer_note: str = ""

    model_config = SettingsConfigDict(
        env_prefix="BRANDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_branding_settings() -> BrandingSettings:
    """Retrieves active branding settings dynamically.

    Checks for `backend/branding.json` (or repo root `branding.json`) first to allow
    runtime config overrides without code changes, falling back to environment
    variables.
    """
    settings_dict = {}

    # Check candidates for branding.json
    repo_root = get_repo_root()
    candidates = [
        repo_root / "branding.json",
        repo_root / "backend" / "branding.json",
        Path("branding.json").resolve(),
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                with open(candidate, encoding="utf-8") as f:
                    file_data = json.load(f)
                    if isinstance(file_data, dict):
                        settings_dict.update(file_data)
                        break
            except Exception as err:
                logger.warning("Failed to parse branding file %s: %s", candidate, err)

    return BrandingSettings(**settings_dict)
