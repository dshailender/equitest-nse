"""Automated artifact retention and cascade purge manager for EquiTest NSE."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from sqlmodel import Session, col, select

from app.core.config import get_backtests_dir, get_reports_dir, settings
from app.db.models import BacktestRun, BacktestSweep

logger = logging.getLogger(__name__)


def _get_max_runs() -> int:
    """Resolves MAX_BACKTEST_RUNS from environment, settings, or fallback 5."""
    env_val = os.environ.get("MAX_BACKTEST_RUNS")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass
    return getattr(settings, "MAX_BACKTEST_RUNS", 5)


def _get_max_sweeps() -> int:
    """Resolves MAX_BACKTEST_SWEEPS from environment, settings, or fallback 2."""
    env_val = os.environ.get("MAX_BACKTEST_SWEEPS")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass
    return getattr(settings, "MAX_BACKTEST_SWEEPS", 2)


def _is_retention_enabled() -> bool:
    """Resolves BACKTEST_RETENTION_ENABLED from env, settings, or fallback True."""
    env_val = os.environ.get("BACKTEST_RETENTION_ENABLED")
    if env_val is not None:
        return env_val.strip().lower() in ("true", "1", "yes")
    return bool(getattr(settings, "BACKTEST_RETENTION_ENABLED", True))


MAX_BACKTEST_RUNS: int = _get_max_runs()
MAX_BACKTEST_SWEEPS: int = _get_max_sweeps()
BACKTEST_RETENTION_ENABLED: bool = _is_retention_enabled()


def _safe_unlink(path: Path) -> bool:
    """Unlinks a file if it exists, logging outcome without throwing."""
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
            logger.debug("Deleted artifact file: %s", path)
            return True
    except OSError as exc:
        logger.warning("Failed to delete artifact file %s: %s", path, exc)
    return False


def purge_single_run_artifacts(
    run_id: str, repo_root: Path | None = None
) -> dict[str, bool]:
    """Purges all disk artifacts associated with a single backtest run."""
    clean_id = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in run_id)
    if repo_root is not None:
        backtests_dir = (repo_root / "data" / "backtests").resolve()
        reports_dir = (repo_root / "data" / "reports").resolve()
    else:
        backtests_dir = get_backtests_dir()
        reports_dir = get_reports_dir()

    deleted_status = {
        "result_json": _safe_unlink(backtests_dir / f"{run_id}.json"),
        "audit_json": _safe_unlink(backtests_dir / f"{run_id}_audit.json"),
        "report_pdf": _safe_unlink(reports_dir / f"backtest_{clean_id}.pdf"),
        "preview_png": _safe_unlink(reports_dir / f"backtest_{clean_id}_preview.png"),
    }
    return deleted_status


def enforce_backtest_retention(
    session: Session,
    max_runs: int | None = None,
    max_sweeps: int | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Enforces MAX_BACKTEST_RUNS and MAX_BACKTEST_SWEEPS retention policies.

    Performs atomic cascading eviction of stale records and associated disk blobs.
    CRITICAL: Active/pending/running runs and sweeps are NEVER touched.
    """
    # 0. Check retention enabled toggle
    if not _is_retention_enabled():
        logger.debug("Backtest retention is disabled; skipping eviction.")
        return {
            "status": "disabled",
            "max_runs_threshold": max_runs if max_runs is not None else _get_max_runs(),
            "max_sweeps_threshold": (
                max_sweeps if max_sweeps is not None else _get_max_sweeps()
            ),
            "evicted_run_count": 0,
            "evicted_sweep_count": 0,
            "evicted_runs": [],
            "evicted_sweeps": [],
        }

    # Resolve effective thresholds
    if max_runs is not None:
        effective_max_runs = max(0, max_runs)
    else:
        effective_max_runs = max(0, _get_max_runs())

    if max_sweeps is not None:
        effective_max_sweeps = max(0, max_sweeps)
    else:
        effective_max_sweeps = max(0, _get_max_sweeps())

    evicted_runs: list[str] = []
    evicted_sweeps: list[str] = []

    # 1. Standalone runs: sweep_id IS NULL and status IN ('completed', 'failed')
    # Active/pending/running runs must NEVER be touched (Active Run Safety Invariant).
    standalone_stmt = (
        select(BacktestRun)
        .where(BacktestRun.sweep_id.is_(None))
        .where(BacktestRun.status.in_(["completed", "failed"]))
        .order_by(col(BacktestRun.created_at).desc())
    )
    standalone_runs = list(session.exec(standalone_stmt).all())

    if len(standalone_runs) > effective_max_runs:
        excess_runs = standalone_runs[effective_max_runs:]
        for run in excess_runs:
            purge_single_run_artifacts(run.id, repo_root=repo_root)
            session.delete(run)
            evicted_runs.append(run.id)
            logger.info(
                "Evicted stale backtest run: %s (created_at=%s)",
                run.id,
                run.created_at,
            )

    # 2. Parameter sweeps: status IN ('completed', 'failed', 'partial')
    # Running/pending sweeps must NEVER be touched.
    sweep_stmt = (
        select(BacktestSweep)
        .where(BacktestSweep.status.in_(["completed", "failed", "partial"]))
        .order_by(col(BacktestSweep.created_at).desc())
    )
    sweeps = list(session.exec(sweep_stmt).all())

    if len(sweeps) > effective_max_sweeps:
        excess_sweeps = sweeps[effective_max_sweeps:]
        for sweep in excess_sweeps:
            children_stmt = select(BacktestRun).where(BacktestRun.sweep_id == sweep.id)
            child_runs = list(session.exec(children_stmt).all())
            for child in child_runs:
                purge_single_run_artifacts(child.id, repo_root=repo_root)
                session.delete(child)
                evicted_runs.append(child.id)

            session.delete(sweep)
            evicted_sweeps.append(sweep.id)
            logger.info(
                "Evicted stale parameter sweep: %s with %d child runs",
                sweep.id,
                len(child_runs),
            )

    session.commit()

    return {
        "status": "success",
        "max_runs_threshold": effective_max_runs,
        "max_sweeps_threshold": effective_max_sweeps,
        "evicted_run_count": len(evicted_runs),
        "evicted_sweep_count": len(evicted_sweeps),
        "evicted_runs": evicted_runs,
        "evicted_sweeps": evicted_sweeps,
    }
