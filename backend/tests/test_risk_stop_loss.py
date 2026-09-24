"""Tests for REQ-4.1: Stop Loss Calculation and Gap-down Exit Resolution."""

import pytest

from app.risk.gap import resolve_stop_exit
from app.risk.position import (
    position_size,
    stop_loss_price,
)


def test_stop_loss_price_calculation():
    """Verify stop loss price is strictly entry * (1 - sl_pct) with 7% default."""
    assert stop_loss_price(100.0) == 93.0
    assert stop_loss_price(100.0, sl_pct=0.07) == 93.0
    assert stop_loss_price(200.0, sl_pct=0.05) == 190.0
    assert stop_loss_price(2450.50, sl_pct=0.07) == 2278.96


def test_stop_loss_price_validation():
    """Verify invalid entry or sl_pct parameters raise ValueError."""
    with pytest.raises(ValueError, match="Entry price must be positive"):
        stop_loss_price(0.0)

    with pytest.raises(ValueError, match="Entry price must be positive"):
        stop_loss_price(-10.0)

    with pytest.raises(ValueError, match="Stop loss percentage"):
        stop_loss_price(100.0, sl_pct=0.0)

    with pytest.raises(ValueError, match="Stop loss percentage"):
        stop_loss_price(100.0, sl_pct=1.0)


def test_gap_down_exit_semantics():
    """Gap test: open=90, sl=93 -> exit at 90, loss > 7%, realized loss > 2%."""
    entry_price = 100.0
    sl = stop_loss_price(entry_price, sl_pct=0.07)
    assert sl == 93.0

    # Market opens below stop loss (overnight gap down)
    open_price = 90.0
    low_price = 85.0
    exit_price, reason = resolve_stop_exit(open_price, low_price, sl)

    assert exit_price == 90.0
    assert reason == "gap"

    # Percentage loss exceeds nominal 7% stop loss
    realized_loss_pct = (entry_price - exit_price) / entry_price
    assert realized_loss_pct == 0.10
    assert realized_loss_pct > 0.07

    # Verify actual monetary loss exceeds 2% of corpus across accounts
    # Case 1: Standard ₹5,00,000 corpus (qty=1428, risk_amount=10000)
    corpus_500k = 500000.0
    qty_500k = position_size(corpus_500k, entry_price, sl_pct=0.07, risk_pct=0.02)
    actual_loss_500k = qty_500k * (entry_price - exit_price)
    loss_fraction_500k = actual_loss_500k / corpus_500k
    assert actual_loss_500k == 14280.0
    assert loss_fraction_500k > 0.02  # 2.856% > 2.0%

    # Case 2: ₹1,00,000 corpus (qty=285, risk_amount=2000)
    corpus_100k = 100000.0
    qty_100k = position_size(corpus_100k, entry_price, sl_pct=0.07, risk_pct=0.02)
    actual_loss_100k = qty_100k * (entry_price - exit_price)
    loss_fraction_100k = actual_loss_100k / corpus_100k
    assert actual_loss_100k == 2850.0
    assert loss_fraction_100k > 0.02  # 2.85% > 2.0%


def test_intraday_stop_loss_exit():
    """Verify intraday stop hit (open > sl, low <= sl) exits at exact sl price."""
    open_price = 95.0
    low_price = 92.0
    sl_price = 93.0

    exit_price, reason = resolve_stop_exit(open_price, low_price, sl_price)
    assert exit_price == 93.0
    assert reason == "stop_loss"


def test_no_stop_loss_exit():
    """Verify bar holding above stop loss (low > sl) does not trigger exit."""
    open_price = 95.0
    low_price = 94.0
    sl_price = 93.0

    exit_price, reason = resolve_stop_exit(open_price, low_price, sl_price)
    assert exit_price == 0.0
    assert reason == "none"


def test_stop_exit_input_validation():
    """Verify invalid price configurations raise descriptive ValueErrors."""
    with pytest.raises(ValueError, match="Prices must be positive"):
        resolve_stop_exit(0.0, 90.0, 93.0)

    with pytest.raises(ValueError, match="Low price cannot exceed Open price"):
        resolve_stop_exit(90.0, 95.0, 93.0)
