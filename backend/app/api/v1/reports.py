"""REST API router for Reporting and Analytics (REQ-7.1, REQ-7.2, REQ-7.3)."""

import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api.v1.schemas import (
    MonthlyReturnRow,
    PdfJobCreateResponse,
    PdfJobResponse,
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
from app.reports.jobs import (
    job_manager,
    render_pdf_first_page_png,
)
from app.reports.metrics import calculate_metrics
from app.reports.monthly import compute_monthly_returns
from app.reports.pdf import generate_pdf, sanitize_run_id

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


def _run_pdf_job(job_id: str, run_id: str):
    """Background worker for rendering large or explicitly async PDF jobs."""
    try:
        pdf_path = generate_pdf(run_id)
        job_manager.update_job(job_id, status="ready", file_path=str(pdf_path))
    except Exception as exc:
        logger.exception(
            "Background PDF job %s failed for run %s: %s", job_id, run_id, exc
        )
        job_manager.update_job(job_id, status="failed", error=str(exc))


@router.get(
    "/{run_id}/export",
    summary="Export Backtest Report Bundle",
    description=(
        "Exports trade ledger and metrics bundle as CSV, XLSX, ZIP, or PDF "
        "(REQ-7.3, REQ-9.1, REQ-9.4)."
    ),
)
def api_export_report(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
    background_tasks: BackgroundTasks,
    format: str = Query(
        "csv",
        description=(
            "Export format: 'csv' (trade ledger), 'xlsx' (Excel workbook), "
            "'zip' (all CSVs), or 'pdf' (print-ready PDF)"
        ),
        pattern="^(csv|xlsx|zip|pdf)$",
    ),
) -> Response:
    if format == "pdf":
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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Report data for run '{run_id}' is incomplete "
                    f"(status: {run_record.status})"
                ),
            )

        try:
            result = BacktestResult.load(run_record.result_blob_path)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Report data for run '{run_id}' is incomplete or corrupt: {err}"
                ),
            ) from err

        clean_run_id = sanitize_run_id(run_id)
        trade_count = len(result.trades)

        if trade_count <= 2000:
            # Synchronous PDF generation
            try:
                pdf_path = generate_pdf(run_id)
                pdf_bytes = pdf_path.read_bytes()
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="backtest_{clean_run_id}.pdf"'
                        )
                    },
                )
            except Exception as exc:
                logger.exception(
                    "Synchronous PDF generation failed for %s: %s", run_id, exc
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"PDF generation failed: {exc}",
                ) from exc
        else:
            # Asynchronous job dispatch for large runs (> 2000 trades)
            job = job_manager.create_job(run_id)
            background_tasks.add_task(_run_pdf_job, job.job_id, run_id)
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"job_id": job.job_id},
                headers={"Location": f"/api/v1/reports/jobs/{job.job_id}"},
            )

    # Legacy export paths (CSV, XLSX, ZIP)
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


@router.post(
    "/{run_id}/export/pdf/async",
    response_model=PdfJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Force Asynchronous PDF Generation",
    description=(
        "Forces async background PDF generation regardless of trade count " "(REQ-9.4)."
    ),
)
def api_export_pdf_async(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
    background_tasks: BackgroundTasks,
) -> JSONResponse:
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Report data for run '{run_id}' is incomplete "
                f"(status: {run_record.status})"
            ),
        )

    job = job_manager.create_job(run_id)
    background_tasks.add_task(_run_pdf_job, job.job_id, run_id)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job.job_id,
            "status": "pending",
            "message": "PDF generation job started",
        },
        headers={"Location": f"/api/v1/reports/jobs/{job.job_id}"},
    )


@router.get(
    "/jobs/{job_id}",
    response_model=PdfJobResponse,
    summary="Get Asynchronous PDF Job Status",
    description=(
        "Returns lifecycle status and metadata for an async PDF generation "
        "job (REQ-9.4)."
    ),
)
def api_get_pdf_job_status(job_id: str) -> PdfJobResponse:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF job '{job_id}' not found",
        )
    if job.is_expired():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"PDF job '{job_id}' has expired",
        )
    return job.to_response()


@router.get(
    "/jobs/{job_id}/download",
    summary="Download Generated PDF From Async Job",
    description="Streams the generated PDF report when status is 'ready' (REQ-9.4).",
)
def api_download_pdf_job(job_id: str) -> Response:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF job '{job_id}' not found",
        )
    if job.is_expired() or job.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"PDF job '{job_id}' has expired or failed: {job.error}",
        )
    if job.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"PDF job '{job_id}' is still generating",
        )

    if not job.file_path or not Path(job.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Generated PDF file is missing or has been cleaned up",
        )

    pdf_path = Path(job.file_path)
    clean_run_id = sanitize_run_id(job.run_id)
    return Response(
        content=pdf_path.read_bytes(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="backtest_{clean_run_id}.pdf"'
        },
    )


@router.get(
    "/{run_id}/preview.png",
    summary="Preview PDF First Page as PNG",
    description=(
        "Renders the first page of the PDF report as PNG for pre-download preview."
    ),
)
def api_get_pdf_preview(
    run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    run_record = session.get(BacktestRun, run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run '{run_id}' not found",
        )
    if run_record.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Run '{run_id}' is incomplete (status: {run_record.status})",
        )

    try:
        pdf_path = generate_pdf(run_id)
        preview_png_path = pdf_path.parent / f"{pdf_path.stem}_preview.png"
        render_pdf_first_page_png(pdf_path, preview_png_path)
        return Response(
            content=preview_png_path.read_bytes(),
            media_type="image/png",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview PNG: {exc}",
        ) from exc
