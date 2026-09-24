"""Multi-format export generator (CSV, XLSX, ZIP) for EquiTest NSE (REQ-7.3)."""

import io
import re
import xml.sax.saxutils as saxutils
import zipfile
from typing import Any
import pandas as pd

from app.reports.metrics import PerformanceMetrics


def generate_trades_csv(trades: pd.DataFrame) -> str:
    """Generates CSV string of executed round-trip trade ledger."""
    if trades.empty:
        cols = [
            "symbol",
            "entry_date",
            "entry_price",
            "qty",
            "exit_date",
            "exit_price",
            "pnl",
            "pnl_pct",
            "exit_reason",
            "days_held",
            "costs",
        ]
        return ",".join(cols) + "\n"

    out = io.StringIO()
    trades.to_csv(out, index=False)
    return out.getvalue()


def generate_equity_csv(equity_curve: pd.DataFrame) -> str:
    """Generates CSV string of daily mark-to-market equity curve."""
    if equity_curve.empty:
        cols = [
            "date",
            "equity",
            "cash",
            "positions_value",
            "open_positions",
            "daily_return",
            "drawdown",
            "drawdown_pct",
        ]
        return ",".join(cols) + "\n"

    out = io.StringIO()
    equity_curve.to_csv(out, index=False)
    return out.getvalue()


def generate_summary_csv(metrics: PerformanceMetrics) -> str:
    """Generates key-value CSV string of performance KPIs."""
    lines = ["metric,value,description"]
    data = [
        ("total_trades", metrics.total_trades, "Total completed round-trip trades"),
        ("win_trades", metrics.win_trades, "Number of profitable trades"),
        ("loss_trades", metrics.loss_trades, "Number of losing trades"),
        ("win_rate", metrics.win_rate, "Fraction of winning trades"),
        ("avg_profit", metrics.avg_profit, "Average profit of winning trades (INR)"),
        ("avg_loss", metrics.avg_loss, "Average loss of losing trades (INR)"),
        ("total_return_pct", metrics.total_return_pct, "Total return percentage"),
        ("initial_capital", metrics.initial_capital, "Starting corpus (INR)"),
        ("final_capital", metrics.final_capital, "Ending portfolio equity (INR)"),
        ("net_profit", metrics.net_profit, "Net profit (INR)"),
        ("cagr", metrics.cagr, "Compound Annual Growth Rate"),
        ("max_drawdown_pct", metrics.max_drawdown_pct, "Maximum percentage drawdown"),
        ("max_drawdown_amount", metrics.max_drawdown_amount, "Maximum monetary drawdown (INR)"),
        ("sharpe_ratio", metrics.sharpe_ratio, "Annualized Sharpe ratio (rf=0)"),
        ("sortino_ratio", metrics.sortino_ratio, "Annualized Sortino ratio (MAR=0)"),
        ("calmar_ratio", metrics.calmar_ratio, "Calmar ratio: CAGR / Max Drawdown"),
        ("profit_factor", metrics.profit_factor, "Gross Profit / Gross Loss"),
        ("expectancy", metrics.expectancy, "Average trade monetary expectancy (INR)"),
        ("avg_days_held", metrics.avg_days_held, "Average holding duration in days"),
    ]
    for key, val, desc in data:
        lines.append(f"{key},{val},\"{desc}\"")
    return "\n".join(lines) + "\n"


def generate_monthly_csv(monthly_matrix: list[dict[str, Any]]) -> str:
    """Generates CSV string of month x year returns matrix."""
    cols = ["year", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "total"]
    lines = [",".join(cols)]
    for row in monthly_matrix:
        row_vals = []
        for c in cols:
            v = row.get(c)
            row_vals.append("" if v is None else str(v))
        lines.append(",".join(row_vals))
    return "\n".join(lines) + "\n"


def generate_report_zip(
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    metrics: PerformanceMetrics,
    monthly_matrix: list[dict[str, Any]],
) -> bytes:
    """Creates in-memory ZIP bundle containing all 4 report CSV files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("summary.csv", generate_summary_csv(metrics).encode("utf-8"))
        zf.writestr("trades.csv", generate_trades_csv(trades).encode("utf-8"))
        zf.writestr("equity_curve.csv", generate_equity_csv(equity_curve).encode("utf-8"))
        zf.writestr("monthly_returns.csv", generate_monthly_csv(monthly_matrix).encode("utf-8"))
    return buf.getvalue()


def _col_idx_to_letter(idx: int) -> str:
    """Converts 0-indexed column integer to Excel column letters (0 -> A, 27 -> AB)."""
    result = ""
    idx += 1
    while idx > 0:
        idx, remainder = divmod(idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _rows_to_worksheet_xml(rows: list[list[Any]]) -> str:
    """Converts 2D list of row values into OpenXML worksheet XML."""
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>',
    ]
    for r_idx, row in enumerate(rows, start=1):
        cell_parts = []
        for c_idx, val in enumerate(row):
            if val is None or val == "":
                continue
            cell_ref = f"{_col_idx_to_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)):
                cell_parts.append(f'<c r="{cell_ref}"><v>{val}</v></c>')
            elif isinstance(val, bool):
                cell_parts.append(f'<c r="{cell_ref}" t="b"><v>{1 if val else 0}</v></c>')
            else:
                escaped = saxutils.escape(str(val))
                cell_parts.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        if cell_parts:
            xml_parts.append(f'<row r="{r_idx}">{"".join(cell_parts)}</row>')
    xml_parts.extend(["</sheetData>", "</worksheet>"])
    return "".join(xml_parts)


def generate_report_xlsx(
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    metrics: PerformanceMetrics,
    monthly_matrix: list[dict[str, Any]],
) -> bytes:
    """Generates multi-sheet Excel spreadsheet using standard OpenXML OPC container."""
    # Sheet 1: Summary
    summary_rows = [["Metric", "Value", "Description"]]
    summary_data = [
        ("Total Trades", metrics.total_trades, "Total completed round-trip trades"),
        ("Win Trades", metrics.win_trades, "Number of profitable trades"),
        ("Loss Trades", metrics.loss_trades, "Number of losing trades"),
        ("Win Rate", metrics.win_rate, "Fraction of winning trades"),
        ("Avg Profit (INR)", metrics.avg_profit, "Average profit of winning trades"),
        ("Avg Loss (INR)", metrics.avg_loss, "Average loss of losing trades"),
        ("Total Return (%)", metrics.total_return_pct, "Total return percentage"),
        ("Initial Capital (INR)", metrics.initial_capital, "Starting corpus"),
        ("Final Capital (INR)", metrics.final_capital, "Ending portfolio equity"),
        ("Net Profit (INR)", metrics.net_profit, "Net monetary gain/loss"),
        ("CAGR", metrics.cagr, "Compound Annual Growth Rate"),
        ("Max Drawdown (%)", metrics.max_drawdown_pct, "Maximum percentage drawdown"),
        ("Max Drawdown Amount (INR)", metrics.max_drawdown_amount, "Maximum monetary drawdown"),
        ("Sharpe Ratio (rf=0)", metrics.sharpe_ratio, "Annualized Sharpe ratio"),
        ("Sortino Ratio (MAR=0)", metrics.sortino_ratio, "Annualized Sortino ratio"),
        ("Calmar Ratio", metrics.calmar_ratio, "Calmar ratio: CAGR / Max Drawdown"),
        ("Profit Factor", metrics.profit_factor, "Gross Profit / Gross Loss"),
        ("Expectancy (INR)", metrics.expectancy, "Average trade monetary expectancy"),
        ("Avg Days Held", metrics.avg_days_held, "Average holding duration in days"),
    ]
    summary_rows.extend(list(summary_data))

    # Sheet 2: Trades
    trades_rows: list[list[Any]] = []
    if not trades.empty:
        trades_cols = list(trades.columns)
        trades_rows.append(trades_cols)
        for _, tr in trades.iterrows():
            trades_rows.append([tr[col] for col in trades_cols])
    else:
        trades_rows.append(["symbol", "entry_date", "entry_price", "qty", "exit_date", "exit_price", "pnl", "pnl_pct", "exit_reason", "days_held", "costs"])

    # Sheet 3: Equity Curve
    equity_rows: list[list[Any]] = []
    if not equity_curve.empty:
        eq_cols = list(equity_curve.columns)
        equity_rows.append(eq_cols)
        for _, eq in equity_curve.iterrows():
            equity_rows.append([eq[col] for col in eq_cols])
    else:
        equity_rows.append(["date", "equity", "cash", "positions_value", "open_positions", "daily_return", "drawdown", "drawdown_pct"])

    # Sheet 4: Monthly Returns
    monthly_cols = ["Year", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total (YTD)"]
    raw_keys = ["year", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "total"]
    monthly_rows: list[list[Any]] = [monthly_cols]
    for row in monthly_matrix:
        monthly_rows.append([row.get(k) for k in raw_keys])

    sheets = [
        ("Summary", summary_rows),
        ("Trades", trades_rows),
        ("Equity Curve", equity_rows),
        ("Monthly Returns", monthly_rows),
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. [Content_Types].xml
        ct_xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        ]
        for i in range(1, len(sheets) + 1):
            ct_xml.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        ct_xml.append("</Types>")
        zf.writestr("[Content_Types].xml", "".join(ct_xml).encode("utf-8"))

        # 2. _rels/.rels
        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )
        zf.writestr("_rels/.rels", rels_xml.encode("utf-8"))

        # 3. xl/_rels/workbook.xml.rels
        wb_rels_parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        ]
        for i in range(1, len(sheets) + 1):
            wb_rels_parts.append(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            )
        wb_rels_parts.append("</Relationships>")
        zf.writestr("xl/_rels/workbook.xml.rels", "".join(wb_rels_parts).encode("utf-8"))

        # 4. xl/workbook.xml
        wb_xml_parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
            '<sheets>',
        ]
        for i, (name, _) in enumerate(sheets, start=1):
            safe_name = re.sub(r'[\:\\\/\?\*\[\]]', "_", name)[:31]
            wb_xml_parts.append(f'<sheet name="{safe_name}" sheetId="{i}" r:id="rId{i}"/>')
        wb_xml_parts.extend(["</sheets>", "</workbook>"])
        zf.writestr("xl/workbook.xml", "".join(wb_xml_parts).encode("utf-8"))

        # 5. Worksheets
        for i, (_, row_data) in enumerate(sheets, start=1):
            sheet_content = _rows_to_worksheet_xml(row_data)
            zf.writestr(f"xl/worksheets/sheet{i}.xml", sheet_content.encode("utf-8"))

    return buf.getvalue()
