"""Unit and API integration tests for run audit and provenance tracking (REQ-8.2)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.v1.backtest import _execute_backtest_task
from app.api.v1.schemas import BacktestAuditResponse
from app.db.models import BacktestRun
from app.db.session import engine
from app.main import app
from app.validation.audit import (
    compute_data_snapshot_hash,
    get_git_sha,
    get_library_versions,
    load_run_audit,
    record_run_audit,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_git_sha_non_null():
    """Asserts git commit SHA is non-null, non-empty, and valid length."""
    sha = get_git_sha()
    assert sha is not None
    assert isinstance(sha, str)
    assert len(sha) >= 7
    assert sha != ""


def test_library_versions_populated():
    """Asserts library versions dictionary contains expected core packages."""
    versions = get_library_versions()
    assert "python" in versions
    assert "fastapi" in versions
    assert "pandas" in versions
    assert "numpy" in versions
    assert "pydantic" in versions
    assert "sqlmodel" in versions
    for k, v in versions.items():
        assert isinstance(v, str)
        assert v != ""


def test_stable_data_hash_across_runs():
    """Asserts data snapshot hash is strictly deterministic and identical on same fixture."""
    hash1 = compute_data_snapshot_hash(["ALPHA", "BETA", "GAMMA"])
    hash2 = compute_data_snapshot_hash(["ALPHA", "BETA", "GAMMA"])
    assert hash1 is not None
    assert len(hash1) == 64  # SHA-256 length
    assert hash1 == hash2

    # Different symbols set produces different hash
    hash_subset = compute_data_snapshot_hash(["ALPHA"])
    assert hash_subset != hash1


def test_record_and_load_run_audit(tmp_path):
    """Asserts record_run_audit creates file and load_run_audit reads it."""
    import uuid

    run_id = f"test_audit_persistence_{uuid.uuid4().hex[:8]}"
    config = {"corpus": 500000.0, "risk_pct": 0.02, "sl_pct": 0.07}

    audit = record_run_audit(
        run_id=run_id,
        config=config,
        symbols=["ALPHA"],
        created_at="2026-09-24T12:00:00Z",
    )

    assert audit["run_id"] == run_id
    assert audit["git_sha"] == get_git_sha()
    assert audit["config"] == config
    assert len(audit["data_hash"]) == 64

    with Session(engine) as session:
        # Create DB record if needed
        existing = session.get(BacktestRun, run_id)
        if not existing:
            run_rec = BacktestRun(
                id=run_id,
                created_at="2026-09-24T12:00:00Z",
                status="completed",
                config_json=json.dumps(config),
            )
            session.add(run_rec)
            session.commit()

        loaded = load_run_audit(run_id, session)
        assert loaded["run_id"] == run_id
        assert loaded["data_hash"] == audit["data_hash"]


def test_api_backtest_audit_endpoint(client):
    """Happy path & error paths for GET /api/v1/backtest/{run_id}/audit."""
    import uuid

    run_id = f"test_api_audit_run_{uuid.uuid4().hex[:8]}"
    config = {"capital": 500000.0, "risk_pct": 0.02, "sl_pct": 0.07}

    with Session(engine) as session:
        existing = session.get(BacktestRun, run_id)
        if not existing:
            run_rec = BacktestRun(
                id=run_id,
                created_at="2026-09-24T12:00:00Z",
                status="completed",
                config_json=json.dumps(config),
            )
            session.add(run_rec)
            session.commit()

    resp = client.get(f"/api/v1/backtest/{run_id}/audit")
    assert resp.status_code == 200

    data = resp.json()
    model = BacktestAuditResponse(**data)
    assert model.run_id == run_id
    assert model.git_sha is not None and len(model.git_sha) >= 7
    assert len(model.data_hash) == 64
    assert model.config["capital"] == 500000.0
    assert "python" in model.versions

    # Error path: 404 for unknown run
    resp_404 = client.get("/api/v1/backtest/non_existent_run_99999/audit")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


def test_simulation_execution_generates_audit():
    """Asserts that running _execute_backtest_task automatically produces audit file."""
    import uuid

    run_id = f"test_task_audit_gen_{uuid.uuid4().hex[:8]}"
    payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
        "symbols": ["ALPHA"],
        "config": {"corpus": 500000.0, "risk_pct": 0.02, "sl_pct": 0.07},
    }


    with Session(engine) as session:
        run_rec = BacktestRun(
            id=run_id,
            created_at="2026-09-24T12:00:00Z",
            status="pending",
            config_json=json.dumps(payload["config"]),
        )
        session.add(run_rec)
        session.commit()

    _execute_backtest_task(run_id, payload)

    repo_root = Path(__file__).resolve().parents[2]
    audit_file = repo_root / "data" / "backtests" / f"{run_id}_audit.json"
    assert audit_file.exists(), f"Expected audit file {audit_file} to be created by task"

    with open(audit_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["run_id"] == run_id
    assert data["git_sha"] is not None
    assert len(data["data_hash"]) == 64
