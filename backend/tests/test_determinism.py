"""Determinism and property tests for simulation engine (REQ-6.3)."""

from pathlib import Path

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.backtest import Backtest
from app.strategy.config import StrategyConfig


def _load_tiny_universe():
    base = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "tiny_universe"
    prices = {
        "ALPHA": pd.read_parquet(base / "ALPHA.parquet"),
        "BETA": pd.read_parquet(base / "BETA.parquet"),
        "GAMMA": pd.read_parquet(base / "GAMMA.parquet"),
    }
    nifty = pd.read_parquet(base / "NIFTY_TINY.parquet")
    return prices, nifty


def test_exact_determinism_identical_runs():
    """Validates running simulation twice with identical configs is deterministic."""
    prices, nifty = _load_tiny_universe()
    config = StrategyConfig(
        capital=500000.0,
        sl_pct=0.07,
        risk_pct=0.02,
        cost_bps=10.0,
        ranking_rule="momentum",
    )

    bt1 = Backtest(config=config, prices=prices, nifty=nifty)
    res1 = bt1.run(start="2020-06-01", end="2022-04-29")

    bt2 = Backtest(config=config, prices=prices, nifty=nifty)
    res2 = bt2.run(start="2020-06-01", end="2022-04-29")

    assert res1.final_capital == res2.final_capital
    assert res1.total_return == res2.total_return
    assert res1.total_return_pct == res2.total_return_pct
    assert res1.cagr == res2.cagr
    assert res1.total_trades == res2.total_trades
    assert res1.win_rate == res2.win_rate
    assert res1.max_drawdown == res2.max_drawdown
    assert res1.max_drawdown_pct == res2.max_drawdown_pct

    # Compare trade ledgers
    pd.testing.assert_frame_equal(res1.trades, res2.trades)

    # Compare equity curves
    pd.testing.assert_frame_equal(res1.equity_curve, res2.equity_curve)


@settings(max_examples=5, deadline=None)
@given(
    sl_pct=st.sampled_from([0.05, 0.07, 0.09]),
    risk_pct=st.sampled_from([0.01, 0.02, 0.03]),
    cost_bps=st.sampled_from([5.0, 10.0, 15.0]),
    ranking_rule=st.sampled_from(["momentum", "alphabetical", "52w_proximity"]),
)
def test_hypothesis_determinism_across_parameter_space(
    sl_pct, risk_pct, cost_bps, ranking_rule
):
    """Property test: arbitrary parameter combinations run deterministically."""
    prices, nifty = _load_tiny_universe()
    config = StrategyConfig(
        capital=500000.0,
        sl_pct=sl_pct,
        risk_pct=risk_pct,
        cost_bps=cost_bps,
        ranking_rule=ranking_rule,
    )

    bt_a = Backtest(config=config, prices=prices, nifty=nifty)
    res_a = bt_a.run(start="2020-06-01", end="2022-04-29")

    bt_b = Backtest(config=config, prices=prices, nifty=nifty)
    res_b = bt_b.run(start="2020-06-01", end="2022-04-29")

    assert res_a.final_capital == res_b.final_capital
    assert res_a.total_trades == res_b.total_trades
    assert res_a.win_rate == res_b.win_rate
    assert res_a.total_return_pct == res_b.total_return_pct
    pd.testing.assert_frame_equal(res_a.trades, res_b.trades)
    pd.testing.assert_frame_equal(res_a.equity_curve, res_b.equity_curve)
