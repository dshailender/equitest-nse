"""API integration tests for Backtest simulation endpoints (REQ-5.4)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_api_backtest_lifecycle_and_results(client):
    """POST /api/v1/backtest/run launches simulation; GET endpoints retrieve results."""
    payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
        "symbols": ["ALPHA", "BETA", "GAMMA"],
        "config": {
            "corpus": 500000.0,
            "risk_pct": 0.02,
            "stop_loss_pct": 0.07,
            "lot_size": 1,
            "cost_bps": 10.0,
        },
    }

    # 1. Trigger backtest
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    data = post_res.json()
    assert "run_id" in data
    run_id = data["run_id"]
    assert data["status"] in ("pending", "completed")

    # 2. Get status (with TestClient, BackgroundTasks run during request)
    status_res = client.get(f"/api/v1/backtest/{run_id}")
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["run_id"] == run_id
    assert st["status"] == "completed"
    assert st["initial_capital"] == 500000.0
    assert st["final_capital"] == 482707.20
    assert st["total_trades"] == 2
    assert st["win_rate"] == 0.0

    # 3. Get trades ledger
    trades_res = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert trades_res.status_code == 200
    td = trades_res.json()
    assert td["run_id"] == run_id
    assert td["count"] == 2
    assert len(td["trades"]) == 2
    t1 = td["trades"][0]
    assert t1["symbol"] == "ALPHA"
    assert t1["entry_date"] == "2021-05-25"
    assert t1["exit_date"] == "2021-08-10"
    assert t1["exit_reason"] == "gap"

    # 4. Get equity curve
    eq_res = client.get(f"/api/v1/backtest/{run_id}/equity")
    assert eq_res.status_code == 200
    eq = eq_res.json()
    assert eq["run_id"] == run_id
    assert eq["count"] == 500
    assert eq["equity_curve"][0]["equity"] == 500000.0
    assert eq["equity_curve"][-1]["equity"] == 482707.20

    # 5. List runs history
    list_res = client.get("/api/v1/backtest")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert any(r["run_id"] == run_id for r in runs)


def test_api_backtest_not_found(client):
    """GET endpoints return 404 for unknown run_id."""
    unknown = "run_nonexistent_999"
    assert client.get(f"/api/v1/backtest/{unknown}").status_code == 404
    assert client.get(f"/api/v1/backtest/{unknown}/trades").status_code == 404
    assert client.get(f"/api/v1/backtest/{unknown}/equity").status_code == 404


def test_api_backtest_default_symbols(client):
    """POST /api/v1/backtest/run without explicit symbols defaults to tiny universe."""
    payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
    }
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]
    st = client.get(f"/api/v1/backtest/{run_id}").json()
    assert st["status"] == "completed"
    assert st["final_capital"] == 482707.20
