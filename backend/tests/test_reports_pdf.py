"""Unit and integration tests for PDF report generation and export endpoints.

Covers REQ-9.1, REQ-9.2, REQ-9.3, REQ-9.4, REQ-9.5, REQ-9.7.
"""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from sqlmodel import Session

from app.db.models import BacktestRun
from app.db.session import engine
from app.engine.backtest import Backtest
from app.engine.result import BacktestResult
from app.main import app
from app.reports.charts import (
    render_drawdown,
    render_equity_curve,
    render_monthly_heatmap,
)
from app.reports.jobs import job_manager
from app.reports.pdf import generate_pdf, sanitize_run_id
from app.strategy.config import StrategyConfig

TINY_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "fixtures"
    / "tiny_universe"
)


@pytest.fixture
def sample_chart_data():
    """Provides sample equity and monthly DataFrames for chart rendering unit tests."""
    dates = pd.date_range("2021-01-01", periods=120, freq="B").strftime("%Y-%m-%d")
    equity_curve = pd.DataFrame(
        {
            "date": dates,
            "equity": [500000.0 * (1.0 + 0.0015 * i) for i in range(120)],
            "drawdown_pct": [-0.01 * (i % 6) / 5.0 for i in range(120)],
        }
    )
    monthly_df = pd.DataFrame(
        [
            {
                "year": 2021,
                "jan": 0.025,
                "feb": -0.012,
                "mar": 0.041,
                "apr": 0.010,
                "total": 0.065,
            },
            {
                "year": 2022,
                "jan": -0.018,
                "feb": 0.035,
                "mar": -0.005,
                "apr": 0.022,
                "total": 0.034,
            },
        ]
    )
    return equity_curve, monthly_df


@pytest.fixture
def golden_backtest_run(tmp_path):
    """Executes tiny_universe golden simulation and persists DB record + result blob."""
    run_id = "test_golden_pdf_run_001"
    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")
    prices = {
        "ALPHA": pd.read_parquet(TINY_DIR / "ALPHA.parquet"),
        "BETA": pd.read_parquet(TINY_DIR / "BETA.parquet"),
        "GAMMA": pd.read_parquet(TINY_DIR / "GAMMA.parquet"),
    }
    config = StrategyConfig()
    engine_bt = Backtest(config=config, prices=prices, nifty=nifty)
    result = engine_bt.run()

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

    return run_id, result


# =========================================================================
# 1. Unit Tests: Charts (REQ-9.3)
# =========================================================================


def test_render_equity_curve_produces_png(sample_chart_data, tmp_path):
    """Asserts equity curve PNG exists, exceeds 5 KB, and has 1200x600 resolution."""
    equity_df, _ = sample_chart_data
    out_file = tmp_path / "equity.png"
    result_path = render_equity_curve(equity_df, out_file)

    assert result_path.exists()
    assert result_path.stat().st_size > 5000
    with Image.open(result_path) as im:
        assert im.size == (1200, 600)


def test_render_drawdown_produces_png(sample_chart_data, tmp_path):
    """Asserts drawdown PNG exists, exceeds 5 KB, and matches 1200x600 resolution."""
    equity_df, _ = sample_chart_data
    out_file = tmp_path / "drawdown.png"
    result_path = render_drawdown(equity_df, out_file)

    assert result_path.exists()
    assert result_path.stat().st_size > 5000
    with Image.open(result_path) as im:
        assert im.size == (1200, 600)


def test_render_monthly_heatmap_produces_png(sample_chart_data, tmp_path):
    """Asserts monthly heatmap PNG exists, exceeds 5 KB, and has 1200x600 resolution."""
    _, monthly_df = sample_chart_data
    out_file = tmp_path / "heatmap.png"
    result_path = render_monthly_heatmap(monthly_df, out_file)

    assert result_path.exists()
    assert result_path.stat().st_size > 5000
    with Image.open(result_path) as im:
        assert im.size == (1200, 600)


def test_charts_are_deterministic(sample_chart_data, tmp_path):
    """Asserts renders of same DataFrames yield identical SHA-256 hashes."""
    equity_df, monthly_df = sample_chart_data

    # Equity Curve
    eq1 = render_equity_curve(equity_df, tmp_path / "eq1.png")
    eq2 = render_equity_curve(equity_df, tmp_path / "eq2.png")
    assert (
        hashlib.sha256(eq1.read_bytes()).hexdigest()
        == hashlib.sha256(eq2.read_bytes()).hexdigest()
    )

    # Drawdown Curve
    dd1 = render_drawdown(equity_df, tmp_path / "dd1.png")
    dd2 = render_drawdown(equity_df, tmp_path / "dd2.png")
    assert (
        hashlib.sha256(dd1.read_bytes()).hexdigest()
        == hashlib.sha256(dd2.read_bytes()).hexdigest()
    )

    # Monthly Heatmap
    hm1 = render_monthly_heatmap(monthly_df, tmp_path / "hm1.png")
    hm2 = render_monthly_heatmap(monthly_df, tmp_path / "hm2.png")
    assert (
        hashlib.sha256(hm1.read_bytes()).hexdigest()
        == hashlib.sha256(hm2.read_bytes()).hexdigest()
    )


# =========================================================================
# 2. Unit Tests: PDF Generation (REQ-9.1, REQ-9.2, REQ-9.5)
# =========================================================================


def test_generate_pdf_fixture_run(golden_backtest_run, tmp_path):
    """Asserts golden PDF contains run_id, key sections, and exact final capital."""
    run_id, _ = golden_backtest_run
    pdf_path = generate_pdf(run_id, include_creation_date=True, output_dir=tmp_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 10000

    reader = PdfReader(pdf_path)
    full_text = "\n".join(page.extract_text() for page in reader.pages)

    assert run_id in full_text
    assert "Executive Summary" in full_text
    assert "Trade Log" in full_text
    assert "Assumptions" in full_text
    assert "482,707.20" in full_text


def test_pdf_is_deterministic(golden_backtest_run, tmp_path):
    """Asserts generate_pdf(include_creation_date=False) has identical sha256."""
    run_id, _ = golden_backtest_run
    pdf_a = generate_pdf(
        run_id,
        include_creation_date=False,
        output_dir=tmp_path / "dir_a",
    )
    pdf_b = generate_pdf(
        run_id,
        include_creation_date=False,
        output_dir=tmp_path / "dir_b",
    )

    sha_a = hashlib.sha256(pdf_a.read_bytes()).hexdigest()
    sha_b = hashlib.sha256(pdf_b.read_bytes()).hexdigest()
    assert sha_a == sha_b


def test_pdf_page_count(golden_backtest_run, tmp_path):
    """Asserts the generated PDF for the golden run has >= 6 pages."""
    run_id, _ = golden_backtest_run
    pdf_path = generate_pdf(run_id, output_dir=tmp_path)
    reader = PdfReader(pdf_path)
    assert len(reader.pages) >= 6


def test_pdf_contains_all_prd_metrics(golden_backtest_run, tmp_path):
    """Asserts all mandatory PRD performance metrics appear in the extracted text."""
    run_id, _ = golden_backtest_run
    pdf_path = generate_pdf(run_id, output_dir=tmp_path)
    reader = PdfReader(pdf_path)
    full_text = "\n".join(page.extract_text() for page in reader.pages)

    mandatory_metrics = [
        "Final Capital",
        "Total Return",
        "Number of Trades",
        "Average Profit",
        "Average Loss",
        "Win %",
    ]
    for metric in mandatory_metrics:
        assert metric in full_text, f"Metric '{metric}' not found in PDF extracted text"


def test_trade_log_pagination(golden_backtest_run, tmp_path):
    """Asserts repeating table header on multiple pages for a 200-trade run."""
    run_id, result = golden_backtest_run

    # Synthesize 200 trades
    base_trade = (
        result.trades.iloc[0].to_dict()
        if not result.trades.empty
        else {
            "symbol": "ALPHA",
            "entry_date": "2021-01-15",
            "entry_price": 200.0,
            "qty": 500,
            "exit_date": "2021-02-15",
            "exit_price": 210.0,
            "pnl": 5000.0,
            "pnl_pct": 0.05,
            "days_held": 31,
            "exit_reason": "signal",
            "costs": 20.0,
        }
    )
    many_trades = []
    for i in range(200):
        t = dict(base_trade)
        t["symbol"] = f"SYM{i:03d}"
        t["entry_date"] = f"2021-{(i % 12) + 1:02d}-01"
        t["exit_date"] = f"2021-{(i % 12) + 1:02d}-15"
        many_trades.append(t)

    result_200 = BacktestResult(
        trades=pd.DataFrame(many_trades),
        equity_curve=result.equity_curve,
        initial_capital=500000.0,
    )

    run_id_200 = "test_run_200_trades"
    blob_path = tmp_path / f"{run_id_200}.json"
    result_200.save(blob_path)

    with Session(engine) as session:
        existing = session.get(BacktestRun, run_id_200)
        if existing:
            session.delete(existing)
            session.commit()
        run_rec = BacktestRun(
            id=run_id_200,
            created_at="2026-09-24T12:00:00Z",
            status="completed",
            result_blob_path=str(blob_path),
            initial_capital=500000.0,
            config_json="{}",
        )
        session.add(run_rec)
        session.commit()

    pdf_path = generate_pdf(run_id_200, output_dir=tmp_path)
    reader = PdfReader(pdf_path)

    # Check for Trade Log table header across pages
    header_count = sum(
        1
        for page in reader.pages
        if "Entry Price" in re.sub(r"\s+", " ", page.extract_text())
        or "Exit Reason" in re.sub(r"\s+", " ", page.extract_text())
    )
    assert header_count >= 2, f"Expected table header on >= 2 pages, got {header_count}"


# =========================================================================
# 3. API Tests: Endpoints & Async Lifecycle (REQ-9.1, REQ-9.4)
# =========================================================================


def test_export_pdf_small_run_streams_pdf(golden_backtest_run):
    """Asserts GET /export?format=pdf streams application/pdf with %PDF bytes."""
    run_id, _ = golden_backtest_run
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{run_id}/export?format=pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")


def test_export_pdf_large_run_returns_202(tmp_path):
    """Asserts GET /export?format=pdf returns 202 Accepted + job_id for >2000 trades."""
    run_id_large = "test_run_large_3000_trades"
    trades = [
        {
            "symbol": "ALPHA",
            "entry_date": "2021-01-01",
            "entry_price": 100.0,
            "qty": 10,
            "exit_date": "2021-01-10",
            "exit_price": 105.0,
            "pnl": 50.0,
            "pnl_pct": 0.05,
            "days_held": 9,
            "exit_reason": "signal",
            "costs": 1.0,
        }
        for _ in range(2500)
    ]
    eq = pd.DataFrame(
        {
            "date": ["2021-01-01", "2021-01-10"],
            "equity": [500000.0, 500050.0],
            "drawdown_pct": [0.0, 0.0],
        }
    )
    result = BacktestResult(
        trades=pd.DataFrame(trades), equity_curve=eq, initial_capital=500000.0
    )
    blob_path = tmp_path / f"{run_id_large}.json"
    result.save(blob_path)

    with Session(engine) as session:
        existing = session.get(BacktestRun, run_id_large)
        if existing:
            session.delete(existing)
            session.commit()
        run_rec = BacktestRun(
            id=run_id_large,
            created_at="2026-09-24T12:00:00Z",
            status="completed",
            result_blob_path=str(blob_path),
            initial_capital=500000.0,
            config_json="{}",
        )
        session.add(run_rec)
        session.commit()

    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{run_id_large}/export?format=pdf")

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert f"/api/v1/reports/jobs/{data['job_id']}" in resp.headers["location"]


def test_job_status_lifecycle(golden_backtest_run, tmp_path):
    """Asserts pending -> ready lifecycle and download endpoint behavior."""
    run_id, _ = golden_backtest_run
    client = TestClient(app)

    # 1. Create a pending job
    job = job_manager.create_job(run_id)
    resp = client.get(f"/api/v1/reports/jobs/{job.job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    # Download when pending returns 409
    dl_resp = client.get(f"/api/v1/reports/jobs/{job.job_id}/download")
    assert dl_resp.status_code == 409

    # 2. Complete the job
    pdf_file = generate_pdf(run_id, output_dir=tmp_path)
    job_manager.update_job(job.job_id, status="ready", file_path=str(pdf_file))

    resp_ready = client.get(f"/api/v1/reports/jobs/{job.job_id}")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "ready"

    # Download when ready returns PDF
    dl_ready = client.get(f"/api/v1/reports/jobs/{job.job_id}/download")
    assert dl_ready.status_code == 200
    assert dl_ready.headers["content-type"] == "application/pdf"
    assert dl_ready.content.startswith(b"%PDF")


def test_export_pdf_unknown_run_returns_404():
    """Asserts unknown run_id returns HTTP 404."""
    client = TestClient(app)
    resp = client.get("/api/v1/reports/nonexistent_run_9999/export?format=pdf")
    assert resp.status_code == 404


def test_export_pdf_incomplete_run_returns_422():
    """Asserts incomplete backtest run returns HTTP 422."""
    incomplete_id = "test_incomplete_run_001"
    with Session(engine) as session:
        existing = session.get(BacktestRun, incomplete_id)
        if existing:
            session.delete(existing)
            session.commit()

        run_rec = BacktestRun(
            id=incomplete_id,
            created_at="2026-09-24T12:00:00Z",
            status="pending",  # Incomplete status
            result_blob_path=None,
            initial_capital=500000.0,
            config_json="{}",
        )
        session.add(run_rec)
        session.commit()

    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{incomplete_id}/export?format=pdf")
    assert resp.status_code == 422


def test_filename_sanitization():
    """Asserts run_id containing path separators is properly sanitized in filename."""
    unsafe_id = "../../etc/passwd"
    sanitized = sanitize_run_id(unsafe_id)
    assert "/" not in sanitized
    assert ".." not in sanitized
    assert "\\" not in sanitized


def test_existing_csv_xlsx_exports_unaffected(golden_backtest_run):
    """Asserts legacy CSV, XLSX, and ZIP exports remain completely unaffected."""
    run_id, _ = golden_backtest_run
    client = TestClient(app)

    # CSV export
    csv_resp = client.get(f"/api/v1/reports/{run_id}/export?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "symbol,entry_date" in csv_resp.text

    # XLSX export
    xlsx_resp = client.get(f"/api/v1/reports/{run_id}/export?format=xlsx")
    assert xlsx_resp.status_code == 200
    assert "spreadsheetml" in xlsx_resp.headers["content-type"]
    assert xlsx_resp.content.startswith(b"PK")

    # ZIP export
    zip_resp = client.get(f"/api/v1/reports/{run_id}/export?format=zip")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
    assert zip_resp.content.startswith(b"PK")


def test_preview_png_endpoint(golden_backtest_run):
    """Asserts GET /reports/{run_id}/preview.png returns valid image/png."""
    run_id, _ = golden_backtest_run
    client = TestClient(app)
    resp = client.get(f"/api/v1/reports/{run_id}/preview.png")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")
