from pathlib import Path

import pandas as pd
import pytest

from app.indicators.pipeline import (
    IndicatorConfig,
    compute_indicators,
    compute_nifty_indicators,
)


def test_compute_indicators_equity():
    """Verify compute_indicators appends ema_20, ema_50, ema_150, ema_200, high_52w."""
    fixtures_dir = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"
    df = pd.read_parquet(fixtures_dir / "HDFCBANK.parquet")

    result = compute_indicators(df)

    expected_cols = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "ema_20",
        "ema_50",
        "ema_150",
        "ema_200",
        "high_52w",
    ]
    for col in expected_cols:
        assert (
            col in result.columns
        ), f"Missing column {col} in indicator pipeline output"

    # Total rows preserved
    assert len(result) == len(df)

    # Monotonic ascending date check
    assert result["date"].is_monotonic_increasing


def test_compute_nifty_indicators():
    """Verify NIFTY indicator pipeline computes 50 and 200 EMAs on benchmark prices."""
    fixtures_dir = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"
    nifty_df = pd.read_parquet(fixtures_dir / "NIFTY50.parquet")

    result = compute_nifty_indicators(nifty_df)

    assert "ema_50" in result.columns
    assert "ema_200" in result.columns
    assert "ema_20" not in result.columns
    assert "high_52w" not in result.columns

    # Verify warmup
    assert result["ema_50"].iloc[:49].isna().all()
    assert not result["ema_50"].iloc[49:].isna().any()
    assert result["ema_200"].iloc[:199].isna().all()
    assert not result["ema_200"].iloc[199:].isna().any()


def test_pipeline_custom_config():
    """Verify custom spans and lookback settings."""
    dates = pd.date_range("2021-01-01", periods=100, freq="D").strftime("%Y-%m-%d")
    df = pd.DataFrame(
        {
            "date": dates,
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 100.0,
            "adj_close": 100.0,
            "volume": 1000.0,
        }
    )

    custom_config = IndicatorConfig(
        spans=[10, 30], include_high_52w=True, high_52w_lookback=20
    )
    result = compute_indicators(df, config=custom_config)

    assert "ema_10" in result.columns
    assert "ema_30" in result.columns
    assert "high_52w" in result.columns
    assert "ema_20" not in result.columns

    assert result["ema_10"].iloc[:9].isna().all()
    assert not result["ema_10"].iloc[9:].isna().any()
    assert result["high_52w"].iloc[:20].isna().all()
    assert not result["high_52w"].iloc[20:].isna().any()


def test_pipeline_edge_cases():
    """Verify error handling on empty or invalid DataFrames."""
    # Empty DataFrame
    empty_df = pd.DataFrame()
    res = compute_indicators(empty_df)
    assert res.empty
    assert "ema_20" in res.columns
    assert "high_52w" in res.columns

    # Missing close column
    invalid_df = pd.DataFrame({"open": [1.0], "volume": [10.0]})
    with pytest.raises(ValueError, match="DataFrame must contain"):
        compute_indicators(invalid_df)
