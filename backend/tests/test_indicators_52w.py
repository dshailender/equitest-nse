import numpy as np
import pandas as pd
import pytest

from app.indicators.high_52w import high_52w


def test_high_52w_synthetic_series():
    """Unit test on synthetic series asserting bar N equals max(high[N-252:N])."""
    lookback = 252
    total_bars = 400

    # Create a synthetic series with pseudo-random high values
    np.random.seed(42)
    synthetic_highs = pd.Series(100.0 + np.random.uniform(0, 50, size=total_bars))

    # Add a massive spike at bar 300
    synthetic_highs.iloc[300] = 500.0

    result = high_52w(synthetic_highs, lookback=lookback)

    # 1. Warm-up assertion: the first `lookback` bars (indices 0..251) must be NaN
    assert (
        result.iloc[:lookback].isna().all()
    ), f"Expected {lookback} initial NaNs in 52W high"

    # 2. Strict window check: bar N's value must equal max(high[N-lookback:N])
    for n in range(lookback, total_bars):
        expected_max = synthetic_highs.iloc[n - lookback : n].max()
        actual_val = result.iloc[n]
        assert np.isclose(
            actual_val, expected_max
        ), f"Bar {n} mismatch: expected {expected_max}, got {actual_val}"

    # 3. Look-ahead leak prevention: bar 300 has spike of 500.0.
    # Bar 300 itself must NOT show 500.0! Only bars 301 onwards should show 500.0.
    assert (
        result.iloc[300] < 500.0
    ), "Current bar's high must not leak into bar N's 52W high"
    assert result.iloc[301] == 500.0, "Bar 301 must reflect the spike from bar 300"


def test_high_52w_custom_lookback():
    """Verify custom lookback window behavior."""
    lookback = 5
    highs = pd.Series([10.0, 12.0, 15.0, 11.0, 14.0, 20.0, 13.0, 16.0])
    res = high_52w(highs, lookback=lookback)

    # First 5 are NaN
    assert res.iloc[:5].isna().all()
    # Bar 5 (6th element) should be max of elements 0..4 = 15.0
    assert res.iloc[5] == 15.0
    # Bar 6 (7th element) should be max of elements 1..5 = 20.0
    assert res.iloc[6] == 20.0


def test_high_52w_edge_cases():
    """Verify invalid lookback and empty series are handled."""
    with pytest.raises(ValueError, match="must be >= 1"):
        high_52w(pd.Series([1.0]), lookback=0)

    empty = pd.Series([], dtype=float)
    res = high_52w(empty, lookback=252)
    assert res.empty
