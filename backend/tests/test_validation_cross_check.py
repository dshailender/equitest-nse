"""Unit and API integration tests for TradingView cross-check verification engine (REQ-8.1)."""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.v1.schemas import CrossCheckResponse
from app.db.models import BacktestRun
from app.db.session import engine
from app.main import app
from app.validation.cross_check import (
    CROSS_CHECK_COLUMNS,
    generate_cross_check_dataframe,
)
from sqlmodel import Session


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_run_id():
    run_id = "test_run_val_001"
    with Session(engine) as session:
        existing = session.get(BacktestRun, run_id)
        if not existing:
            run_rec = BacktestRun(
                id=run_id,
                created_at="2026-09-24T12:00:00Z",
                status="completed",
                start_date="2020-06-01",
                end_date="2022-04-29",
                config_json='{"corpus": 500000.0, "risk_pct": 0.02, "sl_pct": 0.07}',
            )
            session.add(run_rec)
            session.commit()
    return run_id


def test_cross_check_dataframe_columns_and_dates(sample_run_id):
    """Asserts cross check dataframe has exact columns and one row per trading day."""
    df, csv_str = generate_cross_check_dataframe(
        run_id=sample_run_id,
        symbol="ALPHA",
        filter_dates=True,
    )

    # Assert exact columns
    assert list(df.columns) == CROSS_CHECK_COLUMNS
    assert len(df) > 0

    # Assert date ordering
    dates = df["date"].tolist()
    assert dates == sorted(dates)
    assert df["date"].iloc[0] >= "2020-06-01"
    assert df["date"].iloc[-1] <= "2022-04-29"

    # Assert CSV string matches DataFrame content
    csv_df = pd.read_csv(io.StringIO(csv_str))
    assert list(csv_df.columns) == CROSS_CHECK_COLUMNS
    assert len(csv_df) == len(df)


def test_cross_check_unfiltered_dates():
    """Asserts warm-up and full session history when filter_dates=False or default config."""
    df, csv_str = generate_cross_check_dataframe(
        run_id="default",
        symbol="RELIANCE",
        filter_dates=False,
    )

    assert list(df.columns) == CROSS_CHECK_COLUMNS
    assert len(df) >= 250

    # Assert warm-up NaNs exist in initial rows
    assert np.isnan(df["ema_200"].iloc[0])
    # Assert trailing rows have valid floats
    assert not np.isnan(df["ema_200"].iloc[-1])


def test_cross_check_matches_golden_reliance_ema20():
    """Asserts computed cross-check EMA-20 matches golden reliance_ema20_expected within 1e-6."""
    fixtures_dir = Path(__file__).resolve().parents[2] / "data" / "fixtures"
    expected_csv_path = fixtures_dir / "reliance_ema20_expected.csv"
    assert expected_csv_path.exists()

    expected_df = pd.read_csv(expected_csv_path)

    df, _ = generate_cross_check_dataframe(
        run_id="default",
        symbol="reliance_2020_2023",
        filter_dates=False,
    )

    merged = pd.merge(df, expected_df, on="date", suffixes=("_calc", "_golden"))
    assert len(merged) > 0

    valid_mask = ~merged["ema_20_golden"].isna()
    diff = np.abs(
        merged.loc[valid_mask, "ema_20_calc"] - merged.loc[valid_mask, "ema_20_golden"]
    )
    assert np.max(diff) < 1e-6



def test_api_cross_check_json_endpoint(client, sample_run_id):
    """Happy path: GET /api/v1/validation/{run_id}/{symbol} returns CrossCheckResponse."""
    resp = client.get(f"/api/v1/validation/{sample_run_id}/ALPHA")
    assert resp.status_code == 200

    data = resp.json()
    model = CrossCheckResponse(**data)
    assert model.run_id == sample_run_id
    assert model.symbol == "ALPHA"
    assert model.count == len(model.rows)
    assert model.count > 0
    assert "date,close,ema_20" in model.csv


def test_api_cross_check_csv_endpoint(client, sample_run_id):
    """Happy path: GET /api/v1/validation/{run_id}/{symbol}?format=csv returns CSV file."""
    resp = client.get(f"/api/v1/validation/{sample_run_id}/ALPHA?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]

    csv_lines = resp.text.strip().split("\n")
    header = csv_lines[0].strip()
    assert header == ",".join(CROSS_CHECK_COLUMNS)
    assert len(csv_lines) > 1


def test_api_cross_check_error_paths(client, sample_run_id):
    """Error paths: unknown run and unknown symbol."""
    # 1. Unknown run
    resp = client.get("/api/v1/validation/non_existent_run_999/ALPHA")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    # 2. Unknown symbol
    resp = client.get(f"/api/v1/validation/{sample_run_id}/UNKNOWN_SYMBOL_XYZ")
    assert resp.status_code == 404
    assert "no price data found" in resp.json()["detail"].lower()
