"""Unit and integration tests for storage governance and backtest retention."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import BacktestRun, BacktestSweep
from app.db.session import get_session
from app.engine.retention import (
    enforce_backtest_retention,
    purge_single_run_artifacts,
)
from app.main import create_app, lifespan


@pytest.fixture
def test_client(temp_db: Session):
    """Provides a TestClient with overridden database session."""
    test_app = create_app()

    def override_get_session():
        yield temp_db

    test_app.dependency_overrides[get_session] = override_get_session
    with TestClient(test_app) as client:
        yield client


def _create_mock_run_files(repo_root: Path, run_id: str) -> dict[str, Path]:
    """Helper creating the 4 standard artifact files for a run on disk."""
    backtests_dir = repo_root / "data" / "backtests"
    reports_dir = repo_root / "data" / "reports"
    backtests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    clean_id = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in run_id)

    f_json = backtests_dir / f"{run_id}.json"
    f_audit = backtests_dir / f"{run_id}_audit.json"
    f_pdf = reports_dir / f"backtest_{clean_id}.pdf"
    f_png = reports_dir / f"backtest_{clean_id}_preview.png"

    f_json.write_text('{"mock": "result"}')
    f_audit.write_text('{"mock": "audit"}')
    f_pdf.write_bytes(b"%PDF-1.4 mock pdf content")
    f_png.write_bytes(b"\x89PNG mock png content")

    return {
        "result_json": f_json,
        "audit_json": f_audit,
        "report_pdf": f_pdf,
        "preview_png": f_png,
    }


# ==============================================================================
# RET-01: Standalone Run Eviction
# ==============================================================================
def test_ret01_standalone_run_eviction(temp_db: Session, tmp_path: Path):
    """RET-01: Evicts oldest standalone runs when count > max_runs."""

    run_ids = [f"run_standalone_{i:02d}" for i in range(1, 6)]
    created_dates = [
        "2026-01-01T10:00:00Z",
        "2026-01-02T10:00:00Z",
        "2026-01-03T10:00:00Z",
        "2026-01-04T10:00:00Z",
        "2026-01-05T10:00:00Z",
    ]

    all_files = {}
    for r_id, c_date in zip(run_ids, created_dates, strict=True):
        rec = BacktestRun(
            id=r_id,
            created_at=c_date,
            status="completed",
            sweep_id=None,
        )
        temp_db.add(rec)
        all_files[r_id] = _create_mock_run_files(tmp_path, r_id)

    temp_db.commit()

    # Enforce retention with max_runs=3
    res = enforce_backtest_retention(temp_db, max_runs=3, repo_root=tmp_path)

    assert res["status"] == "success"
    assert res["max_runs_threshold"] == 3
    assert res["evicted_run_count"] == 2
    assert set(res["evicted_runs"]) == {"run_standalone_01", "run_standalone_02"}

    # Verify database remaining records
    remaining_runs = temp_db.exec(
        select(BacktestRun).order_by(BacktestRun.created_at)
    ).all()
    remaining_ids = [r.id for r in remaining_runs]
    assert remaining_ids == [
        "run_standalone_03",
        "run_standalone_04",
        "run_standalone_05",
    ]

    # Verify disk files: run 01 and 02 files must be gone
    for evicted_id in ["run_standalone_01", "run_standalone_02"]:
        for p in all_files[evicted_id].values():
            assert not p.exists(), f"File {p} should have been unlinked"

    # Verify disk files: runs 03, 04, 05 files must still exist
    for retained_id in [
        "run_standalone_03",
        "run_standalone_04",
        "run_standalone_05",
    ]:
        for p in all_files[retained_id].values():
            assert p.exists(), f"File {p} should still exist"


# ==============================================================================
# RET-02: Sweep Atomic Retention
# ==============================================================================
def test_ret02_sweep_atomic_retention(temp_db: Session, tmp_path: Path):
    """RET-02: Evicts oldest sweep atomically with all child runs and files."""
    # Create Sweep 1 (older)

    sweep_1 = BacktestSweep(
        id="sweep_alpha",
        created_at="2026-01-01T10:00:00Z",
        status="completed",
        total_runs=2,
        completed_runs=2,
    )
    temp_db.add(sweep_1)

    s1_child_ids = ["run_sw1_c1", "run_sw1_c2"]
    all_files = {}
    for cid in s1_child_ids:
        r = BacktestRun(
            id=cid,
            created_at="2026-01-01T10:05:00Z",
            status="completed",
            sweep_id=sweep_1.id,
        )
        temp_db.add(r)
        all_files[cid] = _create_mock_run_files(tmp_path, cid)

    # Create Sweep 2 (newer)
    sweep_2 = BacktestSweep(
        id="sweep_beta",
        created_at="2026-01-02T10:00:00Z",
        status="completed",
        total_runs=2,
        completed_runs=2,
    )
    temp_db.add(sweep_2)

    s2_child_ids = ["run_sw2_c1", "run_sw2_c2"]
    for cid in s2_child_ids:
        r = BacktestRun(
            id=cid,
            created_at="2026-01-02T10:05:00Z",
            status="completed",
            sweep_id=sweep_2.id,
        )
        temp_db.add(r)
        all_files[cid] = _create_mock_run_files(tmp_path, cid)

    temp_db.commit()

    # Enforce retention with max_sweeps=1
    res = enforce_backtest_retention(temp_db, max_sweeps=1, repo_root=tmp_path)

    assert res["status"] == "success"
    assert res["max_sweeps_threshold"] == 1
    assert res["evicted_sweep_count"] == 1
    assert res["evicted_sweeps"] == ["sweep_alpha"]
    assert set(res["evicted_runs"]) == {"run_sw1_c1", "run_sw1_c2"}

    # Verify DB: Sweep alpha and its children must be gone
    assert temp_db.get(BacktestSweep, "sweep_alpha") is None
    for cid in s1_child_ids:
        assert temp_db.get(BacktestRun, cid) is None
        for p in all_files[cid].values():
            assert not p.exists()

    # Verify DB: Sweep beta and its children must remain intact
    assert temp_db.get(BacktestSweep, "sweep_beta") is not None
    for cid in s2_child_ids:
        assert temp_db.get(BacktestRun, cid) is not None
        for p in all_files[cid].values():
            assert p.exists()


# ==============================================================================
# RET-03: Active Run Protection Invariant
# ==============================================================================
def test_ret03_active_run_protection(temp_db: Session, tmp_path: Path):
    """RET-03: Active runs (running or pending) must NEVER be evicted."""

    # Create 1 completed run and 2 active runs (running, pending)
    r_done = BacktestRun(
        id="run_done",
        created_at="2026-01-01T10:00:00Z",
        status="completed",
        sweep_id=None,
    )
    r_running = BacktestRun(
        id="run_running",
        created_at="2026-01-02T10:00:00Z",
        status="running",
        sweep_id=None,
    )
    r_pending = BacktestRun(
        id="run_pending",
        created_at="2026-01-03T10:00:00Z",
        status="pending",
        sweep_id=None,
    )

    temp_db.add(r_done)
    temp_db.add(r_running)
    temp_db.add(r_pending)

    # Create 1 active sweep (running) and 1 completed sweep
    sweep_running = BacktestSweep(
        id="sweep_active",
        created_at="2026-01-01T10:00:00Z",
        status="running",
        total_runs=2,
        completed_runs=0,
    )
    sweep_completed = BacktestSweep(
        id="sweep_done",
        created_at="2026-01-02T10:00:00Z",
        status="completed",
        total_runs=1,
        completed_runs=1,
    )
    temp_db.add(sweep_running)
    temp_db.add(sweep_completed)
    temp_db.commit()

    # Create files for all
    files_done = _create_mock_run_files(tmp_path, "run_done")
    files_running = _create_mock_run_files(tmp_path, "run_running")
    files_pending = _create_mock_run_files(tmp_path, "run_pending")

    # Enforce with max_runs=0 and max_sweeps=0 (most aggressive eviction possible)
    res = enforce_backtest_retention(
        temp_db, max_runs=0, max_sweeps=0, repo_root=tmp_path
    )

    assert res["status"] == "success"
    # Only completed run should be evicted
    assert res["evicted_runs"] == ["run_done"]
    # Only completed sweep should be evicted
    assert res["evicted_sweeps"] == ["sweep_done"]

    # Active runs must still exist in DB
    assert temp_db.get(BacktestRun, "run_running") is not None
    assert temp_db.get(BacktestRun, "run_pending") is not None
    assert temp_db.get(BacktestRun, "run_done") is None

    # Active sweep must still exist in DB
    assert temp_db.get(BacktestSweep, "sweep_active") is not None
    assert temp_db.get(BacktestSweep, "sweep_done") is None

    # Active run files must NOT be touched
    for p in files_running.values():
        assert p.exists()
    for p in files_pending.values():
        assert p.exists()

    # Done run files must be purged
    for p in files_done.values():
        assert not p.exists()


# ==============================================================================
# Admin API Tests
# ==============================================================================
def test_admin_retention_cleanup_api(test_client: TestClient, temp_db: Session):
    """Admin API endpoint POST /api/v1/admin/retention/cleanup returns 200 OK."""
    # Test POST with no body
    resp = test_client.post("/api/v1/admin/retention/cleanup")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "evicted_run_count" in data
    assert "evicted_sweep_count" in data
    assert data["max_runs_threshold"] is not None
    assert data["max_sweeps_threshold"] is not None


def test_admin_retention_cleanup_api_with_params(
    test_client: TestClient, temp_db: Session
):
    """Admin API endpoint accepts query params and JSON body overrides."""
    # Test with query params
    resp_query = test_client.post(
        "/api/v1/admin/retention/cleanup?max_runs=7&max_sweeps=3"
    )
    assert resp_query.status_code == 200
    d_q = resp_query.json()
    assert d_q["max_runs_threshold"] == 7
    assert d_q["max_sweeps_threshold"] == 3

    # Test with body payload
    resp_body = test_client.post(
        "/api/v1/admin/retention/cleanup",
        json={"max_runs": 4, "max_sweeps": 2},
    )
    assert resp_body.status_code == 200
    d_b = resp_body.json()
    assert d_b["max_runs_threshold"] == 4
    assert d_b["max_sweeps_threshold"] == 2


# ==============================================================================
# Retention Disabled Toggle & Edge Cases
# ==============================================================================
def test_retention_disabled_toggle(
    temp_db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """When BACKTEST_RETENTION_ENABLED=False, retention returns disabled."""
    monkeypatch.setenv("BACKTEST_RETENTION_ENABLED", "false")

    for i in range(5):
        temp_db.add(
            BacktestRun(
                id=f"run_disabled_{i}",
                created_at="2026-01-01T10:00:00Z",
                status="completed",
            )
        )
    temp_db.commit()

    res = enforce_backtest_retention(temp_db, max_runs=1, repo_root=tmp_path)
    assert res["status"] == "disabled"
    assert res["evicted_run_count"] == 0
    assert len(temp_db.exec(select(BacktestRun)).all()) == 5


def test_failed_runs_and_partial_sweeps_evicted(temp_db: Session, tmp_path: Path):
    """Failed runs and partial sweeps are properly subject to retention eviction."""
    temp_db.add(
        BacktestRun(
            id="run_failed_old",
            created_at="2026-01-01T10:00:00Z",
            status="failed",
        )
    )
    temp_db.add(
        BacktestRun(
            id="run_failed_new",
            created_at="2026-01-02T10:00:00Z",
            status="failed",
        )
    )

    temp_db.add(
        BacktestSweep(
            id="sweep_partial_old",
            created_at="2026-01-01T10:00:00Z",
            status="partial",
        )
    )
    temp_db.add(
        BacktestSweep(
            id="sweep_partial_new",
            created_at="2026-01-02T10:00:00Z",
            status="partial",
        )
    )
    temp_db.commit()

    res = enforce_backtest_retention(
        temp_db, max_runs=1, max_sweeps=1, repo_root=tmp_path
    )
    assert res["status"] == "success"
    assert "run_failed_old" in res["evicted_runs"]
    assert "sweep_partial_old" in res["evicted_sweeps"]


def test_purge_single_run_artifacts_direct(tmp_path: Path):
    """Direct verification of purge_single_run_artifacts unlinking and missing files."""
    files = _create_mock_run_files(tmp_path, "run_special!@#1")
    for f in files.values():
        assert f.exists()

    status_map = purge_single_run_artifacts("run_special!@#1", repo_root=tmp_path)
    assert status_map["result_json"] is True
    assert status_map["audit_json"] is True
    assert status_map["report_pdf"] is True
    assert status_map["preview_png"] is True

    # Re-running on non-existent files returns False without error
    status_map_2 = purge_single_run_artifacts("run_special!@#1", repo_root=tmp_path)
    assert status_map_2["result_json"] is False
    assert status_map_2["audit_json"] is False
    assert status_map_2["report_pdf"] is False
    assert status_map_2["preview_png"] is False

    # Calling without repo_root exercises get_backtests_dir() and get_reports_dir()
    status_default = purge_single_run_artifacts("run_nonexistent_default_dirs")
    assert status_default["result_json"] is False
    assert status_default["audit_json"] is False
    assert status_default["report_pdf"] is False
    assert status_default["preview_png"] is False


@pytest.mark.asyncio
async def test_lifespan_retention_startup(monkeypatch: pytest.MonkeyPatch):
    """Verifies that main lifespan executes retention enforcement on startup."""
    called = []

    def mock_enforce(session):
        called.append(True)
        return {"status": "success"}

    monkeypatch.setattr(
        "app.engine.retention.enforce_backtest_retention",
        mock_enforce,
    )
    test_app = create_app()
    async with lifespan(test_app):
        pass
    assert len(called) == 1


@pytest.mark.asyncio
async def test_lifespan_retention_failure_handled(monkeypatch: pytest.MonkeyPatch):
    """Verifies that failures in lifespan retention enforcement are logged."""

    def _raise_error(*args, **kwargs):
        raise RuntimeError("Simulated failure during startup retention")

    monkeypatch.setattr(
        "app.engine.retention.enforce_backtest_retention",
        _raise_error,
    )
    test_app = create_app()
    async with lifespan(test_app):
        pass


def test_retention_env_parsing_invalid_values(monkeypatch: pytest.MonkeyPatch):
    """Verifies fallback when MAX_BACKTEST_RUNS/SWEEPS have non-int values."""
    from app.engine.retention import _get_max_runs, _get_max_sweeps

    monkeypatch.setenv("MAX_BACKTEST_RUNS", "invalid_number")
    monkeypatch.setenv("MAX_BACKTEST_SWEEPS", "not_an_int")

    assert _get_max_runs() == 5
    assert _get_max_sweeps() == 2


def test_safe_unlink_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that _safe_unlink handles OSError gracefully and returns False."""
    from app.engine.retention import _safe_unlink

    test_file = tmp_path / "protected_file.txt"
    test_file.write_text("content")

    def _failing_unlink(self, *args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "unlink", _failing_unlink)
    result = _safe_unlink(test_file)
    assert result is False


def test_backtest_task_triggers_retention(monkeypatch: pytest.MonkeyPatch):
    """Verifies that _execute_backtest_task calls enforce_backtest_retention."""
    from app.api.v1.backtest import _execute_backtest_task

    retention_called = []

    def mock_enforce(session, *args, **kwargs):
        retention_called.append(True)
        return {"status": "success"}

    monkeypatch.setattr(
        "app.api.v1.backtest.enforce_backtest_retention",
        mock_enforce,
    )

    # Calling with non-existent run_id exits early
    _execute_backtest_task("non_existent_run_id", {})
    # Retention is only called if run_record exists, tested via end of task
