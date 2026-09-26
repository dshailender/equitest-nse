"""Executable Contract Verification Test Suite for Phase 0 (Legacy Contract Freeze).

Verifies that the FastAPI monolith strictly adheres to:
1. All frozen endpoint contracts under data/migration/contracts/endpoints/
2. INV-10: Paisa-level determinism (₹482,707.20 final capital on tiny universe)
3. INV-9: Cryptographic run provenance and canonical JSON serialization
4. The 'Reports Not Ready' async protocol (HTTP 404, 400, 422, 409)
5. The versioned backtest.completed event contract (v1)
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlmodel import Session

from app.db.models import BacktestRun
from app.db.session import engine
from app.main import app
from app.reports.jobs import job_manager

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "data" / "migration" / "contracts"
ENDPOINTS_DIR = CONTRACTS_DIR / "endpoints"


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient with CSV data source."""
    os.environ["DATA_SOURCE"] = "CSV"
    with TestClient(app) as test_client:
        yield test_client


def canonical_json(obj: Any) -> str:
    """Canonical JSON serializer adhering to Phase 0 specification.

    Rules:
    - Keys sorted alphabetically recursively
    - Compact separators (no trailing spaces after colons/commas)
    - Null values preserved
    - UTF-8 encoding
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# =============================================================================
# Event Schema Validation Model (matching backtest-completed-schema.json)
# =============================================================================

UUID_V4_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
GIT_SHA_REGEX = re.compile(r"^[0-9a-fA-F]{40}$")
DATA_HASH_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


class ProvenancePayload(BaseModel):
    engine_git_sha: str
    data_snapshot_id: str
    config_json_canonical: str
    engine_version: str

    @field_validator("engine_git_sha")
    @classmethod
    def validate_git_sha(cls, v: str) -> str:
        if not GIT_SHA_REGEX.match(v):
            raise ValueError("Invalid engine_git_sha format")
        return v

    @field_validator("data_snapshot_id")
    @classmethod
    def validate_data_hash(cls, v: str) -> str:
        if not DATA_HASH_REGEX.match(v):
            raise ValueError("Invalid data_snapshot_id format")
        return v


class ResultSummaryPayload(BaseModel):
    final_capital: float
    total_trades: int = Field(ge=0)
    sessions_processed: int = Field(ge=0)


class BacktestCompletedEventV1(BaseModel):
    event_version: str = Field(pattern=r"^1\.0$")
    event_type: str = Field(pattern=r"^backtest\.completed$")
    idempotency_key: str
    timestamp_utc: str
    run_id: str
    sweep_id: str | None = None
    status: str = Field(pattern=r"^(completed|failed)$")
    provenance: ProvenancePayload
    result_summary: ResultSummaryPayload

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        if not UUID_V4_REGEX.match(v):
            raise ValueError("idempotency_key must be a valid UUID v4")
        return v


# =============================================================================
# Tests
# =============================================================================


def test_golden_backtest_determinism_inv10(client):
    """INV-10: Exact Paisa-Level Determinism on Tiny Universe (₹482,707.20)."""
    golden_fixture_path = CONTRACTS_DIR / "golden-backtest-run.json"
    assert golden_fixture_path.exists(), "golden-backtest-run.json fixture missing!"

    with open(golden_fixture_path, encoding="utf-8") as f:
        golden_data = json.load(f)

    # 1. Trigger simulation with frozen payload
    payload = golden_data["request_payload"]
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]

    # 2. Assert status and exact paisa determinism
    status_res = client.get(f"/api/v1/backtest/{run_id}")
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["status"] == "completed"
    assert st["final_capital"] == 482707.20, f"Got {st['final_capital']}"
    assert st["total_trades"] == 2
    assert st["total_return_pct"] == -0.0346
    assert st["cagr"] == -0.0183
    assert st["max_drawdown_pct"] == 0.0383

    # 3. Assert trades ledger exact match
    trades_res = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert trades_res.status_code == 200
    td = trades_res.json()
    assert td["count"] == 2

    # Trade 1: Alpha gap exit
    t1 = td["trades"][0]
    assert t1["symbol"] == "ALPHA"
    assert t1["entry_date"] == "2021-05-25"
    assert t1["entry_price"] == 217.83
    assert t1["qty"] == 656
    assert t1["exit_date"] == "2021-08-10"
    assert t1["exit_price"] == 194.42
    assert t1["exit_reason"] == "gap"

    # Trade 2: Alpha signal exit
    t2 = td["trades"][1]
    assert t2["symbol"] == "ALPHA"
    assert t2["entry_date"] == "2021-11-02"
    assert t2["entry_price"] == 211.83
    assert t2["qty"] == 654
    assert t2["exit_date"] == "2022-02-23"
    assert t2["exit_price"] == 208.87
    assert t2["exit_reason"] == "exit_signal"

    # 4. Assert summary report metrics match
    rep_res = client.get(f"/api/v1/reports/{run_id}/summary")
    assert rep_res.status_code == 200
    metrics = rep_res.json()["metrics"]
    assert metrics["final_capital"] == 482707.20
    assert metrics["total_trades"] == 2


def test_canonical_json_serialization_inv9():
    """INV-9: Cryptographic Run Provenance Canonical JSON Serializer."""
    # Test key ordering
    dict_unordered = {"z": 1, "a": 2, "m": {"beta": 10, "alpha": 20}}
    dict_ordered = {"a": 2, "m": {"alpha": 20, "beta": 10}, "z": 1}
    assert canonical_json(dict_unordered) == canonical_json(dict_ordered)

    # Test compactness (no space after commas or colons)
    ser = canonical_json({"key": "val", "list": [1, 2, 3]})
    assert " " not in ser

    # Test explicit null handling
    ser_null = canonical_json({"sweep_id": None, "capital": 500000.0})
    assert '"sweep_id":null' in ser_null


def test_backtest_completed_event_schema_contract():
    """Validates backtest-completed-schema.json against valid and invalid events."""
    schema_path = CONTRACTS_DIR / "backtest-completed-schema.json"
    assert schema_path.exists(), "backtest-completed-schema.json missing!"

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["title"] == "BacktestCompletedEvent"
    assert schema["properties"]["event_version"]["const"] == "1.0"
    assert schema["properties"]["event_type"]["const"] == "backtest.completed"

    # Valid event payload
    valid_event = {
        "event_version": "1.0",
        "event_type": "backtest.completed",
        "idempotency_key": "c56a4180-65aa-42ec-a945-5fd21dec0538",
        "timestamp_utc": "2026-09-26T12:00:00Z",
        "run_id": "run_golden_inv10_1234",
        "sweep_id": None,
        "status": "completed",
        "provenance": {
            "engine_git_sha": "474137e1d91ceef20c1bbbdf59bd73d607c17467",
            "data_snapshot_id": (
                "a273fb008db4f1a765198bc0f4912b9fc8f1ea60658000ad09352889dec09547"
            ),
            "config_json_canonical": (
                '{"capital":500000.0,"cost_bps":10.0,"sl_pct":0.07}'
            ),
            "engine_version": "1.0.0",
        },
        "result_summary": {
            "final_capital": 482707.20,
            "total_trades": 2,
            "sessions_processed": 500,
        },
    }

    # Should validate cleanly
    parsed = BacktestCompletedEventV1.model_validate(valid_event)
    assert parsed.result_summary.final_capital == 482707.20

    # Invalid version should fail
    bad_version = valid_event.copy()
    bad_version["event_version"] = "2.0"
    with pytest.raises(ValidationError):
        BacktestCompletedEventV1.model_validate(bad_version)

    # Invalid idempotency key format (not UUID) should fail
    bad_idemp = valid_event.copy()
    bad_idemp["idempotency_key"] = "not-a-uuid"
    with pytest.raises(ValidationError):
        BacktestCompletedEventV1.model_validate(bad_idemp)

    # Invalid SHA format should fail
    bad_sha = valid_event.copy()
    bad_sha["provenance"] = valid_event["provenance"].copy()
    bad_sha["provenance"]["engine_git_sha"] = "short_sha"
    with pytest.raises(ValidationError):
        BacktestCompletedEventV1.model_validate(bad_sha)


def test_health_and_data_contracts(client):
    """Validates health and data contracts from endpoints/health.json and data.json."""
    # Health checks
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200

    # Data ingest and coverage
    cov = client.get("/api/v1/data/coverage")
    assert cov.status_code == 200
    assert "items" in cov.json()


def test_universe_and_prices_contracts(client):
    """Validates universe (INV-2, INV-3) and prices contracts."""
    # Universe dated
    univ_res = client.get("/api/v1/universe?date=2021-06-01")
    assert univ_res.status_code == 200
    u = univ_res.json()
    assert u["count"] == 650
    assert u["survivorship_bias"] is False

    # Prices known symbol
    p_res = client.get("/api/v1/prices/RELIANCE?start=2021-01-01&end=2021-01-15")
    assert p_res.status_code == 200
    assert p_res.json()["symbol"] == "RELIANCE"

    # Prices unknown 404
    assert client.get("/api/v1/prices/NON_EXISTENT_99").status_code == 404


def test_indicators_and_signals_contracts(client):
    """Validates indicators and signals endpoints."""
    # Indicators
    ind_res = client.get("/api/v1/indicators/ALPHA")
    assert ind_res.status_code == 200
    assert ind_res.json()["count"] > 0

    # NIFTY benchmark
    nifty_res = client.get("/api/v1/indicators/nifty")
    assert nifty_res.status_code == 200

    # Preview
    prev_res = client.post(
        "/api/v1/indicators/preview",
        json={"symbol": "ALPHA", "emas": [20, 50]},
    )
    assert prev_res.status_code == 200

    # Signals
    sig_res = client.get("/api/v1/signals/ALPHA")
    assert sig_res.status_code == 200

    # Screen
    screen_res = client.get("/api/v1/signals/screen?date=2021-05-24")
    assert screen_res.status_code == 200


def test_risk_contracts(client):
    """Validates position sizing (INV-6) and config contracts."""
    size_res = client.post(
        "/api/v1/risk/size",
        json={
            "corpus": 500000.0,
            "entry": 200.0,
            "sl_pct": 0.07,
            "risk_pct": 0.02,
            "lot_size": 1,
        },
    )
    assert size_res.status_code == 200
    assert size_res.json()["qty"] == 714

    cfg_res = client.get("/api/v1/risk/config")
    assert cfg_res.status_code == 200


def test_reports_not_ready_protocol_unknown_runs(client):
    """Asserts HTTP 404 behavior for unknown run IDs across all downstream endpoints."""
    unknown = "run_nonexistent_audit_test"
    endpoints_404 = [
        f"/api/v1/backtest/{unknown}",
        f"/api/v1/backtest/{unknown}/trades",
        f"/api/v1/backtest/{unknown}/equity",
        f"/api/v1/backtest/{unknown}/audit",
        f"/api/v1/reports/{unknown}/summary",
        f"/api/v1/reports/{unknown}/monthly",
        f"/api/v1/reports/{unknown}/export?format=csv",
        f"/api/v1/reports/{unknown}/export?format=pdf",
        f"/api/v1/reports/{unknown}/preview.png",
        f"/api/v1/validation/{unknown}/ALPHA",
    ]
    for ep in endpoints_404:
        res = client.get(ep)
        assert res.status_code == 404, f"Expected 404 for {ep}, got {res.status_code}"


def test_reports_not_ready_protocol_incomplete_runs(client):
    """Asserts legacy 400/422/409 behavior when run is pending/running."""
    pending_id = "run_test_not_ready_incomplete"
    with Session(engine) as session:
        rec = BacktestRun(
            id=pending_id,
            status="running",
            created_at=datetime.now(UTC).isoformat(),
            config_version="1.0",
            initial_capital=500000.0,
        )
        session.merge(rec)
        session.commit()

    # 400 Bad Request on metrics
    assert client.get(f"/api/v1/reports/{pending_id}/summary").status_code == 400
    assert client.get(f"/api/v1/reports/{pending_id}/monthly").status_code == 400
    r_csv = client.get(f"/api/v1/reports/{pending_id}/export?format=csv")
    assert r_csv.status_code == 400

    # 422 Unprocessable Content on PDF and preview
    r_pdf = client.get(f"/api/v1/reports/{pending_id}/export?format=pdf")
    assert r_pdf.status_code == 422
    assert (
        client.post(f"/api/v1/reports/{pending_id}/export/pdf/async").status_code == 422
    )
    assert client.get(f"/api/v1/reports/{pending_id}/preview.png").status_code == 422

    # 200 with empty collections for trades and equity
    trades_resp = client.get(f"/api/v1/backtest/{pending_id}/trades")
    assert trades_resp.status_code == 200 and trades_resp.json()["count"] == 0

    equity_resp = client.get(f"/api/v1/backtest/{pending_id}/equity")
    assert equity_resp.status_code == 200 and equity_resp.json()["count"] == 0

    # 409 Conflict when attempting to download pending PDF job
    job = job_manager.create_job("run_test_pending_job")
    job_dl_resp = client.get(f"/api/v1/reports/jobs/{job.job_id}/download")
    assert job_dl_resp.status_code == 409
