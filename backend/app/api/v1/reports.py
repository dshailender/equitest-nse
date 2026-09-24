"""REST API router for Reporting and Analytics (REQ-7.1, REQ-7.2, REQ-7.3)."""

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.api.v1.schemas import (
    MonthlyReturnRow,
    ReportMonthlyResponse,
    ReportSummaryResponse,
)
from app.db.models import BacktestRun
from app.db.session import get_session
from app.engine.result import BacktestResult
from app.reports.export import (
    generate_report_xlsx,
    generate_report_zip,
    generate_trades_csv,
)
from app.reports.metrics import calculate_metrics
from app.reports.monthly import compute_monthly_returns

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def _load_run_and_result(
    run_id: str, session: Session
) -> tuple[BacktestRun, BacktestResult]:
    """Helper retrieving BacktestRun record and loading its BacktestResult blob."""
    run_record = session.get(BacktestRun, run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run '{run_id}' not found",
        )

    if (
        run_record.status != "completed"
        or not run_record.result_blob_path
        or not Path(run_record.result_blob_path).exists()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Backtest run '{run_id}' has not completed or result blob is missing "
                f"(current status: {run_record.status})"
            ),
        )

    try:
        result = BacktestResult.load(run_record.result_blob_path)
    except Exception as err:
        logger.exception("Failed to load result blob for run %s: %s", run_id, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load backtest result blob: {err}",
        ) from err

    return run_record, result


@router.get(
    "/{run_id}/summary",
    response_model=ReportSummaryResponse,
    summary="Get Backtest Run Performance Summary",
    description=(
        "Returns comprehensive core and advanced performance metrics (REQ-7.1)."
    ),
)
def api_get_report_summary(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ReportSummaryResponse:
    run_record, result = _load_run_and_result(run_id, session)

    metrics = calculate_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=result.initial_capital,
    )

    config_dict = json.loads(run_record.config_json or "{}")

    return ReportSummaryResponse(
        run_id=run_record.id,
        status=run_record.status,
        created_at=run_record.created_at,
        config=config_dict,
        metrics=metrics,
    )


@router.get(
    "/{run_id}/monthly",
    response_model=ReportMonthlyResponse,
    summary="Get Monthly Returns Matrix",
    description="Returns Month x Year compounded returns matrix (REQ-7.2).",
)
def api_get_report_monthly(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ReportMonthlyResponse:
    _, result = _load_run_and_result(run_id, session)

    monthly_rows = compute_monthly_returns(result.equity_curve)
    pydantic_rows = [MonthlyReturnRow(**r) for r in monthly_rows]

    return ReportMonthlyResponse(
        run_id=run_id,
        years=pydantic_rows,
    )


@router.get(
    "/{run_id}/export",
    summary="Export Backtest Report Bundle",
    description=(
        "Exports trade ledger and metrics bundle as CSV, XLSX, or ZIP (REQ-7.3)."
    ),
)
def api_export_report(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
    format: str = Query(
        "csv",
        description=(
            "Export format: 'csv' (trade ledger), 'xlsx' (Excel workbook), "
            "or 'zip' (all CSVs)"
        ),
        pattern="^(csv|xlsx|zip)$",
    ),
) -> Response:
    _, result = _load_run_and_result(run_id, session)

    metrics = calculate_metrics(
        trades=result.trades,
        equity_curve=result.equity_curve,
        initial_capital=result.initial_capital,
    )
    monthly_rows = compute_monthly_returns(result.equity_curve)

    if format == "csv":
        csv_data = generate_trades_csv(result.trades)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{run_id}_trades.csv"'
            },
        )
    elif format == "zip":
        zip_data = generate_report_zip(
            trades=result.trades,
            equity_curve=result.equity_curve,
            metrics=metrics,
            monthly_matrix=monthly_rows,
        )
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{run_id}_report.zip"'
            },
        )
    else:  # xlsx
        xlsx_data = generate_report_xlsx(
            trades=result.trades,
            equity_curve=result.equity_curve,
            metrics=metrics,
            monthly_matrix=monthly_rows,
        )
        return Response(
            content=xlsx_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{run_id}_report.xlsx"'
            },
        )
