"""Tests for parameter sweep and multi-run compare endpoints (REQ-6.2, REQ-6.3)."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.v1.backtest import _execute_sweep_task
from app.db.models import BacktestRun
from app.db.session import engine
from app.main import app


def test_api_sweep_validation_errors():
    """Validates parameter grid validation errors (empty grid, empty list)."""
    client = TestClient(app)

    # Empty param_grid
    resp = client.post("/api/v1/backtest/sweep", json={"param_grid": {}})
    assert resp.status_code == 400
    assert "param_grid must not be empty" in resp.json()["detail"]

    # Parameter with empty list
    resp = client.post("/api/v1/backtest/sweep", json={"param_grid": {"sl_pct": []}})
    assert resp.status_code == 400
    assert "must have a non-empty list of values" in resp.json()["detail"]


def test_api_sweep_3x3_grid_and_status():
    """Validates 3x3 grid generates 9 child runs and metrics (REQ-6.2)."""
    client = TestClient(app)

    # 3x3 grid: sl_pct [5, 6, 7], risk_pct [1, 2, 3] -> 9 combinations
    payload = {
        "base_config": {
            "capital": 500000.0,
            "cost_bps": 10.0,
        },
        "param_grid": {
            "sl_pct": [5, 6, 7],
            "risk_pct": [1, 2, 3],
        },
        "start": "2020-06-01",
        "end": "2022-04-29",
        "symbols": ["ALPHA", "BETA", "GAMMA"],
    }

    create_resp = client.post("/api/v1/backtest/sweep", json=payload)
    assert create_resp.status_code == 202
    data = create_resp.json()
    sweep_id = data["sweep_id"]
    assert data["total_runs"] == 9
    assert len(data["run_ids"]) == 9
    assert data["status"] == "pending"

    # Query initial sweep status
    status_resp = client.get(f"/api/v1/backtest/sweep/{sweep_id}")
    assert status_resp.status_code == 200
    sweep_data = status_resp.json()
    assert sweep_data["sweep_id"] == sweep_id
    assert sweep_data["total_runs"] == 9
    assert len(sweep_data["runs"]) == 9

    # Execute first 3 runs synchronously to simulate partial sweep progress
    child_tasks = []
    for r in sweep_data["runs"][:3]:
        rid = r["run_id"]
        with Session(engine) as session:
            run_rec = session.get(BacktestRun, rid)
            assert run_rec is not None
        req_dict = {
            "start": "2020-06-01",
            "end": "2022-04-29",
            "symbols": ["ALPHA", "BETA", "GAMMA"],
            "config": {
                "capital": 500000.0,
                "sl_pct": r["params"].get("sl_pct", 0.07),
                "risk_pct": r["params"].get("risk_pct", 0.02),
            },
        }
        child_tasks.append((rid, req_dict))

    _execute_sweep_task(sweep_id, child_tasks)

    # Check progress reflection
    updated_resp = client.get(f"/api/v1/backtest/sweep/{sweep_id}")
    assert updated_resp.status_code == 200
    updated_data = updated_resp.json()
    assert updated_data["completed_runs"] >= 3

    completed_runs = [r for r in updated_data["runs"] if r["status"] == "completed"]
    assert len(completed_runs) >= 3
    first = completed_runs[0]
    assert first["final_capital"] is not None
    assert first["total_return_pct"] is not None
    assert first["cagr"] is not None
    assert first["total_trades"] is not None


def test_api_compare_endpoint():
    """Validates /compare returns rows keyed by run_id with aligned columns."""
    client = TestClient(app)

    # Trigger two runs
    res1 = client.post(
        "/api/v1/backtest/run",
        json={
            "start": "2020-06-01",
            "end": "2022-04-29",
            "symbols": ["ALPHA"],
            "config": {"sl_pct": 0.07, "risk_pct": 0.02},
        },
    )
    assert res1.status_code == 202
    run1 = res1.json()["run_id"]

    res2 = client.post(
        "/api/v1/backtest/run",
        json={
            "start": "2020-06-01",
            "end": "2022-04-29",
            "symbols": ["ALPHA"],
            "config": {"sl_pct": 0.05, "risk_pct": 0.01},
        },
    )
    assert res2.status_code == 202
    run2 = res2.json()["run_id"]

    # Execute both runs
    from app.api.v1.backtest import _execute_backtest_task

    _execute_backtest_task(
        run1,
        {
            "start": "2020-06-01",
            "end": "2022-04-29",
            "symbols": ["ALPHA"],
            "config": {"sl_pct": 0.07, "risk_pct": 0.02},
        },
    )
    _execute_backtest_task(
        run2,
        {
            "start": "2020-06-01",
            "end": "2022-04-29",
            "symbols": ["ALPHA"],
            "config": {"sl_pct": 0.05, "risk_pct": 0.01},
        },
    )

    # Compare endpoint call
    compare_resp = client.get(f"/api/v1/backtest/compare?run_ids={run1},{run2}")
    assert compare_resp.status_code == 200
    comp_data = compare_resp.json()

    assert comp_data["run_ids"] == [run1, run2]
    # Rows keyed by run_id
    assert run1 in comp_data["runs"]
    assert run2 in comp_data["runs"]

    # Assert aligned metric columns exist for both runs
    for rid in (run1, run2):
        row = comp_data["runs"][rid]
        assert "run_id" in row
        assert "initial_capital" in row
        assert "final_capital" in row
        assert "total_return_pct" in row
        assert "cagr" in row
        assert "total_trades" in row
        assert "win_rate" in row
        assert "max_drawdown_pct" in row
        assert "config" in row

    # Assert overlaid equity curves are returned
    assert run1 in comp_data["equity_curves"]
    assert run2 in comp_data["equity_curves"]
    assert len(comp_data["equity_curves"][run1]) > 0
    assert len(comp_data["equity_curves"][run2]) > 0
