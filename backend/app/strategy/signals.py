import pandas as pd

from app.indicators.pipeline import (
    IndicatorConfig,
    compute_indicators,
    compute_nifty_indicators,
)
from app.strategy.config import StrategyConfig


def market_regime_ok(
    nifty_df: pd.DataFrame, config: StrategyConfig | None = None
) -> pd.Series:
    """Evaluates NIFTY benchmark market regime filter (REQ-3.1).

    Rule:
        Close > EMA50 AND Close > EMA200

    System takes 0 trades when this condition evaluates to False.

    Args:
        nifty_df: DataFrame containing NIFTY OHLCV price series.
        config: Strategy configuration containing regime EMA spans.

    Returns:
        pd.Series[bool] indexed by date, representing regime status on each session.
        Never mutates the input DataFrame.
    """
    if nifty_df.empty:
        return pd.Series(dtype=bool, name="regime_ok")

    cfg = config or StrategyConfig()
    fast_span, slow_span = cfg.regime_ema_spans[0], cfg.regime_ema_spans[1]
    col_fast = f"ema_{fast_span}"
    col_slow = f"ema_{slow_span}"

    # Do not mutate input dataframe
    if col_fast not in nifty_df.columns or col_slow not in nifty_df.columns:
        df_calc = compute_nifty_indicators(nifty_df, spans=[fast_span, slow_span])
    else:
        df_calc = nifty_df

    # Extract close price series
    if "close" in df_calc.columns:
        close_series = df_calc["close"].astype(float)
    elif "adj_close" in df_calc.columns:
        close_series = df_calc["adj_close"].astype(float)
    else:
        raise ValueError("nifty_df must contain 'close' or 'adj_close' column")

    ema_fast = df_calc[col_fast].astype(float)
    ema_slow = df_calc[col_slow].astype(float)

    regime = (close_series > ema_fast) & (close_series > ema_slow)
    regime = regime.fillna(False).astype(bool)

    if "date" in df_calc.columns:
        regime.index = pd.Index(df_calc["date"].astype(str))
    else:
        regime.index = df_calc.index

    regime.name = "regime_ok"
    return regime


def trend_ok(stock_df: pd.DataFrame, config: StrategyConfig | None = None) -> pd.Series:
    """Evaluates stock trend filter (REQ-3.2).

    Rule:
        EMA 20 > EMA 50 > EMA 150 > EMA 200

    Signal is valid only if all four EMAs are strictly stacked in ascending order.

    Args:
        stock_df: DataFrame containing equity OHLCV or indicator-augmented price series.
        config: Strategy configuration containing trend EMA spans.

    Returns:
        pd.Series[bool] indexed by date, representing trend status on each session.
        Never mutates the input DataFrame.
    """
    if stock_df.empty:
        return pd.Series(dtype=bool, name="trend_ok")

    cfg = config or StrategyConfig()
    spans = cfg.ema_trend_spans
    required_cols = [f"ema_{s}" for s in spans]

    # Do not mutate input dataframe
    if any(c not in stock_df.columns for c in required_cols):
        ind_cfg = IndicatorConfig(spans=spans, include_high_52w=False)
        df_calc = compute_indicators(stock_df, config=ind_cfg)
    else:
        df_calc = stock_df

    ema_20 = df_calc["ema_20"].astype(float)
    ema_50 = df_calc["ema_50"].astype(float)
    ema_150 = df_calc["ema_150"].astype(float)
    ema_200 = df_calc["ema_200"].astype(float)

    trend = (ema_20 > ema_50) & (ema_50 > ema_150) & (ema_150 > ema_200)
    trend = trend.fillna(False).astype(bool)

    if "date" in df_calc.columns:
        trend.index = pd.Index(df_calc["date"].astype(str))
    else:
        trend.index = df_calc.index

    trend.name = "trend_ok"
    return trend


def near_52w_high(
    stock_df: pd.DataFrame,
    factor: float = 0.85,
    config: StrategyConfig | None = None,
) -> pd.Series:
    """Evaluates price action proximity filter to 52-week high (REQ-3.3).

    Rule:
        Close > factor * 52W High

    Default factor is 0.85 (stock price must be within 15% of its 52-week high).
    Signal is invalid if price is > 15% away from its 52W rolling maximum.

    Args:
        stock_df: DataFrame containing equity OHLCV or indicator-augmented price series.
        factor: Proximity factor threshold. Defaults to 0.85.
        config: Strategy configuration containing high_52w_factor and lookback.

    Returns:
        pd.Series[bool] indexed by date, representing proximity status on each session.
        Never mutates the input DataFrame.
    """
    if stock_df.empty:
        return pd.Series(dtype=bool, name="near_52w_high")

    cfg = config or StrategyConfig()
    eff_factor = factor if factor != 0.85 or config is None else cfg.high_52w_factor

    # Do not mutate input dataframe
    if "high_52w" not in stock_df.columns:
        ind_cfg = IndicatorConfig(
            spans=[],
            include_high_52w=True,
            high_52w_lookback=cfg.high_52w_lookback,
        )
        df_calc = compute_indicators(stock_df, config=ind_cfg)
    else:
        df_calc = stock_df

    # Extract adjusted close price (or close)
    if "adj_close" in df_calc.columns:
        close_series = df_calc["adj_close"].astype(float)
    elif "close" in df_calc.columns:
        close_series = df_calc["close"].astype(float)
    else:
        raise ValueError("stock_df must contain 'adj_close' or 'close' column")

    high_52w_series = df_calc["high_52w"].astype(float)

    is_near = close_series > (eff_factor * high_52w_series)
    is_near = is_near.fillna(False).astype(bool)

    if "date" in df_calc.columns:
        is_near.index = pd.Index(df_calc["date"].astype(str))
    else:
        is_near.index = df_calc.index

    is_near.name = "near_52w_high"
    return is_near
