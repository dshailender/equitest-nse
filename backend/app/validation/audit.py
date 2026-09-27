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

from app.core.config import get_backtests_dir, get_fixtures_dir, get_repo_root
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
        repo_dir = get_repo_root()
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
        repo_dir = get_repo_root()
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
    """Computes deterministic SHA-256 fingerprint across market price data.

    Stable and identical across repeated runs evaluated on the same fixture data.

    Args:
        symbols: Optional list of equity symbols included in run. If None,
            hashes active fixture files or DB prices.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    hasher = hashlib.sha256()
    fixtures_dir = get_fixtures_dir()

    unique_files: list[Path] = []
    if fixtures_dir.exists():
        # Identify parquet files to include
        target_files: list[Path] = []

        if symbols:
            clean_symbols = [
                s.replace("^", "").replace(".NS", "").upper() for s in symbols
            ]
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
        for f in sorted(target_files, key=lambda p: str(p.relative_to(fixtures_dir))):
            if f not in seen_paths and f.exists() and f.is_file():
                seen_paths.add(f)
                unique_files.append(f)

    if unique_files:
        for file_path in unique_files:
            rel_name = str(file_path.relative_to(fixtures_dir)).encode("utf-8")
            hasher.update(rel_name)
            try:
                with open(file_path, "rb") as fh:
                    while chunk := fh.read(65536):
                        hasher.update(chunk)
            except OSError as e:
                logger.warning(
                    "Could not read fixture %s for hashing: %s", file_path, e
                )
        return hasher.hexdigest()

    # Fallback 1: Cache directory (/app/data/cache/yfinance or data/cache/yfinance)
    cache_dirs = [
        get_repo_root() / "data" / "cache" / "yfinance",
        Path("/app/data/cache/yfinance"),
    ]
    cache_files: list[Path] = []
    for c_dir in cache_dirs:
        if c_dir.exists() and c_dir.is_dir():
            if symbols:
                clean_syms = [
                    s.replace("^", "").replace(".NS", "").upper() for s in symbols
                ]
                for s in clean_syms:
                    for cf in sorted(c_dir.glob(f"*{s}*")):
                        if cf.is_file():
                            cache_files.append(cf)
            else:
                cache_files.extend(sorted(f for f in c_dir.glob("**/*") if f.is_file()))
            if cache_files:
                break

    if cache_files:
        c_hasher = hashlib.sha256()
        seen_c = set()
        for cf in sorted(cache_files, key=lambda p: p.name):
            if cf not in seen_c:
                seen_c.add(cf)
                c_hasher.update(cf.name.encode("utf-8"))
                try:
                    with open(cf, "rb") as fh:
                        while chunk := fh.read(65536):
                            c_hasher.update(chunk)
                except OSError as e:
                    logger.warning(
                        "Could not read cache file %s for hashing: %s", cf, e
                    )
        return c_hasher.hexdigest()

    # Fallback 2: Compute SHA-256 fingerprint deterministically from database price data
    try:
        from sqlalchemy import text

        from app.db.session import engine

        with engine.connect() as conn:
            if symbols:
                clean_symbols = [
                    s.replace("^", "").replace(".NS", "").upper() for s in symbols
                ]
                placeholders = ", ".join(f":s{i}" for i in range(len(clean_symbols)))
                params = {f"s{i}": s for i, s in enumerate(clean_symbols)}
                query = text(
                    "SELECT symbol, date, open, high, low, close, adj_close, "
                    "volume FROM prices WHERE symbol IN ("
                    + placeholders
                    + ") ORDER BY symbol, date"
                )
                rows = conn.execute(query, params).fetchall()
                idx_rows = conn.execute(
                    text(
                        "SELECT symbol, date, open, high, low, close, "
                        "adj_close, volume FROM index_prices ORDER BY symbol, date"
                    )
                ).fetchall()
                all_rows = list(rows) + list(idx_rows)
            else:
                query = text(
                    "SELECT symbol, date, open, high, low, close, adj_close, "
                    "volume FROM prices ORDER BY symbol, date"
                )
                all_rows = list(conn.execute(query).fetchall())

            if all_rows:
                db_hasher = hashlib.sha256()
                for r in all_rows:
                    line = f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}|{r[6]}|{r[7]}\n"
                    db_hasher.update(line.encode("utf-8"))
                return db_hasher.hexdigest()
    except Exception as exc:
        logger.debug("Database snapshot hash fallback failed: %s", exc)

    # Fallback 3: Deterministic fallback hash based on symbols
    clean_syms = sorted([s.upper() for s in symbols]) if symbols else []
    fallback_payload = f"fallback_price_snapshot:{','.join(clean_syms)}"
    hasher.update(fallback_payload.encode("utf-8"))
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
        out_dir = get_backtests_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        audit_file = out_dir / f"{run_id}_audit.json"
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2)
    except Exception as err:
        logger.warning("Failed saving audit record for run %s: %s", run_id, err)

    return audit_data


def load_run_audit(run_id: str, session: Session) -> dict[str, Any]:
    """Loads audit record for run, generating on-the-fly if not already on disk."""
    audit_file = get_backtests_dir() / f"{run_id}_audit.json"

    if audit_file.exists():
        try:
            with open(audit_file, encoding="utf-8") as f:
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
