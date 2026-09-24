"""Tests for REQ-4.3: Position Sizing and Portfolio Allocation Constraints."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.risk.position import (
    can_allocate,
    capital_required,
    position_size,
    risk_amount,
)


def test_position_sizing_baseline_prd_inputs():
    """Verify position sizing formula matches PRD §4 requirements.

    Formula:
        risk_amount = corpus * risk_pct
        sl_distance = entry * sl_pct
        qty = floor(risk_amount / sl_distance)

    Test Cases:
    1. Corpus ₹5,00,000 (PRD baseline), entry ₹100, sl 7%, risk 2%:
       - risk_amount = ₹10,000
       - sl_distance = ₹7.00
       - qty = floor(10000 / 7) = 1428 shares
       - capital_required = ₹1,42,800 (~28.56% of corpus)
    2. Corpus ₹1,00,000, entry ₹100, sl 7%, risk 2%:
       - risk_amount = ₹2,000
       - sl_distance = ₹7.00
       - qty = floor(2000 / 7) = 285 shares
       - capital_required = ₹28,500 (28.5% of corpus)
    """
    # Case 1: Standard ₹5,00,000 corpus
    corpus_500k = 500000.0
    entry = 100.0
    sl_pct = 0.07
    risk_pct = 0.02

    risk_500k = risk_amount(corpus_500k, risk_pct)
    assert risk_500k == 10000.0
    assert math.floor(10000 / 7) == 1428

    qty_500k = position_size(corpus_500k, entry, sl_pct, risk_pct)
    assert qty_500k == 1428

    capital_500k = capital_required(qty_500k, entry)
    assert capital_500k == 142800.0
    # Stop loss monetary loss strictly within 2% risk limit
    assert qty_500k * (entry * sl_pct) == pytest.approx(9996.0)
    assert qty_500k * (entry * sl_pct) <= risk_500k

    # Case 2: ₹1,00,000 corpus (yielding exactly qty=285 and capital=28500)
    corpus_100k = 100000.0
    risk_100k = risk_amount(corpus_100k, risk_pct)
    assert risk_100k == 2000.0
    assert math.floor(2000 / 7) == 285

    qty_100k = position_size(corpus_100k, entry, sl_pct, risk_pct)
    assert qty_100k == 285

    capital_100k = capital_required(qty_100k, entry)
    assert capital_100k == 28500.0
    assert qty_100k * (entry * sl_pct) == pytest.approx(1995.0)
    assert qty_100k * (entry * sl_pct) <= risk_100k


def test_position_sizing_lot_size_multiples():
    """Verify position sizing respects lot size multiples."""
    corpus = 500000.0
    entry = 100.0

    # Unconstrained qty is 1428
    # With lot_size=25: floor(1428.57 / 25) * 25 = 57 * 25 = 1425
    qty_lot25 = position_size(corpus, entry, 0.07, 0.02, lot_size=25)
    assert qty_lot25 == 1425
    assert qty_lot25 % 25 == 0

    # With lot_size=100: floor(1428.57 / 100) * 100 = 14 * 100 = 1400
    qty_lot100 = position_size(corpus, entry, 0.07, 0.02, lot_size=100)
    assert qty_lot100 == 1400
    assert qty_lot100 % 100 == 0


def test_position_sizing_edge_cases():
    """Verify boundary inputs return zero or raise expected errors."""
    # Zero or negative capital / entry produces 0 shares
    assert position_size(0.0, 100.0) == 0
    assert position_size(-10000.0, 100.0) == 0
    assert position_size(500000.0, 0.0) == 0
    assert position_size(500000.0, -50.0) == 0

    # Invalid parameter ranges raise ValueError
    with pytest.raises(ValueError, match="Lot size must be at least 1"):
        position_size(500000.0, 100.0, lot_size=0)

    with pytest.raises(ValueError, match="Stop loss percentage"):
        position_size(500000.0, 100.0, sl_pct=0.0)

    with pytest.raises(ValueError, match="Risk percentage"):
        position_size(500000.0, 100.0, risk_pct=0.0)


def test_capital_required_validation():
    """Verify capital required calculations and validations."""
    assert capital_required(100, 50.25) == 5025.0
    assert capital_required(0, 150.0) == 0.0

    with pytest.raises(ValueError, match="Size cannot be negative"):
        capital_required(-5, 100.0)

    with pytest.raises(ValueError, match="Entry price cannot be negative"):
        capital_required(10, -50.0)


def test_can_allocate_portfolio_exposure():
    """Verify exposure constraint <= corpus (PRD §4: max 3-4 trades)."""
    corpus = 500000.0
    trade_capital = 142800.0  # 1428 * 100

    # Trade 1: 0 open positions -> total 142,800 <= 500k -> True
    assert (
        can_allocate(corpus, open_positions_value=0.0, required=trade_capital) is True
    )

    # Trade 2: 1 open position (142,800) -> total 285,600 <= 500k -> True
    assert (
        can_allocate(corpus, open_positions_value=142800.0, required=trade_capital)
        is True
    )

    # Trade 3: 2 open positions (285,600) -> total 428,400 <= 500k -> True
    assert (
        can_allocate(corpus, open_positions_value=285600.0, required=trade_capital)
        is True
    )

    # Trade 4: 3 open positions (428,400) -> total 571,200 > 500k -> False
    assert (
        can_allocate(corpus, open_positions_value=428400.0, required=trade_capital)
        is False
    )

    # Negative inputs reject allocation
    assert can_allocate(-1000.0, 0.0, trade_capital) is False
    assert can_allocate(corpus, -100.0, trade_capital) is False
    assert can_allocate(corpus, 0.0, -500.0) is False


@given(
    entry=st.floats(min_value=0.01, max_value=50000.0),
    corpus=st.floats(min_value=1000.0, max_value=10000000.0),
    sl_pct=st.floats(min_value=0.01, max_value=0.50),
    risk_pct=st.floats(min_value=0.001, max_value=0.10),
)
def test_hypothesis_risk_never_exceeds_max_risk_amount(
    entry: float, corpus: float, sl_pct: float, risk_pct: float
):
    """Property test (Hypothesis): for any entry>0, qty*entry*sl_pct <= risk_amount."""
    risk_limit = corpus * risk_pct
    qty = position_size(corpus, entry, sl_pct=sl_pct, risk_pct=risk_pct, lot_size=1)

    assert qty >= 0
    actual_risk_at_stop = qty * entry * sl_pct
    # Floating point precision safe comparison
    assert actual_risk_at_stop <= (risk_limit + 1e-7)
