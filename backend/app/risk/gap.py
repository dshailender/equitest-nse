"""Stop loss and gap-down exit resolution module."""


def resolve_stop_exit(
    open_: float, low: float, sl_price: float
) -> tuple[float, str]:
    """Resolve exit execution price and trigger reason for a stop loss order.

    Rules (PRD §4 & Assumptions):
    - If Open <= Stop Loss Price: Stop was breached overnight (gap-down).
      Exit executes at the Open price, incurring loss > stop loss %.
      Reason returned: "gap".
    - Else if Low <= Stop Loss Price: Stop loss was hit intraday during the session.
      Exit executes at the Stop Loss price.
      Reason returned: "stop_loss".
    - Else: Stop loss was not hit (Low > Stop Loss Price).
      Exit price: 0.0, reason: "none".

    Args:
        open_: Session open price.
        low: Session low price.
        sl_price: Stop loss trigger price.

    Returns:
        tuple[float, str]: (executed_exit_price, trigger_reason)
    """
    if open_ <= 0 or low <= 0 or sl_price <= 0:
        raise ValueError("Prices must be positive")
    if low > open_:
        raise ValueError("Low price cannot exceed Open price")

    if open_ <= sl_price:
        return (round(open_, 2), "gap")
    elif low <= sl_price:
        return (round(sl_price, 2), "stop_loss")
    else:
        return (0.0, "none")

