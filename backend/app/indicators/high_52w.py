import pandas as pd


def high_52w(high: pd.Series, lookback: int = 252) -> pd.Series:
    """Computes the 52-week rolling maximum high price.

    Uses a rolling window of `lookback` sessions (default 252 trading days)
    shifted by 1 bar. Bar N's value strictly equals the maximum high of the
    previous `lookback` sessions [N - lookback : N], strictly excluding bar N's
    own high to prevent look-ahead bias.

    Args:
        high: Pandas Series of high prices (e.g. adjusted high or session high).
        lookback: Number of preceding trading sessions to inspect (default 252).

    Returns:
        Pandas Series of rolling 52-week highs with first `lookback` values as NaN.
    """
    if lookback < 1:
        raise ValueError(f"Lookback must be >= 1, got {lookback}")

    if high.empty:
        return high.copy()

    # Shift by 1 to exclude current session, then take rolling max
    return high.shift(1).rolling(window=lookback, min_periods=lookback).max()
