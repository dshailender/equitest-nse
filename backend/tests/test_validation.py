import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.ingest import InvariantViolationError, validate_ohlcv_dataframe


# Strategy generating valid OHLCV series
@st.composite
def valid_ohlcv_dataframe_strategy(draw):
    size = draw(st.integers(min_value=2, max_value=20))
    start_ts = pd.Timestamp("2022-01-01")
    dates = [
        (start_ts + pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(size)
    ]

    opens = [
        draw(
            st.floats(
                min_value=10.0, max_value=5000.0, allow_nan=False, allow_infinity=False
            )
        )
        for _ in range(size)
    ]
    closes = [
        draw(
            st.floats(
                min_value=10.0, max_value=5000.0, allow_nan=False, allow_infinity=False
            )
        )
        for _ in range(size)
    ]
    high_offsets = [
        draw(
            st.floats(
                min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False
            )
        )
        for _ in range(size)
    ]
    low_offsets = [
        draw(
            st.floats(
                min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
            )
        )
        for _ in range(size)
    ]

    highs = [
        max(o, c) + h
        for o, c, h in zip(opens, closes, high_offsets, strict=True)
    ]
    lows = [
        max(0.1, min(o, c) - low_off)
        for o, c, low_off in zip(opens, closes, low_offsets, strict=True)
    ]
    adj_closes = [
        draw(
            st.floats(
                min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False
            )
        )
        for _ in range(size)
    ]
    volumes = [
        draw(
            st.floats(
                min_value=0.0, max_value=1e8, allow_nan=False, allow_infinity=False
            )
        )
        for _ in range(size)
    ]

    df = pd.DataFrame(
        {
            "date": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "adj_close": adj_closes,
            "volume": volumes,
        }
    )
    return df


@given(valid_ohlcv_dataframe_strategy())
@settings(max_examples=40)
def test_hypothesis_valid_ohlcv(df: pd.DataFrame):
    """Property test: valid OHLCV frames must pass validation without error."""
    validate_ohlcv_dataframe(df)


@given(st.floats(min_value=100.0, max_value=500.0))
def test_hypothesis_high_less_than_low_fails(price: float):
    """Property test: High < Low must strictly raise InvariantViolationError."""
    df = pd.DataFrame(
        {
            "date": ["2022-01-01"],
            "open": [price],
            "high": [price - 5.0],  # high is lower than low
            "low": [price],
            "close": [price],
            "adj_close": [price],
            "volume": [1000.0],
        }
    )
    with pytest.raises(InvariantViolationError):
        validate_ohlcv_dataframe(df)


def test_validation_nans_rejected():
    """Verify that NaNs in any OHLCV price column are rejected."""
    df = pd.DataFrame(
        {
            "date": ["2022-01-01", "2022-01-02"],
            "open": [100.0, np.nan],
            "high": [105.0, 105.0],
            "low": [95.0, 95.0],
            "close": [102.0, 101.0],
            "adj_close": [102.0, 101.0],
            "volume": [1000.0, 1000.0],
        }
    )
    with pytest.raises(InvariantViolationError, match="contains NaN values"):
        validate_ohlcv_dataframe(df)


def test_validation_non_monotonic_dates_rejected():
    """Verify that descending or unordered dates are rejected."""
    df = pd.DataFrame(
        {
            "date": ["2022-01-02", "2022-01-01"],  # Out of order
            "open": [100.0, 100.0],
            "high": [105.0, 105.0],
            "low": [95.0, 95.0],
            "close": [102.0, 101.0],
            "adj_close": [102.0, 101.0],
            "volume": [1000.0, 1000.0],
        }
    )
    with pytest.raises(InvariantViolationError, match="strictly monotonic"):
        validate_ohlcv_dataframe(df)
