"""Risk management and position sizing REST endpoints."""

from fastapi import APIRouter

from app.api.v1.schemas import (
    RiskConfigResponse,
    RiskSizeRequest,
    RiskSizeResponse,
)
from app.risk.position import (
    capital_required,
    position_size,
    risk_amount,
    stop_loss_price,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post(
    "/size",
    response_model=RiskSizeResponse,
    summary="Calculate Position Size and Risk",
    description=(
        "Derives integer share quantity, capital required, stop loss price, "
        "and monetary risk amount based on corpus, entry price, stop loss %, "
        "and risk % (REQ-4.1, REQ-4.2, REQ-4.3)."
    ),
)
async def api_calculate_risk_size(request: RiskSizeRequest) -> RiskSizeResponse:
    """Calculate integer position size and derived risk levels."""
    qty = position_size(
        corpus=request.corpus,
        entry=request.entry,
        sl_pct=request.sl_pct,
        risk_pct=request.risk_pct,
        lot_size=request.lot_size,
    )
    cap = capital_required(qty, request.entry)
    sl = stop_loss_price(request.entry, request.sl_pct)
    risk_amt = risk_amount(request.corpus, request.risk_pct)

    return RiskSizeResponse(
        qty=qty,
        capital_required=cap,
        sl_price=sl,
        risk_amount=risk_amt,
    )


@router.get(
    "/config",
    response_model=RiskConfigResponse,
    summary="Get Default Risk Configuration",
    description=(
        "Returns baseline strategy risk, stop loss, capital, and cost parameters."
    ),
)
async def api_get_risk_config() -> RiskConfigResponse:
    """Return default risk and execution configuration parameters."""
    return RiskConfigResponse()
