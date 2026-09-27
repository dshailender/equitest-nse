"""Integration and export tests for Reports API endpoints.

Covers REQ-7.1, REQ-7.2, REQ-7.3.
"""

import io
import json
import uuid
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import BacktestRun
from app.db.session import engine
from app.engine.backtest import Backtest
from app.main import app
from app.strategy.config import StrategyConfig

TINY_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "fixtures"
    / "tiny_universe"
)


@pytest.fixture
def executed_backtest_run_id(tmp_path):
    """Executes backtest, persists result blob and DB record, and returns run_id."""
    run_id = "test_rep_run_001"
    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")
    prices = {
        "ALPHA": pd.read_parquet(TINY_DIR / "ALPHA.parquet"),
        "BETA": pd.read_parquet(TINY_DIR / "BETA.parquet"),
        "GAMMA": pd.read_parquet(TINY_DIR / "GAMMA.parquet"),
    }
    config = StrategyConfig()
    engine_bt = Backtest(config=config, prices=prices, nifty=nifty)
    result = engine_bt.run()

    # Save result blob
    blob_path = tmp_path / f"{run_id}.json"
    result.save(blob_path)

    with Session(engine) as session:
        existing = session.get(BacktestRun, run_id)
        if existing:
            session.delete(existing)
            session.commit()

        run_rec = BacktestRun(
            id=run_id,
            created_at="2026-09-24T12:00:00Z",
            status="completed",
            result_blob_path=str(blob_path),
            initial_capital=500000.0,
            final_capital=result.final_capital,
            total_return_pct=result.total_return_pct,
            cagr=result.cagr,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            max_drawdown_pct=result.max_drawdown_pct,
            config_json=json.dumps(config.to_dict()),
        )
        session.add(run_rec)
        session.commit()

    return run_id


def test_api_report_summary_endpoint(executed_backtest_run_id):
    """Asserts GET /api/v1/reports/{run_id}/summary returns full metrics."""
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{executed_backtest_run_id}/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["run_id"] == executed_backtest_run_id
    assert data["status"] == "completed"
    metrics = data["metrics"]
    assert metrics["total_trades"] == 2
    assert metrics["win_trades"] == 0
    assert metrics["loss_trades"] == 2
    assert metrics["win_rate"] == 0.0
    assert metrics["final_capital"] == 482707.20
    assert metrics["avg_loss"] == -8646.40
    assert metrics["cagr"] == -0.0183
    assert metrics["max_drawdown_pct"] == 0.0383
    assert metrics["avg_days_held"] == 68.0
    assert "benchmark_return" in metrics
    assert "benchmark_cagr" in metrics
    assert "alpha" in metrics
    assert "beta" in metrics
    assert "information_ratio" in metrics


def test_api_report_monthly_endpoint(executed_backtest_run_id):
    """Asserts GET /api/v1/reports/{run_id}/monthly returns month x year matrix."""
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{executed_backtest_run_id}/monthly")
    assert resp.status_code == 200
    data = resp.json()

    assert data["run_id"] == executed_backtest_run_id
    years = data["years"]
    assert len(years) == 3
    assert years[0]["year"] == 2020
    assert years[1]["year"] == 2021
    assert years[2]["year"] == 2022
    assert years[1]["aug"] == -0.0340
    assert years[1]["total"] == -0.0282


def test_api_report_export_csv(executed_backtest_run_id):
    """Asserts CSV export returns text/csv with correct trade row count."""
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{executed_backtest_run_id}/export?format=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert (
        f'filename="{executed_backtest_run_id}_trades.csv"'
        in resp.headers["content-disposition"]
    )

    lines = resp.text.strip().split("\n")
    # 1 header line + 2 executed trade rows
    assert len(lines) == 3
    assert lines[0].startswith("symbol,entry_date,")
    assert "ALPHA" in lines[1]
    assert "ALPHA" in lines[2]


def test_api_report_export_zip(executed_backtest_run_id):
    """Asserts ZIP export returns valid zip bundle with 4 CSV files."""
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{executed_backtest_run_id}/export?format=zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert (
        f'filename="{executed_backtest_run_id}_report.zip"'
        in resp.headers["content-disposition"]
    )

    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        names = zf.namelist()
        assert "summary.csv" in names
        assert "trades.csv" in names
        assert "equity_curve.csv" in names
        assert "monthly_returns.csv" in names

        trades_text = zf.read("trades.csv").decode("utf-8").strip()
        lines = trades_text.split("\n")
        assert len(lines) == 3


def test_api_report_export_xlsx(executed_backtest_run_id):
    """Asserts XLSX export returns valid OpenXML spreadsheet binary."""
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{executed_backtest_run_id}/export?format=xlsx")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert (
        f'filename="{executed_backtest_run_id}_report.xlsx"'
        in resp.headers["content-disposition"]
    )

    # Verify OpenXML OPC container structure
    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        names = zf.namelist()
        assert "[Content_Types].xml" in names
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        assert "xl/worksheets/sheet3.xml" in names
        assert "xl/worksheets/sheet4.xml" in names


def test_api_report_not_found():
    """Asserts 404 on non-existent run ID."""
    client = TestClient(app)
    resp = client.get("/api/v1/reports/non_existent_run/summary")
    assert resp.status_code == 404

    resp_export = client.get("/api/v1/reports/non_existent_run/export")
    assert resp_export.status_code == 404


def test_api_report_not_completed(tmp_path):
    """Asserts 400 when run is still pending or missing result blob."""
    run_id = f"test_pending_run_{uuid.uuid4().hex[:8]}"
    try:
        with Session(engine) as session:
            run_rec = BacktestRun(
                id=run_id,
                created_at="2026-09-24T12:00:00Z",
                status="running",
                initial_capital=500000.0,
            )
            session.add(run_rec)
            session.commit()

        client = TestClient(app)
        resp = client.get(f"/api/v1/reports/{run_id}/summary")
        assert resp.status_code == 400
        assert "has not completed" in resp.json()["detail"]
    finally:
        with Session(engine) as session:
            run_rec = session.get(BacktestRun, run_id)
            if run_rec:
                session.delete(run_rec)
                session.commit()


def test_api_report_export_invalid_format(executed_backtest_run_id):
    """Asserts 422 on unsupported export format."""
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{executed_backtest_run_id}/export?format=docx")
    assert resp.status_code == 422
