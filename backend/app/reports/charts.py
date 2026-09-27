"""Pure-function chart rendering service for institutional PDF reports (REQ-9.3).

Provides deterministic server-side chart rendering for equity curves, underwater
drawdowns, and monthly return matrices using matplotlib's Agg backend.
"""

import os
from pathlib import Path

# Ensure headless Agg backend and writable matplotlib config
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

# Matplotlib styling constants for institutional appearance
PRIMARY_BLUE = "#1e40af"
ACCENT_BLUE = "#3b82f6"
DRAWDOWN_RED = "#dc2626"
DRAWDOWN_FILL = "#fecaca"
GRID_COLOR = "#e2e8f0"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
FONT_FAMILY = "sans-serif"


def _normalize_png_determinism(file_path: Path) -> Path:
    """Strips all variable PNG metadata and re-encodes raw pixel buffers.

    Guarantees bit-for-bit deterministic SHA-256 digests across repeated renders
    on identical input DataFrames.
    """
    with Image.open(file_path) as im:
        clean = Image.frombytes(im.mode, im.size, im.tobytes())
        clean.save(file_path, format="PNG", optimize=False)
    return file_path


def render_equity_curve(
    equity_df: pd.DataFrame,
    out_path: Path,
    width: int = 1200,
    height: int = 600,
    dpi: int = 150,
) -> Path:
    """Renders equity curve to PNG at specified resolution and DPI (REQ-9.3).

    Args:
        equity_df: DataFrame with 'date' and 'equity' columns.
        out_path: Output PNG file destination.
        width: Pixel width (default 1200).
        height: Pixel height (default 600).
        dpi: Dots per inch (default 150).

    Returns:
        Path to generated deterministic PNG image.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig_w = width / dpi
    fig_h = height / dpi

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    if (
        equity_df.empty
        or "date" not in equity_df.columns
        or "equity" not in equity_df.columns
    ):
        ax.text(
            0.5,
            0.5,
            "No Equity Data Available",
            ha="center",
            va="center",
            fontsize=14,
            color=TEXT_MUTED,
            fontfamily=FONT_FAMILY,
        )
    else:
        df = equity_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        dates = df["date"]
        equity = df["equity"].astype(float).values

        # Plot equity curve and gradient under-fill
        ax.plot(
            dates, equity, color=PRIMARY_BLUE, linewidth=2.0, label="Strategy Portfolio"
        )
        ax.fill_between(dates, equity, y2=equity.min(), color=ACCENT_BLUE, alpha=0.15)

        start_cap = float(equity[0])
        end_cap = float(equity[-1])
        start_date = dates.iloc[0]
        end_date = dates.iloc[-1]

        # Check for benchmark series or attempt to resolve (AUD-H-001)
        bench_dates = None
        bench_equity = None

        if "benchmark_equity" in df.columns and not df["benchmark_equity"].isna().all():
            bench_dates = dates
            bench_equity = df["benchmark_equity"].astype(float).values
        elif (
            "benchmark" in df.columns or "benchmark_close" in df.columns
        ) and not df.empty:
            b_col = "benchmark" if "benchmark" in df.columns else "benchmark_close"
            b_vals = df[b_col].astype(float).values
            if len(b_vals) > 0 and b_vals[0] > 0:
                bench_dates = dates
                bench_equity = start_cap * (b_vals / b_vals[0])
        else:
            try:
                from app.reports.metrics import resolve_benchmark_prices

                start_str = str(df["date"].iloc[0])[:10]
                end_str = str(df["date"].iloc[-1])[:10]
                b_df = resolve_benchmark_prices(start_str, end_str)
                if b_df is not None and not b_df.empty and "date" in b_df.columns:
                    b_sub = b_df.copy()
                    b_sub["date_str"] = b_sub["date"].astype(str).str[:10]
                    close_col = (
                        "close"
                        if "close" in b_sub.columns
                        else ("adj_close" if "adj_close" in b_sub.columns else None)
                    )
                    if close_col:
                        df_temp = df[["date"]].copy()
                        df_temp["date_str"] = df_temp["date"].dt.strftime("%Y-%m-%d")
                        merged = pd.merge(
                            df_temp,
                            b_sub[["date_str", close_col]],
                            on="date_str",
                            how="inner",
                        )
                        if len(merged) >= 2:
                            b_prices = merged[close_col].astype(float).values
                            if b_prices[0] > 0:
                                bench_dates = pd.to_datetime(merged["date_str"])
                                bench_equity = start_cap * (b_prices / b_prices[0])
            except Exception:
                pass

        # Plot overlaid benchmark curve if available
        if (
            bench_dates is not None
            and bench_equity is not None
            and len(bench_equity) > 0
        ):
            ax.plot(
                bench_dates,
                bench_equity,
                color="#d97706",
                linewidth=1.75,
                linestyle="--",
                label="Benchmark (NIFTY 50)",
            )
            ax.legend(
                loc="upper left",
                frameon=True,
                facecolor="#ffffff",
                edgecolor=GRID_COLOR,
                fontsize=9,
            )

        # Annotate Start & End Capital
        ax.plot(start_date, start_cap, marker="o", markersize=5, color=PRIMARY_BLUE)
        ax.annotate(
            f"Start: ₹{start_cap:,.2f}",
            xy=(start_date, start_cap),
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color=TEXT_DARK,
            fontfamily=FONT_FAMILY,
            bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec=GRID_COLOR, alpha=0.9),
        )

        ax.plot(end_date, end_cap, marker="o", markersize=5, color=PRIMARY_BLUE)
        ax.annotate(
            f"End: ₹{end_cap:,.2f}",
            xy=(end_date, end_cap),
            xytext=(-90, -15 if end_cap <= start_cap else 10),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color=PRIMARY_BLUE if end_cap >= start_cap else DRAWDOWN_RED,
            fontfamily=FONT_FAMILY,
            bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec=GRID_COLOR, alpha=0.9),
        )

        # Formatting axes
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))

    ax.set_title(
        "Portfolio Equity Curve",
        fontsize=13,
        fontweight="bold",
        color=TEXT_DARK,
        pad=12,
    )
    ax.set_xlabel("Date", fontsize=10, color=TEXT_MUTED, labelpad=8)
    ax.set_ylabel("Equity (INR)", fontsize=10, color=TEXT_MUTED, labelpad=8)
    ax.grid(True, linestyle="--", linewidth=0.7, color=GRID_COLOR, alpha=0.8)
    ax.tick_params(axis="both", which="major", labelsize=9, colors=TEXT_MUTED)

    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    plt.tight_layout()
    fig.savefig(
        out_path,
        format="png",
        dpi=dpi,
        metadata={"Software": None, "Creation Time": None},
    )
    plt.close(fig)

    return _normalize_png_determinism(out_path)


def render_drawdown(
    equity_df: pd.DataFrame,
    out_path: Path,
    width: int = 1200,
    height: int = 600,
    dpi: int = 150,
) -> Path:
    """Renders underwater drawdown curve to PNG at specified resolution and DPI.

    Covers REQ-9.3.

    Args:
        equity_df: DataFrame with 'date' and either 'drawdown_pct' or 'equity' column.
        out_path: Output PNG file destination.
        width: Pixel width (default 1200).
        height: Pixel height (default 600).
        dpi: Dots per inch (default 150).

    Returns:
        Path to generated deterministic PNG image.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig_w = width / dpi
    fig_h = height / dpi

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    if equity_df.empty or "date" not in equity_df.columns:
        ax.text(
            0.5,
            0.5,
            "No Drawdown Data Available",
            ha="center",
            va="center",
            fontsize=14,
            color=TEXT_MUTED,
            fontfamily=FONT_FAMILY,
        )
    else:
        df = equity_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        if "drawdown_pct" in df.columns:
            dd = df["drawdown_pct"].astype(float).values
        elif "equity" in df.columns:
            eq = df["equity"].astype(float).values
            peaks = np.maximum.accumulate(eq)
            dd = np.where(peaks > 0, (eq - peaks) / peaks, 0.0)
        else:
            dd = np.zeros(len(df))

        # Ensure drawdown values are expressed as percentages and non-positive
        # for display
        dd_pct = -np.abs(dd) if np.any(dd > 0) else dd
        dd_display = dd_pct * 100.0  # express as -X.X%

        dates = df["date"]

        ax.plot(dates, dd_display, color=DRAWDOWN_RED, linewidth=1.5, label="Drawdown")
        ax.fill_between(dates, dd_display, y2=0, color=DRAWDOWN_FILL, alpha=0.6)

        max_dd_idx = int(np.argmin(dd_display))
        max_dd_val = float(dd_display[max_dd_idx])
        max_dd_date = dates.iloc[max_dd_idx]

        ax.plot(max_dd_date, max_dd_val, marker="v", markersize=6, color=DRAWDOWN_RED)
        ax.annotate(
            f"Max DD: {max_dd_val:.2f}%",
            xy=(max_dd_date, max_dd_val),
            xytext=(10, -15),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color=DRAWDOWN_RED,
            fontfamily=FONT_FAMILY,
            bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec=GRID_COLOR, alpha=0.9),
        )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}%"))
        ax.set_ylim(top=0.5, bottom=min(max_dd_val * 1.15, -1.0))

    ax.set_title(
        "Underwater Portfolio Drawdown",
        fontsize=13,
        fontweight="bold",
        color=TEXT_DARK,
        pad=12,
    )
    ax.set_xlabel("Date", fontsize=10, color=TEXT_MUTED, labelpad=8)
    ax.set_ylabel("Drawdown %", fontsize=10, color=TEXT_MUTED, labelpad=8)
    ax.axhline(0, color=TEXT_MUTED, linewidth=0.8, linestyle="-")
    ax.grid(True, linestyle="--", linewidth=0.7, color=GRID_COLOR, alpha=0.8)
    ax.tick_params(axis="both", which="major", labelsize=9, colors=TEXT_MUTED)

    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    plt.tight_layout()
    fig.savefig(
        out_path,
        format="png",
        dpi=dpi,
        metadata={"Software": None, "Creation Time": None},
    )
    plt.close(fig)

    return _normalize_png_determinism(out_path)


def render_monthly_heatmap(
    monthly_df: pd.DataFrame,
    out_path: Path,
    width: int = 1200,
    height: int = 600,
    dpi: int = 150,
) -> Path:
    """Renders Month x Year compounded returns matrix heatmap (REQ-9.3).

    Args:
        monthly_df: DataFrame with monthly return columns (jan..dec) and
            year index/column.
        out_path: Output PNG file destination.
        width: Pixel width (default 1200).
        height: Pixel height (default 600).
        dpi: Dots per inch (default 150).

    Returns:
        Path to generated deterministic PNG image.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig_w = width / dpi
    fig_h = height / dpi

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    month_keys = [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    month_labels = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    if monthly_df.empty:
        ax.text(
            0.5,
            0.5,
            "No Monthly Data Available",
            ha="center",
            va="center",
            fontsize=14,
            color=TEXT_MUTED,
            fontfamily=FONT_FAMILY,
        )
    else:
        df = monthly_df.copy()
        if "year" in df.columns:
            df["year"] = df["year"].astype(int)
            df = df.set_index("year")
        df.columns = [str(c).lower() for c in df.columns]

        years = sorted(df.index.tolist())
        num_years = len(years)

        # Build matrix
        data = np.full((num_years, 12), np.nan)
        for i, yr in enumerate(years):
            for j, m in enumerate(month_keys):
                if m in df.columns:
                    val = df.loc[yr, m]
                    if pd.notna(val):
                        data[i, j] = float(val)

        # Plot cells
        for i, _yr in enumerate(years):
            for j in range(12):
                val = data[i, j]
                # Default empty/neutral cell
                if np.isnan(val):
                    bg_color = "#f8fafc"
                    txt_color = "#94a3b8"
                    txt = "—"
                else:
                    pct = val * 100.0
                    txt = f"{pct:+.1f}%" if abs(pct) >= 0.05 else f"{pct:.1f}%"
                    if val > 0:
                        intensity = min(abs(val) / 0.10, 1.0)
                        # Blend green
                        r = int(240 - intensity * (240 - 22))
                        g = int(253 - intensity * (253 - 101))
                        b = int(244 - intensity * (244 - 52))
                        bg_color = f"#{r:02x}{g:02x}{b:02x}"
                        txt_color = "#ffffff" if intensity > 0.65 else "#14532d"
                    elif val < 0:
                        intensity = min(abs(val) / 0.10, 1.0)
                        # Blend red
                        r = int(254 - intensity * (254 - 220))
                        g = int(242 - intensity * (242 - 38))
                        b = int(242 - intensity * (242 - 38))
                        bg_color = f"#{r:02x}{g:02x}{b:02x}"
                        txt_color = "#ffffff" if intensity > 0.65 else "#7f1d1d"
                    else:
                        bg_color = "#f1f5f9"
                        txt_color = "#475569"
                        txt = "0.0%"

                rect = plt.Rectangle(
                    (j, i),
                    1,
                    1,
                    facecolor=bg_color,
                    edgecolor="#cbd5e1",
                    linewidth=1.0,
                )
                ax.add_patch(rect)
                ax.text(
                    j + 0.5,
                    i + 0.5,
                    txt,
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    fontweight=(
                        "bold" if not np.isnan(val) and abs(val) > 0.02 else "normal"
                    ),
                    color=txt_color,
                    fontfamily=FONT_FAMILY,
                )

        ax.set_xlim(0, 12)
        ax.set_ylim(0, num_years)
        ax.set_xticks([j + 0.5 for j in range(12)])
        ax.set_xticklabels(month_labels, fontsize=9, fontweight="bold", color=TEXT_DARK)
        ax.set_yticks([i + 0.5 for i in range(num_years)])
        ax.set_yticklabels(
            [str(y) for y in years], fontsize=9, fontweight="bold", color=TEXT_DARK
        )
        ax.invert_yaxis()  # Top year is earliest

    ax.set_title(
        "Monthly Compounded Returns (%)",
        fontsize=13,
        fontweight="bold",
        color=TEXT_DARK,
        pad=12,
    )
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    plt.tight_layout()
    fig.savefig(
        out_path,
        format="png",
        dpi=dpi,
        metadata={"Software": None, "Creation Time": None},
    )
    plt.close(fig)

    return _normalize_png_determinism(out_path)
