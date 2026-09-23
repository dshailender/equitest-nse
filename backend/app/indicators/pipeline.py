import pandas as pd
from pydantic import BaseModel, Field

from app.indicators.ema import ema
from app.indicators.high_52w import high_52w


class IndicatorConfig(BaseModel):
    """Configuration for technical indicator calculation pipeline."""

    spans: list[int] = Field(
        default=[20, 50, 150, 200],
        description="EMA spans to compute (e.g. [20, 50, 150, 200])",
    )
    include_high_52w: bool = Field(
        default=True,
        description="Whether to compute 52-week rolling high",
    )
    high_52w_lookback: int = Field(
        default=252,
        description="Lookback window sessions for 52W high calculation",
    )


def compute_indicators(
    df: pd.DataFrame, config: IndicatorConfig | None = None
) -> pd.DataFrame:
    """Computes technical indicators and appends them as columns to OHLCV DataFrame.

    Indicators computed:
    - EMA for each span in config.spans (e.g., ema_20, ema_50, ema_150, ema_200)
    - high_52w (rolling 252 sessions max high, shifted by 1 bar)

    All EMA calculations are performed on corporate-action adjusted close (adj_close).
    52W high calculation uses corporate-action adjusted high price.

    Args:
        df: Input DataFrame containing OHLCV price series.
        config: Indicator configuration specifying spans and lookbacks.

    Returns:
        DataFrame augmented with technical indicator columns.
    """
    if config is None:
        config = IndicatorConfig()

    if df.empty:
        result = df.copy()
        for span in config.spans:
            result[f"ema_{span}"] = pd.Series(dtype=float)
        if config.include_high_52w:
            result["high_52w"] = pd.Series(dtype=float)
        return result

    # Ensure chronological ordering by date
    out_df = df.copy()
    if "date" in out_df.columns:
        out_df.sort_values(by="date", ascending=True, inplace=True)
        out_df.reset_index(drop=True, inplace=True)

    # Resolve adjusted close price series for EMA
    if "adj_close" in out_df.columns:
        price_series = out_df["adj_close"].astype(float)
    elif "close" in out_df.columns:
        price_series = out_df["close"].astype(float)
    else:
        raise ValueError("DataFrame must contain 'adj_close' or 'close' column")

    # Vectorized computation of EMAs
    for span in config.spans:
        col_name = f"ema_{span}"
        out_df[col_name] = ema(price_series, span=span)

    # Vectorized computation of 52-week high if requested
    if config.include_high_52w:
        if "adj_high" in out_df.columns:
            high_series = out_df["adj_high"].astype(float)
        elif (
            "high" in out_df.columns
            and "adj_close" in out_df.columns
            and "close" in out_df.columns
        ):
            # Adjust high for splits/bonuses using adj_close / close factor
            adj_factor = out_df["adj_close"].astype(float) / out_df["close"].astype(
                float
            )
            high_series = out_df["high"].astype(float) * adj_factor
        elif "high" in out_df.columns:
            high_series = out_df["high"].astype(float)
        else:
            high_series = price_series

        out_df["high_52w"] = high_52w(high_series, lookback=config.high_52w_lookback)

    return out_df


def compute_nifty_indicators(
    df: pd.DataFrame, spans: list[int] | None = None
) -> pd.DataFrame:
    """Computes benchmark NIFTY index indicators (EMAs 50 and 200).

    Reuses the core indicator pipeline on NIFTY index OHLCV price series.

    Args:
        df: Input DataFrame containing NIFTY OHLCV price series.
        spans: List of EMA spans to compute. Defaults to [50, 200].

    Returns:
        DataFrame augmented with NIFTY EMA columns.
    """
    nifty_spans = spans if spans is not None else [50, 200]
    config = IndicatorConfig(spans=nifty_spans, include_high_52w=False)
    return compute_indicators(df, config=config)
