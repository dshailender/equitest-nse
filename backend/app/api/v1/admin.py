"""REST API router for administrative storage governance and retention."""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlmodel import Session

from app.api.v1.schemas import RetentionCleanupRequest, RetentionCleanupResponse
from app.db.session import get_session
from app.engine.retention import enforce_backtest_retention

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/retention/cleanup",
    response_model=RetentionCleanupResponse,
    status_code=status.HTTP_200_OK,
    summary="Enforce Backtest Retention Cleanup",
    description=(
        "Manually or automatically triggers cascade purging of stale backtests "
        "and sweeps exceeding retention quotas."
    ),
)
def api_admin_retention_cleanup(
    session: Annotated[Session, Depends(get_session)],
    max_runs: Annotated[
        int | None,
        Query(description="Optional override for maximum standalone runs retained"),
    ] = None,
    max_sweeps: Annotated[
        int | None,
        Query(description="Optional override for maximum parameter sweeps retained"),
    ] = None,
    body: Annotated[
        RetentionCleanupRequest | None,
        Body(description="Optional request body to override retention limits"),
    ] = None,
) -> RetentionCleanupResponse:
    effective_max_runs = (
        max_runs if max_runs is not None else (body.max_runs if body else None)
    )
    effective_max_sweeps = (
        max_sweeps if max_sweeps is not None else (body.max_sweeps if body else None)
    )

    summary = enforce_backtest_retention(
        session=session,
        max_runs=effective_max_runs,
        max_sweeps=effective_max_sweeps,
    )
    return RetentionCleanupResponse(**summary)
