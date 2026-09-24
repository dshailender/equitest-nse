"""Tests for REQ-4.2: Dynamic Risk Amount and Transaction Frictions / Slippage Costs."""

import pytest

from app.risk.position import risk_amount
from app.risk.slippage import apply_costs


def test_dynamic_risk_amount_calculation():
    """Verify dynamic 2% corpus risk computation across different capital levels."""
    # Baseline PRD corpus: ₹5,00,000 at 2% risk -> ₹10,000
    assert risk_amount(500000.0) == 10000.0
    assert risk_amount(500000.0, risk_pct=0.02) == 10000.0

    # Compounded capital: ₹7,50,000 at 2% risk -> ₹15,000
    assert risk_amount(750000.0, risk_pct=0.02) == 15000.0

    # Drawdown capital: ₹4,00,000 at 2% risk -> ₹8,000
    assert risk_amount(400000.0, risk_pct=0.02) == 8000.0

    # Smaller test corpus: ₹1,00,000 at 2% risk -> ₹2,000
    assert risk_amount(100000.0, risk_pct=0.02) == 2000.0

    # Custom risk percentage: 1.5%
    assert risk_amount(100000.0, risk_pct=0.015) == 1500.0


def test_risk_amount_validation():
    """Verify invalid corpus or risk fraction raises ValueError."""
    with pytest.raises(ValueError, match="Corpus cannot be negative"):
        risk_amount(-500.0)

    with pytest.raises(ValueError, match="Risk percentage must be between 0 and 1"):
        risk_amount(500000.0, risk_pct=0.0)

    with pytest.raises(ValueError, match="Risk percentage must be between 0 and 1"):
        risk_amount(500000.0, risk_pct=1.5)


def test_apply_costs_buy_side():
    """Cost test: apply_costs(100, 'buy', 10bps) == 100.10 within tolerance."""
    # 10 bps = 0.10% friction penalty on purchase price
    assert apply_costs(100.0, "buy", cost_bps=10.0) == 100.10
    assert apply_costs(100.0, "long", cost_bps=10.0) == 100.10
    assert apply_costs(100.0, "BUY", cost_bps=10.0) == 100.10

    # Default cost_bps is 10.0
    assert apply_costs(100.0, "buy") == 100.10


def test_apply_costs_sell_side():
    """Verify sell side deducts friction costs from execution price."""
    # 10 bps = 0.10% friction deducted on sale price
    assert apply_costs(100.0, "sell", cost_bps=10.0) == 99.90
    assert apply_costs(100.0, "short", cost_bps=10.0) == 99.90
    assert apply_costs(100.0, "SELL") == 99.90


def test_apply_costs_custom_rates():
    """Verify custom brokerage/slippage basis points."""
    # 20 bps = 0.20%
    assert apply_costs(500.0, "buy", cost_bps=20.0) == 501.00
    assert apply_costs(500.0, "sell", cost_bps=20.0) == 499.00

    # 0 bps = Zero slippage
    assert apply_costs(250.0, "buy", cost_bps=0.0) == 250.00
    assert apply_costs(250.0, "sell", cost_bps=0.0) == 250.00


def test_apply_costs_validation():
    """Verify invalid price, side, or cost_bps raises descriptive ValueError."""
    with pytest.raises(ValueError, match="Price must be positive"):
        apply_costs(0.0, "buy")

    with pytest.raises(ValueError, match="Price must be positive"):
        apply_costs(-100.0, "buy")

    with pytest.raises(ValueError, match="Cost basis points cannot be negative"):
        apply_costs(100.0, "buy", cost_bps=-5.0)

    with pytest.raises(ValueError, match="Invalid order side"):
        apply_costs(100.0, "hold")

