"""Backtest result container and serialization module."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class BacktestResult:
    """Holds the complete output of a simulation run."""

    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    config: dict[str, Any] = field(default_factory=dict)
    period: dict[str, str | None] = field(default_factory=dict)
    rejections: list[dict[str, Any]] = field(default_factory=list)
    open_positions: list[dict[str, Any]] = field(default_factory=list)
    initial_capital: float = 500000.0

    @property
    def final_capital(self) -> float:
        """Ending portfolio equity."""
        if not self.equity_curve.empty and "equity" in self.equity_curve.columns:
            return round(float(self.equity_curve["equity"].iloc[-1]), 2)
        return round(self.initial_capital, 2)

    @property
    def total_return(self) -> float:
        """Net monetary gain or loss over starting capital."""
        return round(self.final_capital - self.initial_capital, 2)

    @property
    def total_return_pct(self) -> float:
        """Total return percentage rounded to 4 decimal places."""
        if self.initial_capital <= 0:
            return 0.0
        return round(
            (self.final_capital - self.initial_capital) / self.initial_capital, 4
        )

    @property
    def total_trades(self) -> int:
        """Number of closed round-trip trades."""
        return len(self.trades)

    @property
    def win_trades(self) -> int:
        """Number of closed trades with positive net PnL."""
        if self.trades.empty or "pnl" not in self.trades.columns:
            return 0
        return int((self.trades["pnl"] > 0).sum())

    @property
    def loss_trades(self) -> int:
        """Number of closed trades with non-positive net PnL."""
        if self.trades.empty or "pnl" not in self.trades.columns:
            return 0
        return int((self.trades["pnl"] <= 0).sum())

    @property
    def win_rate(self) -> float:
        """Fraction of winning trades (0.0 to 1.0)."""
        if self.total_trades == 0:
            return 0.0
        return round(self.win_trades / self.total_trades, 4)

    @property
    def avg_profit(self) -> float:
        """Average net profit of winning trades."""
        if self.trades.empty or "pnl" not in self.trades.columns:
            return 0.0
        wins = self.trades[self.trades["pnl"] > 0]["pnl"]
        return round(float(wins.mean()), 2) if not wins.empty else 0.0

    @property
    def avg_loss(self) -> float:
        """Average net loss of losing trades."""
        if self.trades.empty or "pnl" not in self.trades.columns:
            return 0.0
        losses = self.trades[self.trades["pnl"] <= 0]["pnl"]
        return round(float(losses.mean()), 2) if not losses.empty else 0.0

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough monetary drawdown."""
        if self.equity_curve.empty or "drawdown" not in self.equity_curve.columns:
            return 0.0
        return round(float(self.equity_curve["drawdown"].max()), 2)

    @property
    def max_drawdown_pct(self) -> float:
        """Maximum peak-to-trough percentage drawdown."""
        if self.equity_curve.empty or "drawdown_pct" not in self.equity_curve.columns:
            return 0.0
        return round(float(self.equity_curve["drawdown_pct"].max()), 4)

    @property
    def cagr(self) -> float:
        """Annualized compound growth rate (CAGR)."""
        if (
            not self.equity_curve.empty
            and "date" in self.equity_curve.columns
            and len(self.equity_curve) >= 2
            and self.initial_capital > 0
            and self.final_capital > 0
        ):
            try:
                start_dt = pd.to_datetime(self.equity_curve["date"].iloc[0])
                end_dt = pd.to_datetime(self.equity_curve["date"].iloc[-1])
                days = (end_dt - start_dt).days
                if days > 0:
                    years = days / 365.25
                    cagr_val = (self.final_capital / self.initial_capital) ** (
                        1.0 / years
                    ) - 1.0
                    return round(float(cagr_val), 4)
            except Exception:
                pass
        return self.total_return_pct

    def summary(self) -> dict[str, Any]:
        """Returns key performance indicators dictionary."""
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "cagr": self.cagr,
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "win_rate": self.win_rate,
            "avg_profit": self.avg_profit,
            "avg_loss": self.avg_loss,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "period": self.period,
        }

    def to_dict(self) -> dict[str, Any]:
        """Converts result object to JSON-serializable dictionary."""
        trades_list = (
            self.trades.to_dict(orient="records") if not self.trades.empty else []
        )
        equity_list = (
            self.equity_curve.to_dict(orient="records")
            if not self.equity_curve.empty
            else []
        )
        return {
            "summary": self.summary(),
            "config": self.config,
            "period": self.period,
            "trades": trades_list,
            "equity_curve": equity_list,
            "rejections": self.rejections,
            "open_positions": self.open_positions,
        }

    def to_json(self, indent: int = 2) -> str:
        """Converts result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, file_path: str | Path) -> None:
        """Saves serialized result dictionary to disk."""
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, file_path: str | Path) -> "BacktestResult":
        """Loads BacktestResult from JSON file on disk."""
        target = Path(file_path)
        with open(target, encoding="utf-8") as f:
            data = json.load(f)

        trades_df = pd.DataFrame(data.get("trades", []))
        equity_df = pd.DataFrame(data.get("equity_curve", []))
        summary = data.get("summary", {})
        init_cap = float(summary.get("initial_capital", 500000.0))

        return cls(
            trades=trades_df,
            equity_curve=equity_df,
            config=data.get("config", {}),
            period=data.get("period", {}),
            rejections=data.get("rejections", []),
            open_positions=data.get("open_positions", []),
            initial_capital=init_cap,
        )
