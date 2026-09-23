from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.indicators.ema import ema


def test_golden_file_reliance_ema20():
    """Golden-file test: compares EMA-20 to committed expected CSV within 1e-6."""
    fixtures_dir = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"
    parquet_path = fixtures_dir / "reliance_2020_2023.parquet"
    expected_csv_path = fixtures_dir / "reliance_ema20_expected.csv"

    assert parquet_path.exists(), f"Missing golden fixture: {parquet_path}"
    assert expected_csv_path.exists(), f"Missing expected CSV: {expected_csv_path}"

    df = pd.read_parquet(parquet_path)
    expected_df = pd.read_csv(expected_csv_path)

    actual_ema20 = ema(df["adj_close"], span=20)

    # 1. Assert warm-up NaNs match exactly (first 19 rows are NaN)
    assert actual_ema20.iloc[:19].isna().all(), "First 19 rows must be NaN for span=20"
    assert not np.isnan(
        actual_ema20.iloc[19]
    ), "Row 20 (index 19) must be first valid value"

    # 2. Compare valid values with tolerance 1e-6
    valid_actual = actual_ema20.dropna().values
    valid_expected = expected_df["ema_20"].dropna().values

    assert len(valid_actual) == len(valid_expected)
    assert np.allclose(
        valid_actual, valid_expected, atol=1e-6
    ), f"Max difference {np.max(np.abs(valid_actual - valid_expected))} exceeds 1e-6"


def test_ema_warmup_periods():
    """Verify values only appear after warm-up across multiple spans."""
    # Create 300 synthetic price sessions
    prices = pd.Series(100.0 + np.sin(np.linspace(0, 10, 300)) * 10.0)

    for span in [20, 50, 150, 200]:
        computed = ema(prices, span=span)
        # First span - 1 rows must be NaN
        assert (
            computed.iloc[: span - 1].isna().all()
        ), f"Expected {span - 1} NaNs for span {span}"
        # Row index span - 1 (1-indexed row span) must be non-NaN
        assert not np.isnan(
            computed.iloc[span - 1]
        ), f"Row {span} should be the first valid value for span {span}"
        # All subsequent rows must be non-NaN
        assert (
            not computed.iloc[span - 1 :].isna().any()
        ), f"No NaNs allowed after warm-up for span {span}"


def test_ema_edge_cases():
    """Verify invalid inputs and empty series are handled gracefully."""
    # Invalid span
    with pytest.raises(ValueError, match="must be >= 1"):
        ema(pd.Series([1.0, 2.0]), span=0)

    # Empty series
    empty = pd.Series([], dtype=float)
    res = ema(empty, span=20)
    assert res.empty


# --- Hypothesis Property-Based Tests ---


@given(
    c=st.floats(min_value=0.01, max_value=1e5, allow_nan=False, allow_infinity=False),
    span=st.integers(min_value=2, max_value=50),
    length=st.integers(min_value=51, max_value=200),
)
@settings(max_examples=50)
def test_hypothesis_constant_series(c: float, span: int, length: int):
    """Property test: EMA of a constant series equals the constant."""
    series = pd.Series([c] * length)
    computed = ema(series, span=span)

    # All values from index span-1 onwards must equal c within numerical tolerance
    valid_values = computed.iloc[span - 1 :].values
    assert np.allclose(
        valid_values, c, atol=1e-5
    ), f"EMA of constant {c} did not equal constant"


@given(
    m=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
    c=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    span=st.integers(min_value=3, max_value=30),
)
@settings(max_examples=50)
def test_hypothesis_increasing_linear_series(m: float, c: float, span: int):
    """Property test: EMA of increasing series is < series and > lagged series."""
    # Length >= 3 * span to test lag properties
    length = 3 * span + 50
    t = np.arange(length, dtype=float)
    series = pd.Series(m * t + c)
    computed = ema(series, span=span)

    # 1. EMA is strictly less than current series value for all warmed-up bars
    assert (
        computed.iloc[span - 1 :] < series.iloc[span - 1 :]
    ).all(), "EMA must lag below the series in a strictly increasing trend"

    # 2. EMA is strictly greater than the lagged series (series shifted by span)
    lagged_series = series.shift(span)
    # Compare where lagged_series is available (from index 2 * span)
    assert (
        computed.iloc[2 * span :] > lagged_series.iloc[2 * span :]
    ).all(), "EMA must be greater than series shifted by span"

    # 3. EMA is strictly monotonically increasing for an increasing series
    diffs = computed.iloc[span:].diff().dropna()
    assert (diffs > 0).all(), "EMA must be strictly increasing"
