"""Unit tests for Order Execution Engine and Simulation Periods (REQ-5.2)."""

from pathlib import Path

import pandas as pd
import pytest

from app.engine.backtest import Backtest
from app.risk.slippage import apply_costs
from app.strategy.config import StrategyConfig

TINY_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "fixtures"
    / "tiny_universe"
)


@pytest.fixture
def tiny_universe_data():
    """Loads parquet files from /data/fixtures/tiny_universe/."""
    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")
    prices = {
        "ALPHA": pd.read_parquet(TINY_DIR / "ALPHA.parquet"),
        "BETA": pd.read_parquet(TINY_DIR / "BETA.parquet"),
        "GAMMA": pd.read_parquet(TINY_DIR / "GAMMA.parquet"),
    }
    return prices, nifty


def test_simulation_period_start_filter(tiny_universe_data):
    """Setting start date filters prior trades while honoring warm-up indicators."""
    prices, nifty = tiny_universe_data
    # Trade 1 occurred on 2021-05-25. Setting start after Trade 1 excludes it.
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result = engine.run(start="2021-09-01", end="2022-04-29")

    # Only Trade 2 (2021-11-02 to 2022-02-23) should execute
    assert len(result.trades) == 1
    trade = result.trades.iloc[0]
    assert trade["entry_date"] == "2021-11-02"
    assert trade["exit_date"] == "2022-02-23"
    assert result.equity_curve["date"].min() == "2021-09-01"
    assert result.equity_curve["date"].max() == "2022-04-29"


def test_simulation_period_end_filter(tiny_universe_data):
    """Setting end date stops simulation and excludes subsequent entry signals."""
    prices, nifty = tiny_universe_data
    # Trade 1 exits on 2021-08-10. Trade 2 enters on 2021-11-02.
    # Setting end to 2021-09-01 captures only Trade 1.
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result = engine.run(start="2020-06-01", end="2021-09-01")

    assert len(result.trades) == 1
    trade = result.trades.iloc[0]
    assert trade["entry_date"] == "2021-05-25"
    assert trade["exit_date"] == "2021-08-10"
    assert result.equity_curve["date"].max() == "2021-09-01"


def test_no_lookahead_at_engine_level(tiny_universe_data):
    """Truncating price DataFrame at date D guarantees all entries <= D."""
    cutoff_date = "2021-07-01"
    raw_prices, raw_nifty = tiny_universe_data

    truncated_prices = {
        sym: df[df["date"] <= cutoff_date].copy() for sym, df in raw_prices.items()
    }
    truncated_nifty = raw_nifty[raw_nifty["date"] <= cutoff_date].copy()

    engine = Backtest(
        config=StrategyConfig(),
        prices=truncated_prices,
        nifty=truncated_nifty,
    )
    result = engine.run()

    # All closed trade entries must be <= cutoff_date
    for _, t in result.trades.iterrows():
        assert t["entry_date"] <= cutoff_date

    # All open position entries must also be <= cutoff_date
    for pos in result.open_positions:
        assert pos["entry_date"] <= cutoff_date

    # Trade 1 entered on 2021-05-25 <= 2021-07-01, but exit was 2021-08-10 > cutoff
    # Therefore, Trade 1 should be currently OPEN at the cutoff
    assert len(result.open_positions) == 1

    open_trade = result.open_positions[0]
    assert open_trade["symbol"] == "ALPHA"
    assert open_trade["entry_date"] == "2021-05-25"
    assert open_trade["entry_date"] <= cutoff_date


def test_order_execution_strictly_at_market_open_with_costs(tiny_universe_data):
    """Executions strictly execute on session T open price with configured slippage."""
    prices, nifty = tiny_universe_data
    cost_bps = 10.0
    config = StrategyConfig(cost_bps=cost_bps)
    engine = Backtest(config=config, prices=prices, nifty=nifty)
    result = engine.run()

    # Verify Trade 1 execution
    alpha_df = prices["ALPHA"]
    entry_row = alpha_df[alpha_df["date"] == "2021-05-25"].iloc[0]
    expected_entry = apply_costs(float(entry_row["open"]), "buy", cost_bps)

    t1 = result.trades.iloc[0]
    assert t1["entry_price"] == expected_entry
    # Never equal to close or high
    assert t1["entry_price"] != entry_row["close"]
    assert t1["entry_price"] != entry_row["high"]

    # Verify Trade 2 exit execution
    exit_row = alpha_df[alpha_df["date"] == "2022-02-23"].iloc[0]
    expected_exit = apply_costs(float(exit_row["open"]), "sell", cost_bps)

    t2 = result.trades.iloc[1]
    assert t2["exit_price"] == expected_exit
    assert t2["exit_price"] != exit_row["close"]
