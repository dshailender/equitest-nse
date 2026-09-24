"""Unit tests for Monthly Returns Matrix Aggregation (REQ-7.2)."""

from pathlib import Path
import pandas as pd
import pytest

from app.engine.backtest import Backtest
from app.reports.monthly import compute_monthly_returns
from app.strategy.config import StrategyConfig

TINY_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "fixtures"
    / "tiny_universe"
)


@pytest.fixture
def tiny_universe_equity():
    """Runs backtest on tiny_universe and returns mark-to-market equity curve."""
    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")
    prices = {
        "ALPHA": pd.read_parquet(TINY_DIR / "ALPHA.parquet"),
        "BETA": pd.read_parquet(TINY_DIR / "BETA.parquet"),
        "GAMMA": pd.read_parquet(TINY_DIR / "GAMMA.parquet"),
    }
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    res = engine.run()
    return res.equity_curve


def test_monthly_returns_on_phase5_fixture(tiny_universe_equity):
    """Asserts monthly compounded returns matrix across 2020, 2021, and 2022 on golden fixture."""
    matrix = compute_monthly_returns(tiny_universe_equity)

    assert len(matrix) == 3
    years = [row["year"] for row in matrix]
    assert years == [2020, 2021, 2022]

    # Year 2020: Data begins in June 2020
    y2020 = matrix[0]
    assert y2020["jan"] is None
    assert y2020["feb"] is None
    assert y2020["mar"] is None
    assert y2020["apr"] is None
    assert y2020["may"] is None
    assert y2020["jun"] == 0.0
    assert y2020["dec"] == 0.0
    assert y2020["total"] == 0.0

    # Year 2021: First trade entered May 2021, gap loss Aug 2021
    y2021 = matrix[1]
    assert y2021["jan"] == 0.0
    assert y2021["apr"] == 0.0
    assert y2021["may"] == 0.0006
    assert y2021["jun"] == 0.0014
    assert y2021["jul"] == 0.0014
    assert y2021["aug"] == -0.0340
    assert y2021["nov"] == 0.0014
    assert y2021["dec"] == 0.0012
    assert y2021["total"] == -0.0282

    # Year 2022: Second trade exit Feb 2022, data ends April 2022
    y2022 = matrix[2]
    assert y2022["jan"] == 0.0011
    assert y2022["feb"] == -0.0077
    assert y2022["mar"] == 0.0
    assert y2022["apr"] == 0.0
    assert y2022["may"] is None
    assert y2022["dec"] is None
    assert y2022["total"] == -0.0066

    # Compounded overall return check: (1 + total_2020) * (1 + total_2021) * (1 + total_2022) - 1
    cum_tot = (1.0 + y2020["total"]) * (1.0 + y2021["total"]) * (1.0 + y2022["total"]) - 1.0
    assert round(cum_tot, 4) == -0.0346


def test_monthly_returns_empty_and_invalid_inputs():
    """Asserts graceful handling of empty or malformed DataFrames."""
    assert compute_monthly_returns(pd.DataFrame()) == []
    assert compute_monthly_returns(pd.DataFrame({"date": ["2023-01-01"]})) == []
    assert compute_monthly_returns(pd.DataFrame({"equity": [500000.0]})) == []


def test_monthly_returns_synthetic_multi_month():
    """Asserts accurate monthly compounding on handcrafted daily equity series."""
    eq_data = pd.DataFrame([
        {"date": "2023-01-02", "equity": 100000.0},
        {"date": "2023-01-15", "equity": 105000.0},
        {"date": "2023-01-31", "equity": 110000.0},  # +10% in Jan
        {"date": "2023-02-01", "equity": 110000.0},
        {"date": "2023-02-28", "equity": 99000.0},   # -10% in Feb (99k / 110k - 1 = -0.10)
    ])
    matrix = compute_monthly_returns(eq_data)
    assert len(matrix) == 1
    row = matrix[0]
    assert row["year"] == 2023
    assert row["jan"] == 0.1000
    assert row["feb"] == -0.1000
    assert row["mar"] is None
    assert row["total"] == -0.0100  # (1 + 0.10) * (1 - 0.10) - 1 = -0.01
