"""Unit tests and empyrical cross-validation for Performance Metrics.

Covers REQ-7.1.
"""

from decimal import Decimal
from pathlib import Path

import empyrical
import numpy as np
import pandas as pd
import pytest

from app.engine.backtest import Backtest
from app.reports.metrics import calculate_metrics
from app.strategy.config import StrategyConfig

TINY_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "fixtures"
    / "tiny_universe"
)


@pytest.fixture
def tiny_universe_backtest_result():
    """Executes deterministic backtest on Phase-5 tiny_universe golden fixtures."""
    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")
    prices = {
        "ALPHA": pd.read_parquet(TINY_DIR / "ALPHA.parquet"),
        "BETA": pd.read_parquet(TINY_DIR / "BETA.parquet"),
        "GAMMA": pd.read_parquet(TINY_DIR / "GAMMA.parquet"),
    }
    engine = Backtest(config=StrategyConfig(), prices=prices, nifty=nifty)
    return engine.run()


def test_golden_metrics_on_phase5_fixture(tiny_universe_backtest_result):
    """Asserts exact PRD metrics on Phase-5 fixture run with documented precision."""
    res = tiny_universe_backtest_result
    metrics = calculate_metrics(
        trades=res.trades,
        equity_curve=res.equity_curve,
        initial_capital=res.initial_capital,
    )

    # Core Metrics Assertions
    assert metrics.total_trades == 2
    assert metrics.win_trades == 0
    assert metrics.loss_trades == 2
    assert round(metrics.win_rate, 4) == 0.0000
    assert round(metrics.avg_profit, 4) == 0.0000
    assert round(metrics.avg_loss, 4) == -8646.4000
    assert round(metrics.final_capital, 2) == 482707.20
    assert round(metrics.net_profit, 2) == -17292.80
    assert round(metrics.total_return_pct, 4) == -0.0346

    # Advanced Metrics Assertions
    assert round(metrics.cagr, 4) == -0.0183
    assert round(metrics.max_drawdown_amount, 2) == 19208.32
    assert round(metrics.max_drawdown_pct, 4) == 0.0383
    assert round(metrics.profit_factor, 4) == 0.0000
    assert round(metrics.expectancy, 2) == -8646.40
    assert round(metrics.avg_days_held, 1) == 68.0


def test_cross_check_against_empyrical(tiny_universe_backtest_result):
    """Cross-validates Sharpe, Sortino, and MaxDD against empyrical within 1e-6."""
    res = tiny_universe_backtest_result
    returns = res.equity_curve["equity"].pct_change().fillna(0.0)

    # 1. empyrical calculations
    emp_sharpe = float(empyrical.sharpe_ratio(returns, risk_free=0.0, period="daily"))
    emp_sortino = float(
        empyrical.sortino_ratio(returns, required_return=0.0, period="daily")
    )
    emp_mdd = float(empyrical.max_drawdown(returns))

    # 2. calculate_metrics calculations
    metrics = calculate_metrics(
        trades=res.trades,
        equity_curve=res.equity_curve,
        initial_capital=res.initial_capital,
    )

    # 3. Assert precision within 1e-6 (using unrounded formulas from returns)
    mu = returns.mean()
    std = returns.std(ddof=1)
    unrounded_sharpe = (mu / std) * np.sqrt(252.0)
    assert abs(unrounded_sharpe - emp_sharpe) < 1e-6
    assert abs(metrics.sharpe_ratio - round(emp_sharpe, 4)) <= 0.0001

    downside = np.clip(returns, -np.inf, 0.0)
    downside_dev = np.sqrt(np.mean(downside**2))
    unrounded_sortino = (mu / downside_dev) * np.sqrt(252.0)
    assert abs(unrounded_sortino - emp_sortino) < 1e-6
    assert abs(metrics.sortino_ratio - round(emp_sortino, 4)) <= 0.0001

    peak = res.equity_curve["equity"].cummax()
    unrounded_mdd = float(((res.equity_curve["equity"] - peak) / peak).min())
    assert abs(unrounded_mdd - emp_mdd) < 1e-6
    assert abs(metrics.max_drawdown_pct - round(abs(emp_mdd), 4)) <= 0.0001


def test_metrics_all_winners_scenario():
    """Asserts metrics computation when all trades are profitable."""
    trades = pd.DataFrame(
        [
            {"symbol": "AAA", "pnl": 10000.0, "days_held": 20},
            {"symbol": "BBB", "pnl": 20000.0, "days_held": 30},
        ]
    )
    equity_curve = pd.DataFrame(
        [
            {"date": "2023-01-01", "equity": 500000.0},
            {"date": "2023-02-01", "equity": 510000.0},
            {"date": "2023-03-01", "equity": 530000.0},
        ]
    )
    metrics = calculate_metrics(trades, equity_curve, initial_capital=500000.0)

    assert metrics.total_trades == 2
    assert metrics.win_trades == 2
    assert metrics.loss_trades == 0
    assert metrics.win_rate == 1.0
    assert metrics.avg_profit == 15000.0
    assert metrics.avg_loss == 0.0
    assert metrics.final_capital == 530000.0
    assert metrics.net_profit == 30000.0
    assert metrics.total_return_pct == 0.06
    assert metrics.profit_factor == float("inf")
    assert metrics.expectancy == 15000.0
    assert metrics.avg_days_held == 25.0


def test_metrics_empty_inputs_graceful():
    """Asserts metrics computation handles empty trades and equity curves gracefully."""
    empty_trades = pd.DataFrame()
    empty_equity = pd.DataFrame()

    metrics = calculate_metrics(empty_trades, empty_equity, initial_capital=100000.0)
    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.final_capital == 100000.0
    assert metrics.net_profit == 0.0
    assert metrics.sharpe_ratio == 0.0
    assert metrics.sortino_ratio == 0.0
    assert metrics.calmar_ratio == 0.0


def test_metrics_decimal_serialization():
    """Asserts to_decimal_dict converts all metrics into Decimal types."""
    trades = pd.DataFrame(
        [
            {"symbol": "XYZ", "pnl": -5000.0, "days_held": 15},
        ]
    )
    equity_curve = pd.DataFrame(
        [
            {"date": "2023-01-01", "equity": 500000.0},
            {"date": "2023-01-15", "equity": 495000.0},
        ]
    )
    metrics = calculate_metrics(trades, equity_curve, initial_capital=500000.0)
    dec_dict = metrics.to_decimal_dict()

    assert isinstance(dec_dict["total_trades"], Decimal)
    assert isinstance(dec_dict["win_rate"], Decimal)
    assert isinstance(dec_dict["avg_loss"], Decimal)
    assert isinstance(dec_dict["sharpe_ratio"], Decimal)
    assert dec_dict["final_capital"] == Decimal("495000.00")
