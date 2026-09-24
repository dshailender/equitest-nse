"""Unit tests for Core Backtest Simulation Engine (REQ-5.1)."""

from pathlib import Path

import pandas as pd
import pytest

from app.engine.backtest import Backtest
from app.engine.result import BacktestResult
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


def test_deterministic_tiny_universe_golden_backtest(tiny_universe_data):
    """Asserts deterministic execution on tiny_universe against golden metrics."""
    prices, nifty = tiny_universe_data
    config = StrategyConfig()
    engine = Backtest(config=config, prices=prices, nifty=nifty)
    result = engine.run()

    # 1. Total trades verification
    assert len(result.trades) == 2
    assert result.total_trades == 2
    assert result.win_trades == 0
    assert result.loss_trades == 2
    assert result.win_rate == 0.0

    # 2. Trade 1: Gap-down overnight stop loss execution
    t1 = result.trades.iloc[0]
    assert t1["symbol"] == "ALPHA"
    assert t1["entry_date"] == "2021-05-25"
    assert round(float(t1["entry_price"]), 2) == 217.83
    assert int(t1["qty"]) == 656
    assert t1["exit_date"] == "2021-08-10"
    assert round(float(t1["exit_price"]), 2) == 194.42
    assert t1["exit_reason"] == "gap"
    assert round(float(t1["pnl"]), 2) == -15356.96
    assert round(float(t1["pnl_pct"]), 4) == -0.1075
    assert int(t1["days_held"]) == 55
    assert round(float(t1["costs"]), 2) == 268.96

    # 3. Trade 2: Technical exit signal execution (Close < EMA20)
    t2 = result.trades.iloc[1]
    assert t2["symbol"] == "ALPHA"
    assert t2["entry_date"] == "2021-11-02"
    assert round(float(t2["entry_price"]), 2) == 211.83
    assert int(t2["qty"]) == 654
    assert t2["exit_date"] == "2022-02-23"
    assert round(float(t2["exit_price"]), 2) == 208.87
    assert t2["exit_reason"] == "exit_signal"
    assert round(float(t2["pnl"]), 2) == -1935.84
    assert round(float(t2["pnl_pct"]), 4) == -0.0140
    assert int(t2["days_held"]) == 81
    assert round(float(t2["costs"]), 2) == 274.68

    # 4. Final capital to the paisa (round 2 decimals)
    assert result.final_capital == 482707.20
    assert result.total_return == -17292.80
    assert result.total_return_pct == -0.0346

    # 5. Equity curve integrity
    assert len(result.equity_curve) == 500
    assert result.equity_curve["equity"].iloc[0] == 500000.0
    assert result.equity_curve["equity"].iloc[-1] == 482707.20
    assert result.equity_curve["cash"].iloc[-1] == 482707.20
    assert result.equity_curve["open_positions"].iloc[-1] == 0


def test_backtest_idempotency(tiny_universe_data):
    """Running identical backtests produces identical trade logs and equity curves."""
    prices, nifty = tiny_universe_data

    engine1 = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result1 = engine1.run()

    engine2 = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result2 = engine2.run()

    pd.testing.assert_frame_equal(result1.trades, result2.trades)
    pd.testing.assert_frame_equal(result1.equity_curve, result2.equity_curve)
    assert result1.final_capital == result2.final_capital
    assert result1.total_return == result2.total_return
    assert result1.summary() == result2.summary()


def test_backtest_result_serialization(tmp_path, tiny_universe_data):
    """BacktestResult serializes to JSON and reloads perfectly from disk."""
    prices, nifty = tiny_universe_data
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    result = engine.run()

    save_path = tmp_path / "test_run.json"
    result.save(save_path)
    assert save_path.exists()

    loaded = BacktestResult.load(save_path)
    assert loaded.final_capital == result.final_capital
    assert loaded.total_trades == result.total_trades
    assert loaded.win_rate == result.win_rate
    assert len(loaded.trades) == len(result.trades)
    assert len(loaded.equity_curve) == len(result.equity_curve)
    pd.testing.assert_frame_equal(result.trades, loaded.trades)
