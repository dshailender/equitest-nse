"""Position sizing, risk allocation, and stop loss calculation module."""

import math


def stop_loss_price(entry: float, sl_pct: float = 0.07) -> float:
    """Calculate the stop loss price level from entry price.

    Formula: entry * (1 - sl_pct)

    Args:
        entry: Trade entry price.
        sl_pct: Stop loss percentage distance (default: 0.07 = 7%).

    Returns:
        float: Stop loss price rounded to 2 decimal places.

    Raises:
        ValueError: If entry <= 0 or sl_pct is not in (0, 1).
    """
    if entry <= 0:
        raise ValueError("Entry price must be positive")
    if not (0.0 < sl_pct < 1.0):
        raise ValueError("Stop loss percentage must be between 0 and 1")

    return round(entry * (1.0 - sl_pct), 2)


def risk_amount(corpus: float, risk_pct: float = 0.02) -> float:
    """Calculate the maximum monetary corpus risk for a single trade.

    Formula: corpus * risk_pct

    Args:
        corpus: Total available portfolio capital.
        risk_pct: Maximum allowed risk fraction (default: 0.02 = 2%).

    Returns:
        float: Monetary risk amount rounded to 2 decimal places.

    Raises:
        ValueError: If corpus < 0 or risk_pct is not in (0, 1].
    """
    if corpus < 0:
        raise ValueError("Corpus cannot be negative")
    if not (0.0 < risk_pct <= 1.0):
        raise ValueError("Risk percentage must be between 0 and 1")

    return round(corpus * risk_pct, 2)


def position_size(
    corpus: float,
    entry: float,
    sl_pct: float = 0.07,
    risk_pct: float = 0.02,
    lot_size: int = 1,
) -> int:
    """Derive integer position share quantity from 2% risk and 7% stop loss.

    Formula:
        risk_amt = corpus * risk_pct
        sl_distance = entry * sl_pct
        qty = floor( (risk_amt / sl_distance) / lot_size ) * lot_size

    Args:
        corpus: Current portfolio corpus.
        entry: Trade entry price.
        sl_pct: Stop loss fraction (default: 0.07 = 7%).
        risk_pct: Account risk fraction per trade (default: 0.02 = 2%).
        lot_size: Minimum share lot multiple (default: 1).

    Returns:
        int: Maximum integer share quantity that bounds risk <= risk_amount.
    """
    if corpus <= 0 or entry <= 0:
        return 0
    if lot_size < 1:
        raise ValueError("Lot size must be at least 1")
    if not (0.0 < sl_pct < 1.0):
        raise ValueError("Stop loss percentage must be between 0 and 1")
    if not (0.0 < risk_pct <= 1.0):
        raise ValueError("Risk percentage must be between 0 and 1")

    sl_dist = entry * sl_pct
    risk_amt = corpus * risk_pct
    raw_qty = risk_amt / sl_dist
    qty = math.floor(raw_qty / lot_size) * lot_size
    return max(0, int(qty))


def capital_required(size: int, entry: float) -> float:
    """Calculate the total capital required to establish a position.

    Formula: size * entry

    Args:
        size: Share quantity.
        entry: Entry price per share.

    Returns:
        float: Capital required rounded to 2 decimal places.

    Raises:
        ValueError: If size < 0 or entry < 0.
    """
    if size < 0:
        raise ValueError("Size cannot be negative")
    if entry < 0:
        raise ValueError("Entry price cannot be negative")

    return round(size * entry, 2)


def can_allocate(corpus: float, open_positions_value: float, required: float) -> bool:
    """Check whether candidate trade can be allocated without exceeding corpus.

    Rule: total exposure (open_positions_value + required) <= corpus.

    Args:
        corpus: Total available portfolio capital.
        open_positions_value: Sum of capital currently deployed in open positions.
        required: Capital required for the candidate trade.

    Returns:
        bool: True if capital can be allocated, False otherwise.
    """
    if corpus < 0 or open_positions_value < 0 or required < 0:
        return False

    return round(open_positions_value + required, 2) <= round(corpus, 2)
