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


def exit_signal(
    stock_df: pd.DataFrame, config: StrategyConfig | None = None
) -> pd.Series:
    """Evaluates strategy exit signal on bar T (REQ-3.5).

    Rule:
        Close(T) < EMA20(T)

    Execution takes place on session T+1 at the Open price.

    Args:
        stock_df: DataFrame containing equity OHLCV or indicator-augmented price series.
        config: Strategy configuration containing short EMA span (default 20).

    Returns:
        pd.Series[bool] indexed by date, aligned to stock_df.
        Never mutates input DataFrame.
    """
    if stock_df.empty:
        return pd.Series(dtype=bool, name="exit")

    cfg = config or StrategyConfig()
    short_col = f"ema_{cfg.ema_short}"

    if short_col not in stock_df.columns:
        ind_cfg = IndicatorConfig(spans=[cfg.ema_short], include_high_52w=False)
        df_calc = compute_indicators(stock_df, config=ind_cfg)
    else:
        df_calc = stock_df

    if "adj_close" in df_calc.columns:
        close_series = df_calc["adj_close"].astype(float)
    elif "close" in df_calc.columns:
        close_series = df_calc["close"].astype(float)
    else:
        raise ValueError("stock_df must contain 'adj_close' or 'close' column")

    ema_series = df_calc[short_col].astype(float)

    exit_sig = close_series < ema_series
    exit_sig = exit_sig.fillna(False).astype(bool)

    if "date" in df_calc.columns:
        exit_sig.index = pd.Index(df_calc["date"].astype(str))
    else:
        exit_sig.index = df_calc.index

    exit_sig.name = "exit"
    return exit_sig


def entry_signal(
    stock_df: pd.DataFrame,
    nifty_df: pd.DataFrame,
    config: StrategyConfig | None = None,
) -> pd.Series:
    """Evaluates strategy entry signal on bar T (REQ-3.4).

    Rules:
        (regime_ok & trend_ok & near_52w_high) on T
        AND (Close_T > EMA20_T) AND (Close_{T-1} < EMA20_{T-1})

    Execution takes place on session T+1 at the Open price.

    Args:
        stock_df: DataFrame containing equity OHLCV or indicator-augmented price series.
        nifty_df: DataFrame containing NIFTY benchmark OHLCV or indicator series.
        config: Strategy configuration.

    Returns:
        pd.Series[bool] indexed by date, aligned to stock_df.
        Never mutates input DataFrames.
    """
    if stock_df.empty:
        return pd.Series(dtype=bool, name="entry")

    cfg = config or StrategyConfig()

    # Determine date index for stock_df
    if "date" in stock_df.columns:
        stock_dates = pd.Index(stock_df["date"].astype(str))
    else:
        stock_dates = stock_df.index

    # 1. Market regime filter (indexed by nifty dates)
    regime = market_regime_ok(nifty_df, config=cfg)
    aligned_regime = (
        regime.reindex(stock_dates, fill_value=False).fillna(False).astype(bool)
    )
    aligned_regime.index = stock_dates

    # 2. Trend filter
    trend = trend_ok(stock_df, config=cfg)
    trend.index = stock_dates

    # 3. Near 52W high filter
    near_high = near_52w_high(stock_df, factor=cfg.high_52w_factor, config=cfg)
    near_high.index = stock_dates

    # 4. EMA20 crossover
    short_col = f"ema_{cfg.ema_short}"
    if short_col not in stock_df.columns:
        ind_cfg = IndicatorConfig(spans=[cfg.ema_short], include_high_52w=False)
        df_calc = compute_indicators(stock_df, config=ind_cfg)
    else:
        df_calc = stock_df

    if "adj_close" in df_calc.columns:
        close_series = df_calc["adj_close"].astype(float)
    elif "close" in df_calc.columns:
        close_series = df_calc["close"].astype(float)
    else:
        raise ValueError("stock_df must contain 'adj_close' or 'close' column")

    ema_series = df_calc[short_col].astype(float)

    close_curr = close_series
    ema_curr = ema_series
    close_prev = close_series.shift(1)
    ema_prev = ema_series.shift(1)

    if cfg.allow_crossover_equal:
        crossover = (close_curr > ema_curr) & (close_prev <= ema_prev)
    else:
        crossover = (close_curr > ema_curr) & (close_prev < ema_prev)

    crossover = crossover.fillna(False).astype(bool)
    crossover.index = stock_dates

    # All conditions combined
    entry = aligned_regime & trend & near_high & crossover
    entry.name = "entry"
    return entry


def generate_signals(
    stock_df: pd.DataFrame,
    nifty_df: pd.DataFrame,
    config: StrategyConfig | None = None,
) -> pd.DataFrame:
    """Computes all technical indicators, filters, and strategy signals.

    Augments the stock OHLCV DataFrame with:
    - Indicators: ema_20, ema_50, ema_150, ema_200, high_52w
    - Component filters: regime_ok, trend_ok, near_52w_high, crossover
    - Final signals: entry, exit

    Args:
        stock_df: DataFrame containing equity OHLCV prices.
        nifty_df: DataFrame containing NIFTY benchmark OHLCV prices.
        config: Strategy configuration parameters.

    Returns:
        DataFrame augmented with all indicator and signal columns.
        Never mutates input DataFrames.
    """
    if stock_df.empty:
        return stock_df.copy()

    cfg = config or StrategyConfig()

    # Compute indicators if not already present
    required_cols = [f"ema_{s}" for s in cfg.ema_trend_spans] + ["high_52w"]
    if any(c not in stock_df.columns for c in required_cols):
        ind_cfg = IndicatorConfig(
            spans=cfg.ema_trend_spans,
            include_high_52w=True,
            high_52w_lookback=cfg.high_52w_lookback,
        )
        augmented = compute_indicators(stock_df, config=ind_cfg)
    else:
        augmented = stock_df.copy()

    # Date indexing
    if "date" in augmented.columns:
        dates = pd.Index(augmented["date"].astype(str))
    else:
        dates = augmented.index

    # Filters
    regime = market_regime_ok(nifty_df, config=cfg)
    aligned_regime = regime.reindex(dates, fill_value=False).fillna(False).astype(bool)
    aligned_regime.index = dates

    trend = trend_ok(augmented, config=cfg)
    trend.index = dates

    near_high = near_52w_high(augmented, factor=cfg.high_52w_factor, config=cfg)
    near_high.index = dates

    # Crossover
    short_col = f"ema_{cfg.ema_short}"
    close_series = (
        augmented["adj_close"].astype(float)
        if "adj_close" in augmented.columns
        else augmented["close"].astype(float)
    )
    ema_series = augmented[short_col].astype(float)

    close_curr = close_series
    ema_curr = ema_series
    close_prev = close_series.shift(1)
    ema_prev = ema_series.shift(1)

    if cfg.allow_crossover_equal:
        crossover = (close_curr > ema_curr) & (close_prev <= ema_prev)
    else:
        crossover = (close_curr > ema_curr) & (close_prev < ema_prev)

    crossover = crossover.fillna(False).astype(bool)
    crossover.index = dates

    entry = (aligned_regime & trend & near_high & crossover).astype(bool)
    entry.index = dates

    exit_sig = (close_curr < ema_curr).fillna(False).astype(bool)
    exit_sig.index = dates

    # Append columns
    out_df = augmented.copy()
    out_df["regime_ok"] = aligned_regime.values
    out_df["trend_ok"] = trend.values
    out_df["near_52w_high"] = near_high.values
    out_df["crossover"] = crossover.values
    out_df["entry"] = entry.values
    out_df["exit"] = exit_sig.values

    return out_df
