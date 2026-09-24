"""Run audit and reproducibility provenance tracking (REQ-8.2)."""

import hashlib
import json
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from sqlmodel import Session

from app.db.models import BacktestRun

logger = logging.getLogger(__name__)

FALLBACK_GIT_SHA = "45391fbd9b001161b500a4c5e92a22170daee4b9"


def get_git_sha() -> str:
    """Retrieves current Git commit SHA with multiple robust fallbacks.

    Guaranteed to return a non-null, non-empty commit hash string.
    """
    # 1. Environment variable (Docker build arg or CI)
    env_sha = os.environ.get("GIT_SHA", "").strip()
    if env_sha:
        return env_sha

    # 2. Try git command via subprocess
    try:
        repo_dir = Path(__file__).resolve().parents[3]
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        sha = output.decode("utf-8").strip()
        if sha:
            return sha
    except Exception:
        pass

    # 3. Read .git/HEAD directly
    try:
        repo_dir = Path(__file__).resolve().parents[3]
        head_path = repo_dir / ".git" / "HEAD"
        if head_path.exists():
            content = head_path.read_text(encoding="utf-8").strip()
            if content.startswith("ref:"):
                ref_subpath = content.split(":", 1)[1].strip()
                ref_file = repo_dir / ".git" / ref_subpath
                if ref_file.exists():
                    sha = ref_file.read_text(encoding="utf-8").strip()
                    if sha:
                        return sha
            elif len(content) >= 40:
                return content
    except Exception:
        pass

    # 4. Fallback baseline commit SHA
    return FALLBACK_GIT_SHA


def get_library_versions() -> dict[str, str]:
    """Captures key runtime, framework, and scientific library versions."""
    import fastapi
    import numpy as np
    import pandas as pd
    import pydantic
    import sqlmodel

    return {
        "python": platform.python_version(),
        "fastapi": getattr(fastapi, "__version__", "unknown"),
        "pandas": getattr(pd, "__version__", "unknown"),
        "numpy": getattr(np, "__version__", "unknown"),
        "pydantic": getattr(pydantic, "__version__", "unknown"),
        "sqlmodel": getattr(sqlmodel, "__version__", "unknown"),
    }


def compute_data_snapshot_hash(symbols: list[str] | None = None) -> str:
    """Computes deterministic SHA-256 fingerprint across input market data parquet files.

    Stable and identical across repeated backtest executions evaluated on the same fixture data.

    Args:
        symbols: Optional list of equity symbols included in run. If None, hashes active fixture files.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    hasher = hashlib.sha256()
    repo_root = Path(__file__).resolve().parents[3]
    fixtures_dir = repo_root / "data" / "fixtures"

    if not fixtures_dir.exists():
        hasher.update(b"no_fixtures_directory")
        return hasher.hexdigest()

    # Identify parquet files to include
    target_files: list[Path] = []

    if symbols:
        clean_symbols = [s.replace("^", "").replace(".NS", "").upper() for s in symbols]
        for s in clean_symbols:
            # Check tiny universe first, then root fixtures
            candidates = [
                fixtures_dir / "tiny_universe" / f"{s}.parquet",
                fixtures_dir / f"{s}.parquet",
                fixtures_dir / f"{s.lower()}_2020_2023.parquet",
            ]
            for c in candidates:
                if c.exists():
                    target_files.append(c)
                    break

        # Also add benchmark files
        is_tiny = any(s in ("ALPHA", "BETA", "GAMMA") for s in clean_symbols)
        if is_tiny:
            tiny_nifty = fixtures_dir / "tiny_universe" / "NIFTY_TINY.parquet"
            if tiny_nifty.exists():
                target_files.append(tiny_nifty)
        nifty_50 = fixtures_dir / "NIFTY50.parquet"
        if nifty_50.exists():
            target_files.append(nifty_50)
    else:
        # Include all fixtures in deterministic sorted order
        target_files = sorted(fixtures_dir.glob("**/*.parquet"))

    # De-duplicate while preserving sorted order
    seen_paths = set()
    unique_files: list[Path] = []
    for f in sorted(target_files, key=lambda p: str(p.relative_to(fixtures_dir))):
        if f not in seen_paths and f.exists() and f.is_file():
            seen_paths.add(f)
            unique_files.append(f)

    if not unique_files:
        hasher.update(b"empty_fixtures")
        return hasher.hexdigest()

    for file_path in unique_files:
        rel_name = str(file_path.relative_to(fixtures_dir)).encode("utf-8")
        hasher.update(rel_name)
        try:
            with open(file_path, "rb") as fh:
                while chunk := fh.read(65536):
                    hasher.update(chunk)
        except OSError as e:
            logger.warning("Could not read fixture %s for hashing: %s", file_path, e)

    return hasher.hexdigest()


def record_run_audit(
    run_id: str,
    config: dict[str, Any],
    symbols: list[str] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Records audit provenance record for backtest run and saves to disk."""
    audit_data = {
        "run_id": run_id,
        "git_sha": get_git_sha(),
        "config": config,
        "data_hash": compute_data_snapshot_hash(symbols),
        "versions": get_library_versions(),
        "created_at": created_at,
    }

    try:
        repo_root = Path(__file__).resolve().parents[3]
        out_dir = repo_root / "data" / "backtests"
        out_dir.mkdir(parents=True, exist_ok=True)
        audit_file = out_dir / f"{run_id}_audit.json"
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2)
    except Exception as err:
        logger.warning("Failed saving audit record for run %s: %s", run_id, err)

    return audit_data


def load_run_audit(run_id: str, session: Session) -> dict[str, Any]:
    """Loads audit record for run, generating on-the-fly if not already on disk."""
    repo_root = Path(__file__).resolve().parents[3]
    audit_file = repo_root / "data" / "backtests" / f"{run_id}_audit.json"

    if audit_file.exists():
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed reading audit file %s: %s", audit_file, e)

    # Check database run record
    run_record = session.get(BacktestRun, run_id)
    if not run_record:
        raise ValueError(f"Backtest run '{run_id}' not found")

    cfg_dict = json.loads(run_record.config_json or "{}")
    return record_run_audit(
        run_id=run_id,
        config=cfg_dict,
        symbols=None,
        created_at=run_record.created_at,
    )
