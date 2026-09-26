from pathlib import Path
from typing import Any

import pandas as pd
from sqlmodel import Session, func, select

from app.data.constituents import AUTHENTIC_NSE_CONSTITUENTS
from app.db.models import UniverseMembership

COMPANY_METADATA: dict[str, dict[str, str]] = {
    "IDEA": {"name": "Vodafone Idea Ltd", "sector": "Telecommunication"},
    "YESBANK": {"name": "Yes Bank Ltd", "sector": "Financial Services"},
    "SUZLON": {"name": "Suzlon Energy Ltd", "sector": "Capital Goods"},
    "ZOMATO": {"name": "Zomato Ltd", "sector": "Consumer Services"},
    "PAYTM": {"name": "One97 Communications Ltd", "sector": "Financial Services"},
    "NYKAA": {"name": "FSN E-Commerce Ventures Ltd", "sector": "Consumer Services"},
    "POLICYBZR": {"name": "PB Fintech Ltd", "sector": "Financial Services"},
    "DELHIVERY": {"name": "Delhivery Ltd", "sector": "Services"},
    "TATACHEM": {"name": "Tata Chemicals Ltd", "sector": "Chemicals"},
    "TATACOMM": {"name": "Tata Communications Ltd", "sector": "Telecommunication"},
    "TATAELXSI": {"name": "Tata Elxsi Ltd", "sector": "Information Technology"},
    "FEDERALBNK": {"name": "Federal Bank Ltd", "sector": "Financial Services"},
    "IDFCFIRSTB": {"name": "IDFC First Bank Ltd", "sector": "Financial Services"},
    "BANDHANBNK": {"name": "Bandhan Bank Ltd", "sector": "Financial Services"},
    "AUBANK": {"name": "AU Small Finance Bank Ltd", "sector": "Financial Services"},
    "ASHOKLEY": {
        "name": "Ashok Leyland Ltd",
        "sector": "Automobile and Auto Components",
    },
    "BALKRISIND": {
        "name": "Balkrishna Industries Ltd",
        "sector": "Automobile and Auto Components",
    },
    "MRF": {"name": "MRF Ltd", "sector": "Automobile and Auto Components"},
    "APOLLOTYRE": {
        "name": "Apollo Tyres Ltd",
        "sector": "Automobile and Auto Components",
    },
    "BHARATFORG": {"name": "Bharat Forge Ltd", "sector": "Capital Goods"},
    "ESCORTS": {"name": "Escorts Kubota Ltd", "sector": "Capital Goods"},
    "TIINDIA": {
        "name": "Tube Investments of India Ltd",
        "sector": "Automobile and Auto Components",
    },
    "EXIDEIND": {
        "name": "Exide Industries Ltd",
        "sector": "Automobile and Auto Components",
    },
    "AMARAJABAT": {
        "name": "Amara Raja Energy & Mobility Ltd",
        "sector": "Automobile and Auto Components",
    },
    "BOSCHLTD": {"name": "Bosch Ltd", "sector": "Automobile and Auto Components"},
    "MOTHERSON": {
        "name": "Samvardhana Motherson International Ltd",
        "sector": "Automobile and Auto Components",
    },
    "LUPIN": {"name": "Lupin Ltd", "sector": "Healthcare"},
    "AUROPHARMA": {"name": "Aurobindo Pharma Ltd", "sector": "Healthcare"},
    "BIOCON": {"name": "Biocon Ltd", "sector": "Healthcare"},
    "GLENMARK": {"name": "Glenmark Pharmaceuticals Ltd", "sector": "Healthcare"},
    "TORNTPHARM": {"name": "Torrent Pharmaceuticals Ltd", "sector": "Healthcare"},
    "ALKEM": {"name": "Alkem Laboratories Ltd", "sector": "Healthcare"},
    "IPCALAB": {"name": "IPCA Laboratories Ltd", "sector": "Healthcare"},
    "LAURUSLABS": {"name": "Laurus Labs Ltd", "sector": "Healthcare"},
    "NATCOPHARM": {"name": "Natco Pharma Ltd", "sector": "Healthcare"},
    "GRANULES": {"name": "Granules India Ltd", "sector": "Healthcare"},
    "STAR": {"name": "Strides Pharma Science Ltd", "sector": "Healthcare"},
    "JUBLFOOD": {"name": "Jubilant FoodWorks Ltd", "sector": "Consumer Services"},
    "DEVYANI": {"name": "Devyani International Ltd", "sector": "Consumer Services"},
    "SAPPHIRE": {"name": "Sapphire Foods India Ltd", "sector": "Consumer Services"},
    "WESTLIFE": {"name": "Westlife Foodworld Ltd", "sector": "Consumer Services"},
    "BATAINDIA": {"name": "Bata India Ltd", "sector": "Consumer Durables"},
    "RELAXO": {"name": "Relaxo Footwears Ltd", "sector": "Consumer Durables"},
    "PAGEIND": {"name": "Page Industries Ltd", "sector": "Textiles"},
    "TRENT": {"name": "Trent Ltd", "sector": "Consumer Services"},
    "ABFRL": {
        "name": "Aditya Birla Fashion and Retail Ltd",
        "sector": "Consumer Services",
    },
    "RAYMOND": {"name": "Raymond Ltd", "sector": "Textiles"},
    "VBL": {"name": "Varun Beverages Ltd", "sector": "Fast Moving Consumer Goods"},
    "RADICO": {"name": "Radico Khaitan Ltd", "sector": "Fast Moving Consumer Goods"},
    "UBL": {"name": "United Breweries Ltd", "sector": "Fast Moving Consumer Goods"},
    "COFORGE": {"name": "Coforge Ltd", "sector": "Information Technology"},
    "MPHASIS": {"name": "Mphasis Ltd", "sector": "Information Technology"},
    "PERSISTENT": {
        "name": "Persistent Systems Ltd",
        "sector": "Information Technology",
    },
    "LTIM": {"name": "LTIMindtree Ltd", "sector": "Information Technology"},
    "LTTS": {"name": "L&T Technology Services Ltd", "sector": "Information Technology"},
    "KPITTECH": {"name": "KPIT Technologies Ltd", "sector": "Information Technology"},
    "CYIENT": {"name": "Cyient Ltd", "sector": "Information Technology"},
    "SONACOMS": {
        "name": "Sona BLW Precision Forgings Ltd",
        "sector": "Automobile and Auto Components",
    },
    "POLYCAB": {"name": "Polycab India Ltd", "sector": "Capital Goods"},
    "KEI": {"name": "KEI Industries Ltd", "sector": "Capital Goods"},
    "HAVELLS": {"name": "Havells India Ltd", "sector": "Consumer Durables"},
    "CROMPTON": {
        "name": "Crompton Greaves Consumer Electricals Ltd",
        "sector": "Consumer Durables",
    },
    "VOLTAS": {"name": "Voltas Ltd", "sector": "Consumer Durables"},
    "BLUESTARCO": {"name": "Blue Star Ltd", "sector": "Consumer Durables"},
    "WHIRLPOOL": {"name": "Whirlpool of India Ltd", "sector": "Consumer Durables"},
    "DIXON": {"name": "Dixon Technologies (India) Ltd", "sector": "Consumer Durables"},
    "AMBER": {"name": "Amber Enterprises India Ltd", "sector": "Consumer Durables"},
    "RELIANCE": {
        "name": "Reliance Industries Ltd",
        "sector": "Oil Gas & Consumable Fuels",
    },
    "TCS": {
        "name": "Tata Consultancy Services Ltd",
        "sector": "Information Technology",
    },
    "HDFCBANK": {"name": "HDFC Bank Ltd", "sector": "Financial Services"},
    "INFY": {"name": "Infosys Ltd", "sector": "Information Technology"},
    "ICICIBANK": {"name": "ICICI Bank Ltd", "sector": "Financial Services"},
    "HINDUNILVR": {
        "name": "Hindustan Unilever Ltd",
        "sector": "Fast Moving Consumer Goods",
    },
    "ITC": {"name": "ITC Ltd", "sector": "Fast Moving Consumer Goods"},
    "SBIN": {"name": "State Bank of India", "sector": "Financial Services"},
    "BHARTIARTL": {"name": "Bharti Airtel Ltd", "sector": "Telecommunication"},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank Ltd", "sector": "Financial Services"},
    "LT": {"name": "Larsen & Toubro Ltd", "sector": "Construction"},
    "AXISBANK": {"name": "Axis Bank Ltd", "sector": "Financial Services"},
}


_PARQUET_METADATA_CACHE: dict[str, dict[str, str]] | None = None


def _get_parquet_metadata() -> dict[str, dict[str, str]]:
    global _PARQUET_METADATA_CACHE
    if _PARQUET_METADATA_CACHE is not None:
        return _PARQUET_METADATA_CACHE
    cache: dict[str, dict[str, str]] = {}
    base = Path(__file__).resolve().parent.parent.parent.parent
    constituents_file = base / "data" / "fixtures" / "constituents.parquet"
    if constituents_file.exists():
        try:
            df = pd.read_parquet(constituents_file)
            if {"symbol", "name", "sector"}.issubset(df.columns):
                for _, r in df.iterrows():
                    s = str(r["symbol"]).strip().upper()
                    if s not in cache and pd.notna(r["name"]) and pd.notna(r["sector"]):
                        cache[s] = {"name": str(r["name"]), "sector": str(r["sector"])}
        except Exception:
            pass
    _PARQUET_METADATA_CACHE = cache
    return _PARQUET_METADATA_CACHE


def get_symbol_metadata(symbol: str) -> dict[str, str]:
    """Resolves human-readable name and sector for an equity ticker."""
    clean_sym = symbol.strip().upper()
    if clean_sym in COMPANY_METADATA:
        return dict(COMPANY_METADATA[clean_sym])

    pq_meta = _get_parquet_metadata()
    if clean_sym in pq_meta:
        return dict(pq_meta[clean_sym])

    # Check for synthetic / midcap stock patterns like MIDCAP_STOCK_101
    if clean_sym.startswith("MIDCAP_STOCK_"):
        suffix = clean_sym.replace("MIDCAP_STOCK_", "")
        return {
            "name": f"Midcap Stock {suffix} Ltd",
            "sector": "Midcap Equities",
        }

    # Handle cycle suffixes (e.g. IDEA_1, YESBANK_2)
    if "_" in clean_sym:
        base_sym, cycle = clean_sym.rsplit("_", 1)
        if base_sym in COMPANY_METADATA:
            base_meta = COMPANY_METADATA[base_sym]
            return {
                "name": f"{base_meta['name']} (Series {cycle})",
                "sector": base_meta["sector"],
            }
        if base_sym in pq_meta:
            base_meta = pq_meta[base_sym]
            return {
                "name": f"{base_meta['name']} (Series {cycle})",
                "sector": base_meta["sector"],
            }

    # Default fallback
    name = f"{clean_sym.replace('_', ' ').title()} Ltd"
    return {"name": name, "sector": "Diversified"}


# Representative midcap constituents for fallback & fixtures (AUD-B-003)
SAMPLE_MIDCAPS: list[str] = [
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
sample_midcaps: list[str] = SAMPLE_MIDCAPS


def get_default_fallback_constituents(
    start_rank: int = 101, end_rank: int = 750
) -> list[dict[str, Any]]:
    """Generates default current NSE constituent list with ranks 101 to 750.

    Used when point-in-time constituent data is missing, setting survivorship_bias=True.
    """
    constituents = []
    for rank in range(start_rank, end_rank + 1):
        idx = rank - 101
        if 0 <= idx < len(AUTHENTIC_NSE_CONSTITUENTS):
            symbol = AUTHENTIC_NSE_CONSTITUENTS[idx]
        else:
            symbol = f"NSE_STOCK_{rank}"
        meta = get_symbol_metadata(symbol)
        constituents.append(
            {
                "symbol": symbol,
                "name": meta["name"],
                "rank": rank,
                "sector": meta["sector"],
            }
        )
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
        - details: list of dicts with 'symbol', 'name', 'rank', and 'sector'
    """
    # 1. Check database table if session provided
    if session is not None:
        # Check for point-in-time constituent date (exact or closest preceding date)
        effective_date_stmt = select(func.max(UniverseMembership.date)).where(
            UniverseMembership.date <= date
        )
        effective_db_date = session.exec(effective_date_stmt).one_or_none()
        if effective_db_date is not None:
            statement = (
                select(UniverseMembership)
                .where(UniverseMembership.date == effective_db_date)
                .where(UniverseMembership.rank >= start_rank)
                .where(UniverseMembership.rank <= end_rank)
                .order_by(UniverseMembership.rank)
            )
            results = session.exec(statement).all()
            valid_results = [
                r
                for r in results
                if not r.symbol.startswith("MIDCAP_STOCK_")
                and not r.symbol.startswith("TOP_")
            ]
            if valid_results:
                tickers = [r.symbol for r in valid_results]
                details = [
                    {
                        "symbol": r.symbol,
                        "name": get_symbol_metadata(r.symbol)["name"],
                        "rank": r.rank,
                        "sector": get_symbol_metadata(r.symbol)["sector"],
                    }
                    for r in valid_results
                ]
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
                        details = [
                            {
                                "symbol": row["symbol"],
                                "name": (
                                    row["name"]
                                    if "name" in row and pd.notna(row["name"])
                                    else get_symbol_metadata(row["symbol"])["name"]
                                ),
                                "rank": int(row["rank"]),
                                "sector": (
                                    row["sector"]
                                    if "sector" in row and pd.notna(row["sector"])
                                    else get_symbol_metadata(row["symbol"])["sector"]
                                ),
                            }
                            for row in subset.to_dict(orient="records")
                        ]
                        return tickers, False, details
        except Exception:
            pass

    # 3. Fallback to current constituents with survivorship bias flag
    fallback = get_default_fallback_constituents(
        start_rank=start_rank, end_rank=end_rank
    )
    tickers = [item["symbol"] for item in fallback]
    return tickers, True, fallback
