"""TradingView cross-check validation and visual diff engine (REQ-8.1)."""

import io
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlmodel import Session

from app.data.source import get_price_source
from app.db.models import BacktestRun
from app.strategy.config import StrategyConfig
from app.strategy.signals import generate_signals

logger = logging.getLogger(__name__)

CROSS_CHECK_COLUMNS = [
    "date",
    "close",
    "ema_20",
    "ema_50",
    "ema_150",
    "ema_200",
    "high_52w",
    "entry",
    "exit",
]


def generate_cross_check_dataframe(
    run_id: str,
    symbol: str,
    session: Session | None = None,
    filter_dates: bool = True,
) -> tuple[pd.DataFrame, str]:
    """Generates aligned indicator and signal series for manual visual diffing.

    Output columns: (date, close, ema_20, ema_50, ema_150, ema_200, high_52w, entry, exit).

    Args:
        run_id: Backtest run identifier (or 'default' to evaluate on baseline strategy config).
        symbol: Equity ticker symbol (e.g. 'RELIANCE', 'ALPHA').
        session: Optional active database session to retrieve run record.
        filter_dates: If True and the run specified start/end dates, filters output to that range.

    Returns:
        Tuple of (DataFrame with exact CROSS_CHECK_COLUMNS, CSV formatted string).

    Raises:
        ValueError: If run_id is not found or symbol price data is unavailable.
    """
    strat_config = StrategyConfig()
    start_date: str | None = None
    end_date: str | None = None

    if run_id and run_id != "default":
        if session is not None:
            run_record = session.get(BacktestRun, run_id)
        else:
            from app.db.session import engine

            with Session(engine) as s:
                run_record = s.get(BacktestRun, run_id)

        if not run_record:
            raise ValueError(f"Backtest run '{run_id}' not found")

        if run_record.config_json:
            try:
                cfg_dict = json.loads(run_record.config_json)
                strat_config = StrategyConfig(**cfg_dict)
            except Exception as e:
                logger.warning("Failed parsing config for run %s: %s", run_id, e)

        start_date = run_record.start_date
        end_date = run_record.end_date

    # 1. Load equity prices
    price_source = get_price_source()
    repo_root = Path(__file__).resolve().parents[3]


    stock_df = price_source.get_equity_prices(symbol, start="2000-01-01", end="2099-12-31")

    # If empty via source, check local fixture fallback
    if stock_df.empty:
        symbol_upper = symbol.upper()
        candidates = [
            repo_root / "data" / "fixtures" / f"{symbol_upper}.parquet",
            repo_root / "data" / "fixtures" / "tiny_universe" / f"{symbol_upper}.parquet",
            repo_root / "data" / "fixtures" / f"{symbol_upper.lower()}_2020_2023.parquet",
        ]
        for c in candidates:
            if c.exists():
                stock_df = pd.read_parquet(c)
                break

    if stock_df.empty:
        raise ValueError(f"No price data found for symbol '{symbol}'")

    # 2. Load benchmark prices
    is_tiny = symbol in ("ALPHA", "BETA", "GAMMA")
    nifty_df = pd.DataFrame()
    if is_tiny:
        tiny_nifty = repo_root / "data" / "fixtures" / "tiny_universe" / "NIFTY_TINY.parquet"
        if tiny_nifty.exists():
            nifty_df = pd.read_parquet(tiny_nifty)

    if nifty_df.empty:
        nifty_df = price_source.get_index_prices("^NSEI", start="2000-01-01", end="2099-12-31")

    if nifty_df.empty:
        nifty_fixture = repo_root / "data" / "fixtures" / "NIFTY50.parquet"
        if nifty_fixture.exists():
            nifty_df = pd.read_parquet(nifty_fixture)

    # 3. Compute indicators and signals
    signals_df = generate_signals(stock_df=stock_df, nifty_df=nifty_df, config=strat_config)

    # Ensure required columns exist
    if "date" not in signals_df.columns:
        signals_df["date"] = signals_df.index.astype(str)

    signals_df["date"] = signals_df["date"].astype(str)

    # Use adjusted close for price consistency if available
    price_col = "adj_close" if "adj_close" in signals_df.columns else "close"
    signals_df["close"] = signals_df[price_col].astype(float)

    # Map signals entry and exit booleans
    signals_df["entry"] = signals_df["entry"].fillna(False).astype(bool)
    signals_df["exit"] = signals_df["exit"].fillna(False).astype(bool)

    # 4. Optional date range filtering
    if filter_dates and (start_date or end_date):
        mask = pd.Series(True, index=signals_df.index)
        if start_date:
            mask &= signals_df["date"] >= start_date
        if end_date:
            mask &= signals_df["date"] <= end_date
        signals_df = signals_df[mask]

    # Select and order exact columns
    result_df = signals_df[CROSS_CHECK_COLUMNS].copy()
    result_df = result_df.sort_values("date").reset_index(drop=True)

    csv_buf = io.StringIO()
    result_df.to_csv(csv_buf, index=False)
    csv_str = csv_buf.getvalue()

    return result_df, csv_str
