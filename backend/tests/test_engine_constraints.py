"""Unit tests for Capital Constraints and Ranking Rules (REQ-5.3)."""

from pathlib import Path

import pandas as pd

from app.engine.backtest import Backtest, DefaultRanker
from app.strategy.config import StrategyConfig

TINY_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "fixtures"
    / "tiny_universe"
)


def test_capital_constraint_fourth_signal_rejected():
    """With corpus Rs 5L and 28.5% allocation, 4th concurrent signal is rejected."""
    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")

    # Create 4 stocks: SYM1, SYM2, SYM3, SYM4
    # All generate entry signals on the exact same date (2021-05-24)
    # by cloning ALPHA price series.
    alpha = pd.read_parquet(TINY_DIR / "ALPHA.parquet")

    prices = {
        "SYM1": alpha.copy(),
        "SYM2": alpha.copy(),
        "SYM3": alpha.copy(),
        "SYM4": alpha.copy(),
    }

    # Sizing math: Rs 217.61 entry, 7% SL, 2% risk of Rs 500,000 corpus:
    # Qty = floor(10000 / 15.2327) = 656 shares
    # Capital required = 656 * 217.61 = Rs 142,752.16 (~28.55% of corpus)
    # 3 positions = 3 * 142,752.16 = Rs 428,256.48.
    # Free capital remaining = 500,000 - 428,256.48 = Rs 71,743.52.
    # 4th position requires 142,752.16 > 71,743.52 -> REJECTED.
    config = StrategyConfig(corpus=500000.0, risk_pct=0.02, stop_loss_pct=0.07)
    engine = Backtest(config=config, prices=prices, nifty=nifty)

    # Run for window around entry date (2021-05-24 signal -> 2021-05-25 entry)
    result = engine.run(start="2021-05-20", end="2021-05-30")

    # Exactly 3 positions opened, 1 rejected
    assert len(result.open_positions) == 3
    assert len(result.rejections) == 1

    rej = result.rejections[0]
    assert rej["date"] == "2021-05-25"
    assert rej["reason"] == "insufficient_capital"
    assert rej["required"] > rej["free_capital"]
    assert rej["required"] == 142752.16
    assert rej["free_capital"] < 142752.16


def test_default_ranker_momentum_sorting():
    """DefaultRanker prioritizes candidates with highest (Close - EMA20) / EMA20."""
    eval_date = "2021-05-24"

    # Synthetic signals dict with 3 candidates
    sig_high = pd.DataFrame(
        [{"date": eval_date, "close": 110.0, "adj_close": 110.0, "ema_20": 100.0}]
    )  # +10%
    sig_med = pd.DataFrame(
        [{"date": eval_date, "close": 105.0, "adj_close": 105.0, "ema_20": 100.0}]
    )  # +5%
    sig_low = pd.DataFrame(
        [{"date": eval_date, "close": 102.0, "adj_close": 102.0, "ema_20": 100.0}]
    )  # +2%

    signals = {
        "SYM_LOW": sig_low,
        "SYM_HIGH": sig_high,
        "SYM_MED": sig_med,
    }

    ranker = DefaultRanker()
    ranked = ranker.rank(["SYM_LOW", "SYM_HIGH", "SYM_MED"], eval_date, signals)

    assert ranked == ["SYM_HIGH", "SYM_MED", "SYM_LOW"]


def test_custom_pluggable_ranker():
    """Backtest engine respects a pluggable custom Ranker implementation."""

    class ReverseRanker:
        """Custom ranker sorting candidate symbols in reverse alphabetical order."""

        def rank(
            self,
            candidates: list[str],
            eval_date: str,
            signals: dict[str, pd.DataFrame],
        ) -> list[str]:
            return sorted(candidates, reverse=True)

    nifty = pd.read_parquet(TINY_DIR / "NIFTY_TINY.parquet")
    alpha = pd.read_parquet(TINY_DIR / "ALPHA.parquet")

    # 4 symbols: A_SYM, B_SYM, C_SYM, D_SYM
    # ReverseRanker should prioritize D_SYM, C_SYM, B_SYM, leaving A_SYM rejected
    prices = {
        "A_SYM": alpha.copy(),
        "B_SYM": alpha.copy(),
        "C_SYM": alpha.copy(),
        "D_SYM": alpha.copy(),
    }

    config = StrategyConfig(corpus=500000.0, risk_pct=0.02, stop_loss_pct=0.07)
    engine = Backtest(config=config, prices=prices, nifty=nifty, ranker=ReverseRanker())
    result = engine.run(start="2021-05-20", end="2021-05-30")

    opened_symbols = {p["symbol"] for p in result.open_positions}
    assert opened_symbols == {"D_SYM", "C_SYM", "B_SYM"}
    assert len(result.rejections) == 1
    assert result.rejections[0]["symbol"] == "A_SYM"
