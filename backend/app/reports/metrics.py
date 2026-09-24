"""Performance metrics computation engine for EquiTest NSE (REQ-7.1)."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """Container holding core and advanced quantitative strategy performance metrics."""

    # Core Metrics (PRD §7.1)
    total_trades: int = Field(..., description="Total completed round-trip trades")
    win_trades: int = Field(..., description="Number of profitable trades (PnL > 0)")
    loss_trades: int = Field(..., description="Number of losing or scratch trades (PnL <= 0)")
    win_rate: float = Field(..., description="Fraction of winning trades (0.0 to 1.0, 4 decimal places)")
    avg_profit: float = Field(..., description="Average profit of winning trades in INR (2 decimal places)")
    avg_loss: float = Field(..., description="Average loss of losing trades in INR (2 decimal places)")
    total_return_pct: float = Field(..., description="Total percentage return (4 decimal places)")
    initial_capital: float = Field(..., description="Initial starting corpus in INR (2 decimal places)")
    final_capital: float = Field(..., description="Ending portfolio equity in INR (2 decimal places)")
    net_profit: float = Field(..., description="Net portfolio monetary gain/loss in INR (2 decimal places)")

    # Advanced Risk & Return Metrics (PRD §7.2)
    cagr: float = Field(..., description="Compound Annual Growth Rate (4 decimal places)")
    max_drawdown_pct: float = Field(..., description="Maximum peak-to-trough percentage drawdown (4 decimal places)")
    max_drawdown_amount: float = Field(..., description="Maximum peak-to-trough monetary drawdown in INR (2 decimal places)")
    sharpe_ratio: float = Field(..., description="Annualized Sharpe Ratio with rf=0 (4 decimal places)")
    sortino_ratio: float = Field(..., description="Annualized Sortino Ratio with MAR=0 (4 decimal places)")
    calmar_ratio: float = Field(..., description="Calmar Ratio: CAGR / Max Drawdown (4 decimal places)")
    profit_factor: float = Field(..., description="Gross Profits / Gross Losses (4 decimal places)")
    expectancy: float = Field(..., description="Average monetary expectancy per trade in INR (2 decimal places)")
    avg_days_held: float = Field(..., description="Average holding duration in days (1 decimal place)")

    def to_decimal_dict(self) -> dict[str, Decimal]:
        """Returns dictionary of metrics converted to Python Decimal with documented precision."""
        def _to_dec(val: float | int, places: int) -> Decimal:
            d = Decimal(str(val))
            quant = Decimal("10") ** -places
            return d.quantize(quant, rounding=ROUND_HALF_UP)

        return {
            "total_trades": Decimal(self.total_trades),
            "win_trades": Decimal(self.win_trades),
            "loss_trades": Decimal(self.loss_trades),
            "win_rate": _to_dec(self.win_rate, 4),
            "avg_profit": _to_dec(self.avg_profit, 2),
            "avg_loss": _to_dec(self.avg_loss, 2),
            "total_return_pct": _to_dec(self.total_return_pct, 4),
            "initial_capital": _to_dec(self.initial_capital, 2),
            "final_capital": _to_dec(self.final_capital, 2),
            "net_profit": _to_dec(self.net_profit, 2),
            "cagr": _to_dec(self.cagr, 4),
            "max_drawdown_pct": _to_dec(self.max_drawdown_pct, 4),
            "max_drawdown_amount": _to_dec(self.max_drawdown_amount, 2),
            "sharpe_ratio": _to_dec(self.sharpe_ratio, 4),
            "sortino_ratio": _to_dec(self.sortino_ratio, 4),
            "calmar_ratio": _to_dec(self.calmar_ratio, 4),
            "profit_factor": _to_dec(self.profit_factor, 4),
            "expectancy": _to_dec(self.expectancy, 2),
            "avg_days_held": _to_dec(self.avg_days_held, 1),
        }


def calculate_metrics(
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    initial_capital: float = 500000.0,
) -> PerformanceMetrics:
    """Computes comprehensive quantitative performance and risk metrics.

    Args:
        trades: DataFrame of closed round-trip trades with columns:
            'symbol', 'entry_date', 'exit_date', 'pnl', 'pnl_pct', 'days_held', etc.
        equity_curve: DataFrame of daily portfolio equity with columns:
            'date', 'equity', 'cash', 'positions_value', 'daily_return', 'drawdown', 'drawdown_pct'.
        initial_capital: Starting account corpus in INR.

    Returns:
        PerformanceMetrics model with all PRD core and advanced metrics.
    """
    init_cap = round(float(initial_capital), 2)

    # 1. Final capital & net profit
    if not equity_curve.empty and "equity" in equity_curve.columns:
        final_cap = round(float(equity_curve["equity"].iloc[-1]), 2)
    else:
        final_cap = init_cap

    net_profit = round(final_cap - init_cap, 2)
    total_return_pct = (
        round((final_cap - init_cap) / init_cap, 4) if init_cap > 0 else 0.0
    )

    # 2. Trade statistics
    total_trades = len(trades) if not trades.empty else 0
    if total_trades > 0 and "pnl" in trades.columns:
        pnl_series = trades["pnl"].astype(float)
        wins = pnl_series[pnl_series > 0]
        losses = pnl_series[pnl_series <= 0]
        win_trades = int(len(wins))
        loss_trades = int(len(losses))
        win_rate = round(win_trades / total_trades, 4)
        avg_profit = round(float(wins.mean()), 2) if win_trades > 0 else 0.0
        avg_loss = round(float(losses.mean()), 2) if loss_trades > 0 else 0.0

        gross_profit = float(wins.sum()) if win_trades > 0 else 0.0
        gross_loss = abs(float(losses.sum())) if loss_trades > 0 else 0.0
        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 4)
        else:
            profit_factor = 0.0 if gross_profit == 0.0 else float("inf")

        expectancy = round(float(pnl_series.mean()), 2)
        avg_days_held = (
            round(float(trades["days_held"].astype(float).mean()), 1)
            if "days_held" in trades.columns
            else 0.0
        )
    else:
        win_trades = 0
        loss_trades = 0
        win_rate = 0.0
        avg_profit = 0.0
        avg_loss = 0.0
        profit_factor = 0.0
        expectancy = 0.0
        avg_days_held = 0.0

    # 3. CAGR calculation
    cagr = total_return_pct
    if (
        not equity_curve.empty
        and "date" in equity_curve.columns
        and len(equity_curve) >= 2
        and init_cap > 0
        and final_cap > 0
    ):
        try:
            start_dt = pd.to_datetime(equity_curve["date"].iloc[0])
            end_dt = pd.to_datetime(equity_curve["date"].iloc[-1])
            days = (end_dt - start_dt).days
            if days > 0:
                years = days / 365.25
                cagr_val = (final_cap / init_cap) ** (1.0 / years) - 1.0
                cagr = round(float(cagr_val), 4)
        except Exception:
            pass

    # 4. Maximum Drawdown calculation
    if not equity_curve.empty and "equity" in equity_curve.columns:
        eq_series = equity_curve["equity"].astype(float)
        peaks = eq_series.cummax()
        dd_amount_series = peaks - eq_series
        max_drawdown_amount = round(float(dd_amount_series.max()), 2)

        # Percentage drawdown relative to peak
        dd_pct_series = dd_amount_series / peaks
        max_drawdown_pct = round(float(dd_pct_series.max()), 4)
    else:
        max_drawdown_amount = 0.0
        max_drawdown_pct = 0.0

    # 5. Risk-adjusted metrics (Sharpe, Sortino, Calmar)
    if not equity_curve.empty and "equity" in equity_curve.columns and len(equity_curve) >= 2:
        # Use simple daily returns from equity curve
        returns = equity_curve["equity"].astype(float).pct_change().fillna(0.0)

        # Annualized Sharpe ratio (rf=0, annualization=252)
        mu = returns.mean()
        std = returns.std(ddof=1)
        if std > 0:
            sharpe_val = (mu / std) * np.sqrt(252.0)
            sharpe_ratio = round(float(sharpe_val), 4)
        else:
            sharpe_ratio = 0.0

        # Annualized Sortino ratio (MAR=0, annualization=252)
        # empyrical convention: downside deviation using all bars with positive returns clipped to 0
        downside = np.clip(returns, -np.inf, 0.0)
        downside_dev = np.sqrt(np.mean(downside**2))
        if downside_dev > 0:
            sortino_val = (mu / downside_dev) * np.sqrt(252.0)
            sortino_ratio = round(float(sortino_val), 4)
        else:
            sortino_ratio = 0.0

        # Calmar ratio: CAGR / abs(max_drawdown_pct)
        if max_drawdown_pct > 0:
            calmar_ratio = round(float(cagr / abs(max_drawdown_pct)), 4)
        else:
            calmar_ratio = 0.0
    else:
        sharpe_ratio = 0.0
        sortino_ratio = 0.0
        calmar_ratio = 0.0

    return PerformanceMetrics(
        total_trades=total_trades,
        win_trades=win_trades,
        loss_trades=loss_trades,
        win_rate=win_rate,
        avg_profit=avg_profit,
        avg_loss=avg_loss,
        total_return_pct=total_return_pct,
        initial_capital=init_cap,
        final_capital=final_cap,
        net_profit=net_profit,
        cagr=cagr,
        max_drawdown_pct=max_drawdown_pct,
        max_drawdown_amount=max_drawdown_amount,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        profit_factor=profit_factor,
        expectancy=expectancy,
        avg_days_held=avg_days_held,
    )
