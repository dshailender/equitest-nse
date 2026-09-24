"""Monthly returns aggregation matrix for EquiTest NSE (REQ-7.2)."""

from typing import Any

import pandas as pd

MONTH_KEYS = [
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


def compute_monthly_returns(equity_curve: pd.DataFrame) -> list[dict[str, Any]]:
    """Aggregates daily equity curve into a Month x Year compounded matrix.

    Args:
        equity_curve: DataFrame containing at least 'date' and 'equity' columns.

    Returns:
        List of dictionaries where each item represents one calendar year:
        {
            'year': int,
            'jan': float | None, ..., 'dec': float | None,
            'total': float
        }
    """
    if (
        equity_curve.empty
        or "date" not in equity_curve.columns
        or "equity" not in equity_curve.columns
    ):
        return []

    df = equity_curve[["date", "equity"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Compute daily percentage returns from equity
    eq = df["equity"].astype(float)
    df["daily_ret"] = eq.pct_change().fillna(0.0)

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    results: list[dict[str, Any]] = []

    for year, grp in df.groupby("year", sort=True):
        row: dict[str, Any] = {"year": int(year)}

        for m_idx in range(1, 13):
            month_key = MONTH_KEYS[m_idx - 1]
            m_sub = grp[grp["month"] == m_idx]
            if not m_sub.empty:
                # Compounded return across all sessions in this month
                m_ret = float((1.0 + m_sub["daily_ret"]).prod() - 1.0)
                row[month_key] = round(m_ret, 4)
            else:
                row[month_key] = None

        # Full year compounded return
        y_ret = float((1.0 + grp["daily_ret"]).prod() - 1.0)
        row["total"] = round(y_ret, 4)
        results.append(row)

    return results
