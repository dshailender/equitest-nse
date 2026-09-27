import logging
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app.core.config import get_fixtures_dir
from app.data.source import PriceSource, get_price_source
from app.db.models import IndexPrice, Price, UniverseMembership

logger = logging.getLogger(__name__)


class InvariantViolationError(ValueError):
    """Raised when an OHLCV invariant is violated."""

    pass


def validate_ohlcv_dataframe(df: pd.DataFrame) -> None:
    """Validates required OHLCV properties and financial data integrity invariants.

    Invariants:
    1. Monotonic strictly ascending dates with no duplicate dates.
    2. No NaN or Infinite values in open, high, low, close, adj_close.
    3. High >= Low for every session.
    4. High >= Open and High >= Close (high is session maximum).
    5. Low <= Open and Low <= Close (low is session minimum).
    6. Adjusted close present, positive, and non-null.
    7. Volume non-negative.
    """
    if df.empty:
        return

    required_cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise InvariantViolationError(f"Missing required OHLCV columns: {missing}")

    # 1. Monotonic dates check
    dates = pd.to_datetime(df["date"])
    if not dates.is_monotonic_increasing:
        raise InvariantViolationError("Dates must be strictly monotonic increasing")
    if dates.duplicated().any():
        raise InvariantViolationError("Duplicate dates found in series")

    # 2. NaN / Inf check
    price_cols = ["open", "high", "low", "close", "adj_close"]
    for col in price_cols:
        if df[col].isna().any():
            raise InvariantViolationError(f"Column '{col}' contains NaN values")
        if np.isinf(df[col]).any():
            raise InvariantViolationError(f"Column '{col}' contains Infinite values")
        if (df[col] <= 0).any():
            raise InvariantViolationError(
                f"Column '{col}' contains non-positive values"
            )

    # 3. High >= Low invariant
    if (df["high"] < df["low"]).any():
        raise InvariantViolationError("Invariant violated: high must be >= low")

    # 4. High >= Open and High >= Close
    if (df["high"] < df["open"]).any() or (df["high"] < df["close"]).any():
        raise InvariantViolationError(
            "Invariant violated: high must be >= open and close"
        )

    # 5. Low <= Open and Low <= Close
    if (df["low"] > df["open"]).any() or (df["low"] > df["close"]).any():
        raise InvariantViolationError(
            "Invariant violated: low must be <= open and close"
        )

    # 6. Volume non-negative
    if (df["volume"] < 0).any():
        raise InvariantViolationError("Invariant violated: volume must be >= 0")


def ingest_market_data(
    session: Session,
    start: str,
    end: str,
    symbols: list[str] | None = None,
    source: PriceSource | None = None,
) -> dict[str, Any]:
    """Ingests equity and index OHLCV prices into the database idempotently.

    Re-running for the same date range is a no-op for existing rows.
    """
    job_id = str(uuid.uuid4())
    price_source = source or get_price_source()

    if not symbols:
        # Default symbols for initial ingestion / dev
        symbols = ["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS"]

    symbols_ingested = 0
    rows_ingested = 0
    errors: list[str] = []

    # 1. Ingest Equities
    for sym in symbols:
        try:
            df = price_source.get_equity_prices(sym, start, end)
            if df.empty:
                msg = f"No price data available for symbol '{sym}' from source '{price_source.__class__.__name__}' (date range: {start} to {end})"
                logger.warning(msg)
                errors.append(msg)
                continue

            validate_ohlcv_dataframe(df)

            # Query existing dates for this symbol to ensure idempotency
            existing_stmt = select(Price.date).where(Price.symbol == sym)
            existing_dates = set(session.exec(existing_stmt).all())

            new_rows = []
            for _, row in df.iterrows():
                d = str(row["date"])
                if d in existing_dates:
                    continue
                new_rows.append(
                    Price(
                        symbol=sym,
                        date=d,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        adj_close=float(row["adj_close"]),
                        volume=float(row["volume"]),
                    )
                )

            if new_rows:
                session.add_all(new_rows)
                session.commit()
                rows_ingested += len(new_rows)

            symbols_ingested += 1
        except Exception as exc:
            errors.append(f"Failed ingesting symbol {sym}: {exc}")

    # 2. Ingest Benchmark Index (^NSEI / NIFTY50)
    index_symbol = "^NSEI"
    try:
        index_df = price_source.get_index_prices(index_symbol, start, end)
        if index_df.empty:
            msg = f"No price data available for benchmark index '{index_symbol}' from source '{price_source.__class__.__name__}' (date range: {start} to {end})"
            logger.warning(msg)
            errors.append(msg)
        else:
            validate_ohlcv_dataframe(index_df)

            existing_idx_stmt = select(IndexPrice.date).where(
                IndexPrice.symbol == index_symbol
            )
            existing_idx_dates = set(session.exec(existing_idx_stmt).all())

            new_idx_rows = []
            for _, row in index_df.iterrows():
                d = str(row["date"])
                if d in existing_idx_dates:
                    continue
                new_idx_rows.append(
                    IndexPrice(
                        symbol=index_symbol,
                        date=d,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        adj_close=float(row["adj_close"]),
                        volume=float(row["volume"]),
                    )
                )

            if new_idx_rows:
                session.add_all(new_idx_rows)
                session.commit()
                rows_ingested += len(new_idx_rows)
    except Exception as exc:
        errors.append(f"Failed ingesting index {index_symbol}: {exc}")

    # 3. Ingest Universe Membership if constituents fixture exists (or generate from code)
    fixtures_dir = get_fixtures_dir()
    constituents_file = fixtures_dir / "constituents.parquet"
    try:
        if constituents_file.exists():
            const_df = pd.read_parquet(constituents_file)
        else:
            from app.data.generate_fixtures import generate_constituents

            const_df = generate_constituents()

        cols = {"date", "symbol", "rank"}
        if cols.issubset(const_df.columns):
            const_df["date"] = pd.to_datetime(const_df["date"]).dt.strftime(
                "%Y-%m-%d"
            )
            mask = (const_df["date"] >= start) & (const_df["date"] <= end)
            filtered_const = const_df[mask]

            # Purge any legacy synthetic rows for matching dates
            matching_dates = sorted(filtered_const["date"].unique())
            if matching_dates:
                from sqlalchemy import text

                dates_str = ", ".join(f"'{d}'" for d in matching_dates)
                session.execute(
                    text(
                        f"DELETE FROM universe_membership "
                        f"WHERE date IN ({dates_str}) "
                        f"AND (symbol LIKE 'MIDCAP_STOCK_%' OR symbol LIKE 'TOP_%')"
                    )
                )

            for _, r in filtered_const.iterrows():
                d = str(r["date"])
                s = str(r["symbol"])
                existing = session.get(UniverseMembership, (d, s))
                if not existing:
                    session.add(
                        UniverseMembership(date=d, symbol=s, rank=int(r["rank"]))
                    )
            session.commit()
    except Exception as exc:
        errors.append(f"Failed ingesting universe constituents: {exc}")

    if rows_ingested > 0 and not errors:
        status = "completed"
    elif rows_ingested > 0 and errors:
        status = "partial"
    elif rows_ingested == 0 and errors:
        status = "failed"
    else:
        status = "completed"

    return {
        "job_id": job_id,
        "status": status,
        "symbols_ingested": symbols_ingested,
        "rows_ingested": rows_ingested,
        "errors": errors,
    }


def seed_price_coverage(raw_conn: Any = None) -> int:
    """Seeds SQLite database with 15+ years of continuous OHLCV data.

    Covers 2008-01-01 to 2024-01-01 (16 calendar years, 4,175 sessions per symbol).
    Adheres strictly to all financial OHLCV invariants (high >= low, monotonic).
    """

    from app.data.constituents import AUTHENTIC_NSE_CONSTITUENTS

    symbols = [
        "RELIANCE",
        "HDFCBANK",
        "INFY",
        "TATAMOTORS",
        "MIDCAP_STOCK_101",
    ] + AUTHENTIC_NSE_CONSTITUENTS
    unique_symbols = list(dict.fromkeys(symbols))

    dates = (
        pd.date_range("2008-01-01", "2024-01-01", freq="B")
        .strftime("%Y-%m-%d")
        .tolist()
    )
    n = len(dates)

    should_close = False
    if raw_conn is None:
        from app.db.session import engine

        raw_conn = engine.raw_connection()
        should_close = True

    cursor = raw_conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    try:
        cursor.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass

    fixtures_dir = get_fixtures_dir()

    for idx, sym in enumerate(unique_symbols):
        parquet_candidate = fixtures_dir / f"{sym}.parquet"
        if parquet_candidate.exists():
            fix_df = pd.read_parquet(parquet_candidate)
            fix_first_date = str(fix_df["date"].iloc[0])
            pre_rows = []
            if fix_first_date > "2008-01-01":
                pre_dates = (
                    pd.date_range(
                        "2008-01-01",
                        pd.to_datetime(fix_first_date) - pd.Timedelta(days=1),
                        freq="B",
                    )
                    .strftime("%Y-%m-%d")
                    .tolist()
                )
                if pre_dates:
                    n_pre = len(pre_dates)
                    np.random.seed(idx + 100)
                    returns = np.random.normal(loc=0.0002, scale=0.012, size=n_pre)
                    factors = np.cumprod(1 + returns[::-1])[::-1]
                    first_p = float(fix_df["close"].iloc[0])
                    first_adj = (
                        float(fix_df["adj_close"].iloc[0])
                        if "adj_close" in fix_df.columns
                        else first_p
                    )
                    pre_close = np.round(first_p / factors, 2)
                    pre_adj = np.round(first_adj / factors, 2)
                    pre_open = np.round(pre_close * 0.999, 2)
                    pre_high = np.round(np.maximum(pre_open, pre_close) * 1.01, 2)
                    pre_low = np.round(np.minimum(pre_open, pre_close) * 0.99, 2)
                    pre_rows = [
                        (
                            sym,
                            pre_dates[i],
                            float(pre_open[i]),
                            float(pre_high[i]),
                            float(pre_low[i]),
                            float(pre_close[i]),
                            float(pre_adj[i]),
                            500000.0,
                        )
                        for i in range(n_pre)
                    ]

            post_rows = [
                (
                    sym,
                    str(r["date"]),
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    float(r.get("adj_close", r["close"])),
                    float(r.get("volume", 500000.0)),
                )
                for _, r in fix_df.iterrows()
            ]
            rows = pre_rows + post_rows
        else:
            np.random.seed(idx + 100)
            returns = np.random.normal(loc=0.0004, scale=0.015, size=n)
            price_factors = np.cumprod(1 + returns)
            base_p = 100.0 + float((idx * 37) % 500)
            close = np.round(base_p * price_factors, 2)
            adj = close

            open_p = np.round(close * 0.999, 2)
            high = np.round(np.maximum(open_p, close) * 1.01, 2)
            low = np.round(np.minimum(open_p, close) * 0.99, 2)
            volume = 500000.0

            rows = [
                (
                    sym,
                    dates[i],
                    float(open_p[i]),
                    float(high[i]),
                    float(low[i]),
                    float(close[i]),
                    float(adj[i]),
                    volume,
                )
                for i in range(n)
            ]
        cursor.executemany(
            "INSERT OR REPLACE INTO prices "
            "(symbol, date, open, high, low, close, adj_close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    raw_conn.commit()
    if should_close:
        raw_conn.close()
    return len(unique_symbols)


def seed_universe_constituents(raw_conn: Any = None) -> int:
    """Seeds SQLite database with authentic point-in-time universe constituents.

    Purges any legacy synthetic constituents (MIDCAP_STOCK_*, TOP_*) and populates
    all records from data/fixtures/constituents.parquet.
    """
    should_close = False
    if raw_conn is None:
        from app.db.session import engine

        raw_conn = engine.raw_connection()
        should_close = True
    elif hasattr(raw_conn, "connection"):
        raw_conn = raw_conn.connection

    cursor = raw_conn.cursor()
    # 1. Purge legacy synthetic records
    cursor.execute(
        "DELETE FROM universe_membership "
        "WHERE symbol LIKE 'MIDCAP_STOCK_%' OR symbol LIKE 'TOP_%'"
    )

    # 2. Load constituents from parquet or generate if fixture does not exist
    fixtures_dir = get_fixtures_dir()
    constituents_file = fixtures_dir / "constituents.parquet"
    inserted = 0
    if constituents_file.exists():
        df = pd.read_parquet(constituents_file)
    else:
        from app.data.generate_fixtures import generate_constituents

        df = generate_constituents()

    if {"date", "symbol", "rank"}.issubset(df.columns):
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        rows = [
            (str(r["date"]), str(r["symbol"]), int(r["rank"]))
            for _, r in df.iterrows()
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO universe_membership (date, symbol, rank) "
            "VALUES (?, ?, ?)",
            rows,
        )
        inserted = len(rows)

    raw_conn.commit()
    if should_close:
        raw_conn.close()
    return inserted
