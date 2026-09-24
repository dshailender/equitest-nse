"""Transaction friction, brokerage, and slippage cost modeling."""


def apply_costs(price: float, side: str, cost_bps: float = 10.0) -> float:
    """Adjust execution price by transaction friction and slippage costs.

    Default is 10 basis points (0.10%) per side (REQ-0.3, PRD §3 Phase 0).
    - Buy/Long: Increases execution price by (1 + cost_bps / 10000).
    - Sell/Short: Decreases execution price by (1 - cost_bps / 10000).

    Args:
        price: Unadjusted trade execution price.
        side: Order side ('buy' or 'sell').
        cost_bps: Total friction cost in basis points (default: 10.0 bps = 0.1%).

    Returns:
        float: Friction-adjusted execution price rounded to 2 decimal places.

    Raises:
        ValueError: If price <= 0, cost_bps < 0, or side is not 'buy'/'sell'.
    """
    if price <= 0:
        raise ValueError("Price must be positive")
    if cost_bps < 0:
        raise ValueError("Cost basis points cannot be negative")

    side_clean = side.strip().lower()
    if side_clean in ("buy", "long"):
        adjusted = price * (1.0 + cost_bps / 10000.0)
    elif side_clean in ("sell", "short"):
        adjusted = price * (1.0 - cost_bps / 10000.0)
    else:
        raise ValueError(f"Invalid order side '{side}'. Must be 'buy' or 'sell'")

    return round(adjusted, 2)
