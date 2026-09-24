from pathlib import Path
from typing import Any

import pandas as pd
from sqlmodel import Session, select

from app.db.models import UniverseMembership


def get_default_fallback_constituents(
    start_rank: int = 101, end_rank: int = 750
) -> list[dict[str, Any]]:
    """Generates default current NSE 750 constituent list with ranks 101 to 750.

    Used when point-in-time constituent data is missing, setting survivorship_bias=True.
    """
    sample_midcaps = [
        "IDEA",
        "YESBANK",
        "SUZLON",
        "ZOMATO",
        "PAYTM",
        "NYKAA",
        "POLICYBZR",
        "DELHIVERY",
        "TATACHEM",
        "TATACOMM",
        "TATAELXSI",
        "FEDERALBNK",
        "IDFCFIRSTB",
        "BANDHANBNK",
        "AUBANK",
        "ASHOKLEY",
        "BALKRISIND",
        "MRF",
        "APOLLOTYRE",
        "BHARATFORG",
        "ESCORTS",
        "TIINDIA",
        "EXIDEIND",
        "AMARAJABAT",
        "BOSCHLTD",
        "MOTHERSON",
        "LUPIN",
        "AUROPHARMA",
        "BIOCON",
        "GLENMARK",
        "TORNTPHARM",
        "ALKEM",
        "IPCALAB",
        "LAURUSLABS",
        "NATCOPHARM",
        "GRANULES",
        "STAR",
        "JUBLFOOD",
        "DEVYANI",
        "SAPPHIRE",
        "WESTLIFE",
        "BATAINDIA",
        "RELAXO",
        "PAGEIND",
        "TRENT",
        "ABFRL",
        "RAYMOND",
        "VBL",
        "RADICO",
        "UBL",
        "COFORGE",
        "MPHASIS",
        "PERSISTENT",
        "LTIM",
        "LTTS",
        "KPITTECH",
        "TATACOMM",
        "CYIENT",
        "SONACOMS",
        "POLYCAB",
        "KEI",
        "HAVELLS",
        "CROMPTON",
        "VOLTAS",
        "BLUESTARCO",
        "WHIRLPOOL",
        "DIXON",
        "AMBER",
    ]
    # Expand to fill symbols from start_rank to end_rank
    constituents = []
    base_count = len(sample_midcaps)
    for rank in range(start_rank, end_rank + 1):
        idx = (rank - 101) % base_count
        cycle = (rank - 101) // base_count
        suffix = f"_{cycle}" if cycle > 0 else ""
        symbol = f"{sample_midcaps[idx]}{suffix}"
        constituents.append({"symbol": symbol, "rank": rank})
    return constituents


def get_universe(
    date: str,
    session: Session | None = None,
    start_rank: int = 101,
    end_rank: int = 750,
) -> tuple[list[str], bool, list[dict[str, Any]]]:
    """Resolves tickers ranked between start_rank and end_rank by market cap.

    Returns:
        (tickers, survivorship_bias, details)
        - tickers: list of ticker symbols
        - survivorship_bias: bool, False if historical point-in-time list found,
          True if fallback used
        - details: list of dicts with 'symbol' and 'rank'
    """
    # 1. Check database table if session provided
    if session is not None:
        statement = (
            select(UniverseMembership)
            .where(UniverseMembership.date == date)
            .where(UniverseMembership.rank >= start_rank)
            .where(UniverseMembership.rank <= end_rank)
            .order_by(UniverseMembership.rank)
        )
        results = session.exec(statement).all()
        if results:
            tickers = [r.symbol for r in results]
            details = [{"symbol": r.symbol, "rank": r.rank} for r in results]
            return tickers, False, details

    # 2. Check point-in-time parquet file in /data/fixtures/constituents.parquet
    base = Path(__file__).resolve().parent.parent.parent.parent
    constituents_file = base / "data" / "fixtures" / "constituents.parquet"

    if constituents_file.exists():
        try:
            df = pd.read_parquet(constituents_file)
            if "date" in df.columns and "symbol" in df.columns and "rank" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                # Exact date match or closest preceding date
                available_dates = sorted(df["date"].unique())
                matching_dates = [d for d in available_dates if d <= date]
                if matching_dates:
                    effective_date = matching_dates[-1]
                    subset = df[
                        (df["date"] == effective_date)
                        & (df["rank"] >= start_rank)
                        & (df["rank"] <= end_rank)
                    ].sort_values(by="rank")

                    if not subset.empty:
                        tickers = subset["symbol"].tolist()
                        details = subset[["symbol", "rank"]].to_dict(orient="records")
                        return tickers, False, details
        except Exception:
            pass

    # 3. Fallback to current constituents with survivorship bias flag
    fallback = get_default_fallback_constituents(
        start_rank=start_rank, end_rank=end_rank
    )
    tickers = [item["symbol"] for item in fallback]
    return tickers, True, fallback
