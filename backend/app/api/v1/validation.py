"""REST API router for TradingView cross-check validation (REQ-8.1)."""

import logging
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.api.v1.schemas import CrossCheckPoint, CrossCheckResponse
from app.db.session import get_session
from app.validation.cross_check import generate_cross_check_dataframe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get(
    "/{run_id}/{symbol}",
    response_model=CrossCheckResponse,
    summary="Get TradingView Cross-Check Data",
    description=(
        "Returns aligned indicators and entry/exit signals for manual visual "
        "diffing against TradingView (REQ-8.1). Supports JSON schema response "
        "or raw CSV file download via '?format=csv'."
    ),
)
def api_get_cross_check(
    run_id: str,
    symbol: str,
    session: Annotated[Session, Depends(get_session)],
    format: str = Query(
        "json",
        description="Response format: 'json' (default) or 'csv' (file attachment)",
        pattern="^(json|csv)$",
    ),
) -> Response | CrossCheckResponse:
    symbol_clean = symbol.strip().upper()

    try:
        df, csv_str = generate_cross_check_dataframe(
            run_id=run_id, symbol=symbol_clean, session=session, filter_dates=True
        )
    except ValueError as err:
        err_msg = str(err)
        if "not found" in err_msg.lower() or "no price data" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            ) from err
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        ) from err

    except Exception as err:
        logger.exception(
            "Failed generating cross-check for %s/%s: %s", run_id, symbol, err
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cross-check computation failed: {err}",
        ) from err

    if format == "csv":
        filename = f"{symbol_clean}_cross_check_{run_id}.csv"
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Convert DataFrame records to Pydantic CrossCheckPoint objects
    rows: list[CrossCheckPoint] = []
    for row in df.itertuples(index=False):
        ema20_val = None if pd_isna(row.ema_20) else float(row.ema_20)
        ema50_val = None if pd_isna(row.ema_50) else float(row.ema_50)
        ema150_val = None if pd_isna(row.ema_150) else float(row.ema_150)
        ema200_val = None if pd_isna(row.ema_200) else float(row.ema_200)
        high52_val = None if pd_isna(row.high_52w) else float(row.high_52w)

        rows.append(
            CrossCheckPoint(
                date=str(row.date),
                close=float(row.close),
                ema_20=ema20_val,
                ema_50=ema50_val,
                ema_150=ema150_val,
                ema_200=ema200_val,
                high_52w=high52_val,
                entry=bool(row.entry),
                exit=bool(row.exit),
            )
        )

    return CrossCheckResponse(
        run_id=run_id,
        symbol=symbol_clean,
        count=len(rows),
        rows=rows,
        csv=csv_str,
    )


def pd_isna(val: Any) -> bool:
    if val is None:
        return True
    try:
        return bool(np.isnan(val))
    except (TypeError, ValueError):
        return False
