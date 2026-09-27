"""Unit tests for Order Execution Engine and Simulation Periods (REQ-5.2)."""

from pathlib import Path

import pandas as pd
import pytest

from app.engine.backtest import Backtest
from app.engine.result import BacktestResult
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


def test_backtest_date_truncation_warning_and_cagr_10y(tiny_universe_data):
    """Requesting 10y horizon earlier than coverage generates warnings and CAGR."""
    prices, nifty = tiny_universe_data
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result = engine.run(start="2014-01-01", end="2024-01-01")

    # Verify warnings are present
    assert len(result.warnings) >= 1
    assert any("earlier than earliest available data" in w for w in result.warnings)
    assert any("annualized over full requested period" in w for w in result.warnings)

    # Verify CAGR uses 10-year horizon (~10 years), not 500-day 2-year horizon (-0.0183)
    assert result.cagr != -0.0183
    assert result.cagr == pytest.approx(-0.0037, abs=0.0005)
    assert result.summary()["warnings"] == result.warnings


def test_backtest_date_truncation_warning_and_cagr_15y(tiny_universe_data):
    """Requesting 15y horizon earlier than coverage differentiates CAGR from 10y."""
    prices, nifty = tiny_universe_data
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result_15y = engine.run(start="2009-01-01", end="2024-01-01")
    result_10y = engine.run(start="2014-01-01", end="2024-01-01")

    assert len(result_15y.warnings) >= 1
    # 15y CAGR must be distinct from 10y CAGR and distinct from 2y unadjusted CAGR
    assert result_15y.cagr != result_10y.cagr
    assert result_15y.cagr != -0.0183
    assert result_15y.cagr == pytest.approx(-0.0024, abs=0.0005)


def test_backtest_no_truncation_warning_within_coverage(tiny_universe_data):
    """Running within coverage produces no truncation warnings."""
    prices, nifty = tiny_universe_data
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result = engine.run(start="2020-06-01", end="2021-12-31")

    assert result.warnings == []
    assert result.summary()["warnings"] == []


def test_backtest_result_warnings_serialization(tmp_path, tiny_universe_data):
    """BacktestResult preserves warnings across JSON save and load cycle."""
    prices, nifty = tiny_universe_data
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result = engine.run(start="2014-01-01", end="2024-01-01")
    assert len(result.warnings) > 0

    save_path = tmp_path / "result_with_warnings.json"
    result.save(save_path)

    loaded = BacktestResult.load(save_path)
    assert loaded.warnings == result.warnings
    assert loaded.cagr == result.cagr
    assert loaded.summary()["warnings"] == result.warnings


def test_backtest_honours_nifty_regime_ema200_filter(tiny_universe_data):
    """Backtest engine honours REQ-3.1: zero new trades if NIFTY is below 200 EMA."""
    prices, nifty = tiny_universe_data

    # Artificially depress NIFTY close below 200 EMA across the entire series
    nifty_bear = nifty.copy()
    nifty_bear["close"] = 1.0
    if "adj_close" in nifty_bear.columns:
        nifty_bear["adj_close"] = 1.0

    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty_bear)
    result = engine.run()

    # Zero trades and zero open positions must be executed
    assert len(result.trades) == 0
    assert result.total_trades == 0
    assert len(result.open_positions) == 0
    # Final capital must remain untouched
    assert result.final_capital == 500000.0
