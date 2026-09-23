import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    """Computes Exponential Moving Average (EMA) using pandas ewm.

    Calculates EMA with decay alpha = 2 / (span + 1). Warm-up period requires
    at least `span` sessions, ensuring no NaN leakage beyond the warm-up window
    (i.e., for span=20, index 19 / row 20 is the first non-NaN value).

    Args:
        series: Pandas Series of price values (e.g., adj_close).
        span: Number of sessions in EMA window. Must be >= 1.

    Returns:
        Pandas Series of computed EMA values with initial (span - 1) NaNs.
    """
    if span < 1:
        raise ValueError(f"EMA span must be >= 1, got {span}")

    if series.empty:
        return series.copy()

    # Vectorized computation using pandas ewm
    return series.ewm(span=span, adjust=False, min_periods=span).mean()
