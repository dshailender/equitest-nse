"""Deterministic, institutional-grade PDF report generation engine.

Produces print-ready multi-page PDF documents for completed backtest runs using
WeasyPrint, Jinja2 templating, and server-side matplotlib charts (REQ-9.1, REQ-9.5).
"""

import base64
import hashlib
import io
import json
import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jinja2
import markdown
import pandas as pd
from pypdf import PdfReader, PdfWriter
from sqlmodel import Session
from weasyprint import HTML

from app.core.branding import get_branding_settings
from app.db.session import engine
from app.reports.charts import (
    render_drawdown,
    render_equity_curve,
    render_monthly_heatmap,
)
from app.reports.metrics import calculate_metrics
from app.reports.monthly import compute_monthly_returns
from app.validation.audit import load_run_audit

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class PdfGenerationError(Exception):
    """Raised when PDF report generation fails, wrapping underlying cause."""

    pass


def sanitize_run_id(run_id: str) -> str:
    """Sanitizes run_id against path traversal and special characters."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", run_id)


def generate_pdf(
    run_id: str,
    include_creation_date: bool = True,
    output_dir: Path | None = None,
) -> Path:
    """Generates print-ready, deterministic multi-page backtest PDF report.

    Covers REQ-9.1, REQ-9.5.

    Args:
        run_id: Backtest run identifier.
        include_creation_date: If False, strips timestamps and produces bit-for-bit
            identical PDF output across repeated runs.
        output_dir: Optional destination folder. Defaults to data/reports/.

    Returns:
        Path to the generated PDF file.

    Raises:
        PdfGenerationError: On missing run data or generation failure.
    """
    try:
        # 1. Load run metadata and BacktestResult
        from app.api.v1.reports import _load_run_and_result

        with Session(engine) as session:
            try:
                run_record, result = _load_run_and_result(run_id, session)
            except Exception as err:
                raise PdfGenerationError(
                    f"Failed loading run '{run_id}': {err}"
                ) from err

            audit = load_run_audit(run_id, session)

        # 2. Compute performance metrics and monthly matrix
        metrics = calculate_metrics(
            trades=result.trades,
            equity_curve=result.equity_curve,
            initial_capital=result.initial_capital,
        )
        monthly_matrix = compute_monthly_returns(result.equity_curve)

        # 3. Branding configuration
        branding = get_branding_settings()

        # 4. Period & Narrative calculations
        eq_df = result.equity_curve.copy()
        if not eq_df.empty and "date" in eq_df.columns:
            eq_dates = pd.to_datetime(eq_df["date"])
            start_date_str = eq_dates.min().strftime("%Y-%m-%d")
            end_date_str = eq_dates.max().strftime("%Y-%m-%d")
            days_span = (eq_dates.max() - eq_dates.min()).days
            years_span = max(round(days_span / 365.25, 1), 0.1)
        else:
            start_date_str = run_record.start_date or "N/A"
            end_date_str = run_record.end_date or "N/A"
            years_span = 1.0

        narrative = {
            "years": f"{years_span:.1f}",
            "trades": metrics.total_trades,
            "win_rate": f"{metrics.win_rate * 100:.1f}",
            "start_cap": f"₹{metrics.initial_capital:,.2f}",
            "end_cap": f"₹{metrics.final_capital:,.2f}",
            "cagr": f"{metrics.cagr * 100:+.2f}",
        }

        # 5. Strategy configuration items
        config_dict = json.loads(run_record.config_json or "{}")
        config_items = sorted(config_dict.items(), key=lambda x: str(x[0]))
        config_hash = hashlib.sha256(
            json.dumps(config_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()

        # 6. Trade log preparation & capping
        trades_df = result.trades.copy()
        if not include_creation_date and not trades_df.empty:
            sort_cols = [c for c in ["entry_date", "symbol"] if c in trades_df.columns]
            if sort_cols:
                trades_df = trades_df.sort_values(sort_cols).reset_index(drop=True)

        trades_count = len(trades_df)
        trades_truncated = trades_count > 5000
        trades_display = trades_df.iloc[:5000]

        trades_rows: list[dict[str, Any]] = []
        for _, row in trades_display.iterrows():
            trades_rows.append(
                {
                    "symbol": str(row.get("symbol", "")),
                    "entry_date": str(row.get("entry_date", "")),
                    "entry_price": float(row.get("entry_price", 0.0)),
                    "qty": int(row.get("qty", 0)),
                    "exit_date": str(row.get("exit_date", "")),
                    "exit_price": float(row.get("exit_price", 0.0)),
                    "pnl": float(row.get("pnl", 0.0)),
                    "pnl_pct": float(row.get("pnl_pct", 0.0)),
                    "days_held": int(row.get("days_held", 0)),
                    "exit_reason": str(row.get("exit_reason", "")),
                }
            )

        symbol_count = (
            int(trades_df["symbol"].nunique())
            if not trades_df.empty and "symbol" in trades_df.columns
            else 1
        )

        # 7. Render ASSUMPTIONS.md to HTML
        assumptions_path = REPO_ROOT / "docs" / "ASSUMPTIONS.md"
        if assumptions_path.exists():
            assumptions_raw = assumptions_path.read_text(encoding="utf-8")
            assumptions_html = markdown.markdown(
                assumptions_raw, extensions=["tables", "fenced_code"]
            )
        else:
            assumptions_html = "<p><em>ASSUMPTIONS.md documentation not found.</em></p>"

        # 8. Generation date handling
        if include_creation_date:
            generation_date_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            generation_date_str = ""

        # Setup destination path
        clean_run_id = sanitize_run_id(run_id)
        if output_dir:
            dest_dir = Path(output_dir)
        else:
            dest_dir = REPO_ROOT / "data" / "reports"
        dest_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = dest_dir / f"backtest_{clean_run_id}.pdf"

        # 9. Render charts in temporary workspace & compile template
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            eq_img_path = tmp_dir / "equity_curve.png"
            dd_img_path = tmp_dir / "drawdown.png"
            hm_img_path = tmp_dir / "monthly_heatmap.png"

            render_equity_curve(result.equity_curve, eq_img_path)
            render_drawdown(result.equity_curve, dd_img_path)
            render_monthly_heatmap(pd.DataFrame(monthly_matrix), hm_img_path)

            def _to_data_uri(path: Path) -> str:
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                return f"data:image/png;base64,{encoded}"

            eq_data_uri = _to_data_uri(eq_img_path)
            dd_data_uri = _to_data_uri(dd_img_path)
            hm_data_uri = _to_data_uri(hm_img_path)

            logo_uri = None
            if branding.logo_path and Path(branding.logo_path).is_file():
                raw_logo = Path(branding.logo_path).read_bytes()
                ext = Path(branding.logo_path).suffix.lstrip(".").lower() or "png"
                b64_logo = base64.b64encode(raw_logo).decode("ascii")
                logo_uri = f"data:image/{ext};base64,{b64_logo}"

            # Read CSS stylesheet template
            css_template_path = TEMPLATES_DIR / "report.css"
            css_raw = css_template_path.read_text(encoding="utf-8")
            css_compiled = jinja2.Template(css_raw).render(
                firm_name=branding.firm_name,
                run_id=run_id,
                footer_note=branding.footer_note,
                primary_color=branding.primary_color,
            )

            # Compile HTML template
            jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=True,
            )
            template = jinja_env.get_template("report.html.j2")
            html_content = template.render(
                stylesheet_content=css_compiled,
                branding=branding,
                strategy_name="4-EMA Breakout Strategy",
                run_id=run_id,
                generation_date=generation_date_str,
                start_date=start_date_str,
                end_date=end_date_str,
                symbol_count=symbol_count,
                narrative=narrative,
                metrics=metrics,
                config_items=config_items,
                audit=audit,
                config_hash=config_hash,
                equity_chart_path=eq_data_uri,
                drawdown_chart_path=dd_data_uri,
                heatmap_chart_path=hm_data_uri,
                logo_uri=logo_uri,
                trades_count=trades_count,
                trades_truncated=trades_truncated,
                trades_rows=trades_rows,
                assumptions_html=assumptions_html,
            )

            # Generate PDF with WeasyPrint
            old_epoch = os.environ.get("SOURCE_DATE_EPOCH")
            try:
                if not include_creation_date:
                    os.environ["SOURCE_DATE_EPOCH"] = "0"
                raw_pdf_bytes = HTML(string=html_content).write_pdf()
            finally:
                if not include_creation_date:
                    if old_epoch is not None:
                        os.environ["SOURCE_DATE_EPOCH"] = old_epoch
                    else:
                        os.environ.pop("SOURCE_DATE_EPOCH", None)

        # 10. Post-process with pypdf for deterministic mode if requested
        if not include_creation_date:
            reader = PdfReader(io.BytesIO(raw_pdf_bytes))
            writer = PdfWriter()
            writer.append(reader)
            # Remove creation and modification metadata
            writer.metadata = {}
            with open(pdf_path, "wb") as f_out:
                writer.write(f_out)
        else:
            with open(pdf_path, "wb") as f_out:
                f_out.write(raw_pdf_bytes)

        logger.info("Generated PDF report for run %s -> %s", run_id, pdf_path)
        return pdf_path

    except Exception as err:
        if isinstance(err, PdfGenerationError):
            raise
        logger.exception("Unexpected error generating PDF for run %s: %s", run_id, err)
        raise PdfGenerationError(
            f"PDF generation failed for run '{run_id}': {err}"
        ) from err


if __name__ == "__main__":
    import shutil
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m app.reports.pdf <run_id> <out_path>", file=sys.stderr)
        sys.exit(1)

    r_id = sys.argv[1]
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        gen_path = generate_pdf(r_id, output_dir=destination.parent)
        if gen_path != destination:
            shutil.copyfile(gen_path, destination)
        print(f"Successfully generated PDF report: {destination}")
        sys.exit(0)
    except Exception as exc:
        print(f"Failed to generate PDF for {r_id}: {exc}", file=sys.stderr)
        sys.exit(2)
