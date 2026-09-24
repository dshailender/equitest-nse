import pandas as pd

from app.indicators.pipeline import compute_nifty_indicators
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
