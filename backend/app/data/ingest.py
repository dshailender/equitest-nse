import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app.data.source import PriceSource, get_price_source
from app.db.models import IndexPrice, Price, UniverseMembership


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
            raise InvariantViolationError(f"Column '{col}' contains non-positive values")

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
        if not index_df.empty:
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

    # 3. Ingest Universe Membership if constituents fixture exists
    base = Path(__file__).resolve().parent.parent.parent.parent
    constituents_file = base / "data" / "fixtures" / "constituents.parquet"
    if constituents_file.exists():
        try:
            const_df = pd.read_parquet(constituents_file)
            if "date" in const_df.columns and "symbol" in const_df.columns and "rank" in const_df.columns:
                const_df["date"] = pd.to_datetime(const_df["date"]).dt.strftime("%Y-%m-%d")
                mask = (const_df["date"] >= start) & (const_df["date"] <= end)
                filtered_const = const_df[mask]

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

    return {
        "job_id": job_id,
        "status": "completed" if not errors else "partial",
        "symbols_ingested": symbols_ingested,
        "rows_ingested": rows_ingested,
        "errors": errors,
    }

