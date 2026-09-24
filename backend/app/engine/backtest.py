"""Event-driven quantitative backtest engine (Phase 5: REQ-5.1, REQ-5.2, REQ-5.3)."""

import logging
from collections.abc import Callable
from typing import Any, Protocol

import pandas as pd

from app.engine.result import BacktestResult
from app.risk.gap import resolve_stop_exit
from app.risk.position import (
    can_allocate,
    capital_required,
    position_size,
    stop_loss_price,
)
from app.risk.slippage import apply_costs
from app.strategy.config import StrategyConfig
from app.strategy.signals import generate_signals

logger = logging.getLogger(__name__)


class Ranker(Protocol):
    """Protocol for candidate ranking when multiple entry signals occur."""

    def rank(
        self,
        candidates: list[str],
        eval_date: str,
        signals: dict[str, pd.DataFrame],
    ) -> list[str]:
        """Ranks candidate symbols for execution prioritization."""
        ...


class DefaultRanker:
    """Default ranker prioritizing entry candidates by momentum score:

    Score = (Close - EMA20) / EMA20 descending.

    Resolves PRD Open Question #3. Candidates whose closing prices have broken
    furthest above their 20-day exponential moving average receive highest
    execution priority under capital constraints.
    """

    def rank(
        self,
        candidates: list[str],
        eval_date: str,
        signals: dict[str, pd.DataFrame],
    ) -> list[str]:
        if len(candidates) <= 1:
            return list(candidates)

        scores: list[tuple[float, str]] = []
        for sym in candidates:
            sig_df = signals.get(sym)
            if sig_df is None or sig_df.empty:
                scores.append((-float("inf"), sym))
                continue

            if "date" in sig_df.columns:
                matches = sig_df[sig_df["date"] == eval_date]
            else:
                matches = sig_df.loc[[eval_date]] if eval_date in sig_df.index else None

            if matches is None or matches.empty:
                scores.append((-float("inf"), sym))
                continue

            row = matches.iloc[0]
            close_val = float(
                row["adj_close"] if "adj_close" in matches.columns else row["close"]
            )
            ema20_val = float(row["ema_20"]) if "ema_20" in matches.columns else 0.0

            if ema20_val > 0:
                momentum = (close_val - ema20_val) / ema20_val
            else:
                momentum = -float("inf")

            scores.append((momentum, sym))

        # Sort descending by momentum score, with symbol ascending as tie-breaker
        scores.sort(key=lambda item: (-item[0], item[1]))
        return [sym for _, sym in scores]


class Backtest:
    """Event-driven daily backtesting simulation engine.

    Iterates trading sessions chronologically, executes stop-loss / gap-down
    and strategy exits at market open, applies capital allocation limits,
    executes entry signals at next-day open with transaction friction,
    and records an audit trade ledger and daily mark-to-market equity curve.
    """

    def __init__(
        self,
        config: StrategyConfig | None = None,
        prices: dict[str, pd.DataFrame] | None = None,
        nifty: pd.DataFrame | None = None,
        universe_provider: Callable[[str], tuple[list[str], bool]] | None = None,
        ranker: Ranker | None = None,
    ):
        self.config = config or StrategyConfig()
        self.prices = prices or {}
        self.nifty = nifty if nifty is not None else pd.DataFrame()
        self.universe_provider = universe_provider
        self.ranker = ranker or DefaultRanker()

    def run(
        self,
        start: str | None = None,
        end: str | None = None,
    ) -> BacktestResult:
        """Executes simulation between start and end dates.

        Args:
            start: Optional start date filter (YYYY-MM-DD).
            end: Optional end date filter (YYYY-MM-DD).

        Returns:
            BacktestResult container with trade ledger and equity curve.
        """
        # Ensure we have benchmark data
        if self.nifty.empty:
            from app.data.source import get_price_source

            src = get_price_source()
            self.nifty = src.get_index_prices(
                "^NSEI", start="2000-01-01", end="2099-12-31"
            )

        # 1. Pre-compute signals for each stock across all available history
        signals: dict[str, pd.DataFrame] = {}
        for sym, df in self.prices.items():
            if df.empty:
                continue
            sig_df = generate_signals(
                stock_df=df, nifty_df=self.nifty, config=self.config
            )
            signals[sym] = sig_df

        # 2. Build fast session lookup tables
        # Map: date -> {sym: dict_of_bar_values}
        date_bars: dict[str, dict[str, dict[str, Any]]] = {}
        all_dates_set: set[str] = set()

        if "date" in self.nifty.columns:
            all_dates_set.update(self.nifty["date"].astype(str))

        for sym, sig_df in signals.items():
            if "date" not in sig_df.columns:
                continue
            for row in sig_df.itertuples(index=False):
                d = str(row.date)
                all_dates_set.add(d)
                if d not in date_bars:
                    date_bars[d] = {}
                date_bars[d][sym] = {
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "adj_close": float(getattr(row, "adj_close", row.close)),
                    "volume": float(row.volume),
                    "ema_20": float(getattr(row, "ema_20", 0.0) or 0.0),
                    "entry": bool(getattr(row, "entry", False)),
                    "exit": bool(getattr(row, "exit", False)),
                }

        # Filter sorted trading days within [start, end]
        sorted_all_dates = sorted(all_dates_set)
        trading_days = [
            d
            for d in sorted_all_dates
            if (start is None or d >= start) and (end is None or d <= end)
        ]

        # Simulation state
        initial_corpus = float(self.config.corpus)
        cash: float = initial_corpus
        corpus: float = initial_corpus
        open_positions: dict[str, dict[str, Any]] = {}
        closed_trades: list[dict[str, Any]] = []
        equity_records: list[dict[str, Any]] = []
        rejections: list[dict[str, Any]] = []
        peak_equity: float = initial_corpus

        cost_bps = float(self.config.cost_bps)
        sl_pct = float(self.config.stop_loss_pct)
        risk_pct = float(self.config.risk_pct)
        lot_size = int(self.config.lot_size)

        for t_idx, current_date in enumerate(trading_days):
            # Prior date in the chronological sequence
            if t_idx > 0:
                prev_date = trading_days[t_idx - 1]
            else:
                # If first session, find prior date from sorted_all_dates if available
                cur_pos = sorted_all_dates.index(current_date)
                prev_date = sorted_all_dates[cur_pos - 1] if cur_pos > 0 else None

            # --- STEP 1: Evaluate Exits First at Session T Open ---
            for sym, pos in list(open_positions.items()):
                sym_bar = date_bars.get(current_date, {}).get(sym)
                if sym_bar is None:
                    continue

                open_T = sym_bar["open"]
                low_T = sym_bar["low"]
                sl_price = pos["sl_price"]

                # 1a. Check stop loss and gap-down rules
                stop_exit_price, stop_reason = resolve_stop_exit(
                    open_T, low_T, sl_price
                )
                exit_price_raw: float | None = None
                exit_reason: str | None = None

                if stop_reason != "none":
                    exit_price_raw = stop_exit_price
                    exit_reason = stop_reason
                elif prev_date is not None:
                    # 1b. Check strategy exit trigger from T-1 close (Close < EMA20)
                    prev_sym_bar = date_bars.get(prev_date, {}).get(sym)
                    if prev_sym_bar is not None and prev_sym_bar["exit"]:
                        exit_price_raw = open_T
                        exit_reason = "exit_signal"

                if exit_price_raw is not None and exit_reason is not None:
                    # Execute sell exit with slippage
                    exit_price = apply_costs(exit_price_raw, "sell", cost_bps)
                    qty = pos["qty"]
                    buy_price = pos["entry_price"]

                    trade_pnl = round((exit_price - buy_price) * qty, 2)
                    trade_pnl_pct = (
                        round((exit_price - buy_price) / buy_price, 4)
                        if buy_price > 0
                        else 0.0
                    )
                    sell_cost = round(qty * (exit_price_raw - exit_price), 2)
                    total_costs = round(pos["buy_costs"] + sell_cost, 2)
                    days_held = t_idx - pos["entry_t_idx"]

                    # Credit cash
                    cash += round(qty * exit_price, 2)
                    corpus += trade_pnl

                    closed_trades.append(
                        {
                            "symbol": sym,
                            "entry_date": pos["entry_date"],
                            "entry_price": buy_price,
                            "qty": qty,
                            "exit_date": current_date,
                            "exit_price": exit_price,
                            "pnl": trade_pnl,
                            "pnl_pct": trade_pnl_pct,
                            "exit_reason": exit_reason,
                            "days_held": max(1, days_held),
                            "costs": total_costs,
                        }
                    )
                    del open_positions[sym]

            # --- STEP 2: Compute Free Capital ---
            # open_positions_value is sum of capital deployed in open positions
            open_positions_value = sum(
                pos["capital_required"] for pos in open_positions.values()
            )
            free_capital = max(0.0, round(corpus - open_positions_value, 2))

            # --- STEP 3: Evaluate Candidate Entries on Session T Open ---
            if prev_date is not None:
                # Resolve universe constituents on T-1
                if self.universe_provider:
                    active_universe, _ = self.universe_provider(prev_date)
                    active_universe_set = set(active_universe)
                else:
                    active_universe_set = set(self.prices.keys())

                candidates: list[str] = []
                for sym in active_universe_set:
                    if sym in open_positions:
                        continue
                    prev_sym_bar = date_bars.get(prev_date, {}).get(sym)
                    if prev_sym_bar is not None and prev_sym_bar["entry"]:
                        candidates.append(sym)

                # Prioritize candidates via pluggable Ranker
                ranked_candidates = self.ranker.rank(candidates, prev_date, signals)

                for sym in ranked_candidates:
                    curr_sym_bar = date_bars.get(current_date, {}).get(sym)
                    if curr_sym_bar is None:
                        continue

                    raw_entry = curr_sym_bar["open"]
                    if raw_entry <= 0:
                        continue

                    # Sizing via Phase 4
                    qty = position_size(
                        corpus=corpus,
                        entry=raw_entry,
                        sl_pct=sl_pct,
                        risk_pct=risk_pct,
                        lot_size=lot_size,
                    )
                    req_capital = capital_required(qty, raw_entry)

                    if qty <= 0 or req_capital <= 0:
                        rejections.append(
                            {
                                "date": current_date,
                                "symbol": sym,
                                "reason": "zero_quantity",
                                "required": req_capital,
                                "free_capital": free_capital,
                            }
                        )
                        continue

                    # Capital allocation constraint check
                    if (
                        not can_allocate(corpus, open_positions_value, req_capital)
                        or req_capital > free_capital
                        or req_capital > cash
                    ):
                        rejection_entry = {
                            "date": current_date,
                            "symbol": sym,
                            "reason": "insufficient_capital",
                            "required": req_capital,
                            "free_capital": free_capital,
                            "open_positions_value": open_positions_value,
                            "corpus": corpus,
                        }
                        rejections.append(rejection_entry)
                        logger.info(
                            "Skipped %s on %s: capital %.2f > free %.2f",
                            sym,
                            current_date,
                            req_capital,
                            free_capital,
                        )

                        continue

                    # Open position with slippage
                    eff_entry = apply_costs(raw_entry, "buy", cost_bps)
                    buy_cost = round(qty * (eff_entry - raw_entry), 2)
                    spent = round(qty * eff_entry, 2)
                    sl_price = stop_loss_price(raw_entry, sl_pct)

                    cash -= spent
                    open_positions[sym] = {
                        "symbol": sym,
                        "entry_date": current_date,
                        "entry_t_idx": t_idx,
                        "raw_entry": raw_entry,
                        "entry_price": eff_entry,
                        "qty": qty,
                        "sl_price": sl_price,
                        "capital_required": req_capital,
                        "buy_costs": buy_cost,
                    }
                    open_positions_value += req_capital
                    free_capital = max(0.0, round(corpus - open_positions_value, 2))

            # --- STEP 4: Mark-to-Market Equity Curve Using T Close ---
            mtm_positions_val: float = 0.0
            for sym, pos in open_positions.items():
                curr_sym_bar = date_bars.get(current_date, {}).get(sym)
                close_price = (
                    curr_sym_bar["close"]
                    if curr_sym_bar is not None
                    else pos["raw_entry"]
                )
                mtm_positions_val += round(pos["qty"] * close_price, 2)

            current_equity = round(cash + mtm_positions_val, 2)
            if current_equity > peak_equity:
                peak_equity = current_equity

            drawdown = round(peak_equity - current_equity, 2)
            drawdown_pct = round(drawdown / peak_equity, 4) if peak_equity > 0 else 0.0

            prev_eq = equity_records[-1]["equity"] if equity_records else initial_corpus
            daily_ret = (
                round((current_equity - prev_eq) / prev_eq, 4) if prev_eq > 0 else 0.0
            )

            equity_records.append(
                {
                    "date": current_date,
                    "equity": current_equity,
                    "cash": round(cash, 2),
                    "positions_value": round(mtm_positions_val, 2),
                    "open_positions": len(open_positions),
                    "daily_return": daily_ret,
                    "drawdown": drawdown,
                    "drawdown_pct": drawdown_pct,
                }
            )

        # Assemble trades and equity DataFrames
        trades_cols = [
            "symbol",
            "entry_date",
            "entry_price",
            "qty",
            "exit_date",
            "exit_price",
            "pnl",
            "pnl_pct",
            "exit_reason",
            "days_held",
            "costs",
        ]
        trades_df = pd.DataFrame(closed_trades)
        if trades_df.empty:
            trades_df = pd.DataFrame(columns=trades_cols)
        else:
            trades_df = trades_df[trades_cols]

        equity_cols = [
            "date",
            "equity",
            "cash",
            "positions_value",
            "open_positions",
            "daily_return",
            "drawdown",
            "drawdown_pct",
        ]
        equity_df = pd.DataFrame(equity_records)
        if equity_df.empty:
            equity_df = pd.DataFrame(columns=equity_cols)
        else:
            equity_df = equity_df[equity_cols]

        open_positions_list = [
            {
                "symbol": pos["symbol"],
                "entry_date": pos["entry_date"],
                "entry_price": pos["entry_price"],
                "qty": pos["qty"],
                "sl_price": pos["sl_price"],
                "capital_required": pos["capital_required"],
            }
            for pos in open_positions.values()
        ]

        cfg_dict = (
            self.config.to_dict()
            if hasattr(self.config, "to_dict")
            else {
                "corpus": self.config.corpus,
                "risk_pct": self.config.risk_pct,
                "stop_loss_pct": self.config.stop_loss_pct,
                "lot_size": self.config.lot_size,
                "cost_bps": self.config.cost_bps,
            }
        )

        return BacktestResult(
            trades=trades_df,
            equity_curve=equity_df,
            config=cfg_dict,
            period={"start": start, "end": end},
            rejections=rejections,
            open_positions=open_positions_list,
            initial_capital=initial_corpus,
        )
