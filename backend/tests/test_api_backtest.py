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
    """POST /api/v1/backtest/run without symbols resolves universe constituents."""
    payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
    }
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]
    st = client.get(f"/api/v1/backtest/{run_id}").json()
    assert st["status"] == "completed"
    assert st["final_capital"] == 630365.73
    assert st["total_trades"] == 87

    # Verify trades ledger contains universe constituents and not ALPHA/BETA/GAMMA
    trades_res = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert trades_res.status_code == 200
    trades_data = trades_res.json()
    symbols_traded = {t["symbol"] for t in trades_data["trades"]}
    assert len(symbols_traded) > 10
    assert "FEDERALBNK" in symbols_traded
    assert "ALPHA" not in symbols_traded
    assert "BETA" not in symbols_traded
    assert "GAMMA" not in symbols_traded


def test_api_backtest_default_parameters_resolves_universe(client):
    """POST /api/v1/backtest/run with empty payload resolves universe."""
    post_res = client.post("/api/v1/backtest/run", json={})
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]
    st = client.get(f"/api/v1/backtest/{run_id}").json()
    assert st["status"] == "completed"
    trades_res = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert trades_res.status_code == 200
    trades_data = trades_res.json()
    symbols_traded = {t["symbol"] for t in trades_data["trades"]}
    assert "ALPHA" not in symbols_traded
    assert "BETA" not in symbols_traded
    assert "GAMMA" not in symbols_traded


def test_api_backtest_multi_symbol_fixture_execution(client):
    """AUD-A-003: data/fixtures contains multiple midcap constituents and trades
    diverse midcap stocks.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    fixtures_dir = repo_root / "data" / "fixtures"

    # 1. Verify data/fixtures contains OHLCV parquet files for multiple constituents
    midcap_files = list(fixtures_dir.glob("MIDCAP_STOCK_*.parquet"))
    assert (
        len(midcap_files) >= 20
    ), f"Expected at least 20 midcap fixtures, found {len(midcap_files)}"

    # 2. Run backtest with default parameters and verify trades across diverse stocks
    payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
    }
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]

    trades_res = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert trades_res.status_code == 200
    trades_data = trades_res.json()

    assert trades_data["count"] > 20
    symbols_traded = {t["symbol"] for t in trades_data["trades"]}
    # Diverse midcap stocks must have executed trades
    assert (
        len(symbols_traded) >= 15
    ), f"Expected >= 15 diverse symbols traded, got {len(symbols_traded)}"
    assert all(not s.startswith("MIDCAP_STOCK_") for s in symbols_traded)
    assert all("_" not in s for s in symbols_traded)


def test_api_backtest_pre_2020_fallback_execution(client):
    """AUD-A-004: Pre-2020 backtest runs in offline mode find valid constituent
    price series and execute trades without returning empty series.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    fixtures_dir = repo_root / "data" / "fixtures"

    # 1. Verify data/fixtures contains OHLCV parquet files for fallback sample midcaps
    fallback_tickers = [
        "IDEA",
        "YESBANK",
        "SUZLON",
        "ZOMATO",
        "PAYTM",
        "NYKAA",
        "POLICYBZR",
        "DELHIVERY",
        "TATACHEM",
        "TATACOMM",
    ]
    for sym in fallback_tickers:
        assert (
            fixtures_dir / f"{sym}.parquet"
        ).exists(), f"Missing offline fixture for fallback symbol {sym}"

    # 2. Run backtest with start date prior to 2020-01-01 (triggering fallback)
    payload = {
        "start": "2019-01-01",
        "end": "2020-12-31",
    }
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]

    status_res = client.get(f"/api/v1/backtest/{run_id}")
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["status"] == "completed"
    assert st["total_trades"] > 0

    trades_res = client.get(f"/api/v1/backtest/{run_id}/trades")
    assert trades_res.status_code == 200
    trades_data = trades_res.json()
    assert trades_data["count"] > 0
    symbols_traded = {t["symbol"] for t in trades_data["trades"]}
    # Verify trades were executed in authentic fallback tickers
    assert any(s in fallback_tickers for s in symbols_traded)

    equity_res = client.get(f"/api/v1/backtest/{run_id}/equity")
    assert equity_res.status_code == 200
    eq_data = equity_res.json()
    assert eq_data["count"] > 200


def test_api_backtest_injects_point_in_time_universe_provider(client, monkeypatch):
    """AUD-C-002: Inject point-in-time universe provider into Backtest engine
    during simulation run.

    Acceptance criteria:
    - Backtest executes with universe_provider active.
    - T-1 entry screening calls universe_provider(prev_date) on each trading session.
    """
    from app.engine.backtest import Backtest

    original_run = Backtest.run
    captured_providers = []
    called_dates = []

    def tracking_run(self, *args, **kwargs):
        captured_providers.append(self.universe_provider)
        assert (
            self.universe_provider is not None
        ), "universe_provider must be active on Backtest"
        assert callable(self.universe_provider), "universe_provider must be callable"

        real_provider = self.universe_provider

        def spy_provider(eval_date: str):
            called_dates.append(eval_date)
            return real_provider(eval_date)

        self.universe_provider = spy_provider
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(Backtest, "run", tracking_run)

    # 1. Trigger simulation run with default universe
    payload = {
        "start": "2020-06-01",
        "end": "2022-04-29",
    }
    post_res = client.post("/api/v1/backtest/run", json=payload)
    assert post_res.status_code == 202
    run_id = post_res.json()["run_id"]

    status_res = client.get(f"/api/v1/backtest/{run_id}")
    assert status_res.status_code == 200
    st = status_res.json()
    assert st["status"] == "completed"

    # Verify Acceptance Criterion 1: Backtest executes with universe_provider active
    assert len(captured_providers) == 1
    provider = captured_providers[0]
    assert provider is not None
    assert callable(provider)

    # Verify Acceptance Criterion 2: T-1 entry screening calls
    # universe_provider(prev_date) on each session
    assert len(called_dates) == 500  # 500 trading days evaluated on T-1
    # Prior session T-1 for initial session 2020-06-01
    assert called_dates[0] == "2020-05-29"
    assert "2021-05-25" in called_dates

    # Verify provider output resolves point-in-time tickers and survivorship_bias flag
    tickers, bias = provider("2021-05-25")
    assert isinstance(tickers, list)
    assert len(tickers) == 650
    assert "FEDERALBNK" in tickers
    assert isinstance(bias, bool)
