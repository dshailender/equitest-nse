from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import settings


class PriceSource(ABC):
    """Abstract interface for fetching equity and index OHLCV price series."""

    @abstractmethod
    def get_equity_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch equity prices for the given symbol and date range [start, end].

        Returns DataFrame with columns:
        ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        """
        pass

    @abstractmethod
    def get_index_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch benchmark index prices for the given symbol and range [start, end].

        Returns DataFrame with columns:
        ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        """
        pass

    @abstractmethod
    def get_coverage(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Inspect available historical date ranges and session counts.

        Returns a list of dicts with keys:
        ['symbol', 'first_date', 'last_date', 'rows']
        """
        pass


class CSVSource(PriceSource):
    """Source reading parquet fixtures from /data/fixtures/*.parquet."""

    def __init__(self, fixtures_dir: Path | str | None = None):
        if fixtures_dir:
            self.fixtures_dir = Path(fixtures_dir)
        else:
            # Locate root /data/fixtures relative to backend
            base = Path(__file__).resolve().parent.parent.parent.parent
            self.fixtures_dir = base / "data" / "fixtures"

    def _load_parquet(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        # Normalize symbol name for file lookup (strip ^ and .NS if present)
        clean_symbol = symbol.replace("^", "").replace(".NS", "").upper()
        candidates = [
            self.fixtures_dir / f"{symbol}.parquet",
            self.fixtures_dir / f"{clean_symbol}.parquet",
            self.fixtures_dir / f"index_{clean_symbol}.parquet",
            self.fixtures_dir / "tiny_universe" / f"{symbol}.parquet",
            self.fixtures_dir / "tiny_universe" / f"{clean_symbol}.parquet",
        ]

        target_file = None
        for candidate in candidates:
            if candidate.exists():
                target_file = candidate
                break

        if not target_file:
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "adj_close", "volume"]
            )

        df = pd.read_parquet(target_file)

        # Standardize column names to lowercase with underscores
        df.columns = [
            c.lower().replace(" ", "_").replace("adj_close", "adj_close")
            for c in df.columns
        ]

        # Handle index if date is in index
        if "date" not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                df.rename(columns={df.columns[0]: "date"}, inplace=True)
            elif "index" in df.columns:
                df.rename(columns={"index": "date"}, inplace=True)

        # Ensure date format is YYYY-MM-DD
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # Fallback for adj_close if missing
        if "adj_close" not in df.columns and "close" in df.columns:
            df["adj_close"] = df["close"]

        required_cols = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
        ]
        available_cols = [c for c in required_cols if c in df.columns]
        df = df[available_cols]

        # Filter by date range
        mask = (df["date"] >= start) & (df["date"] <= end)
        filtered = df[mask].copy()
        filtered.sort_values(by="date", ascending=True, inplace=True)
        return filtered.reset_index(drop=True)

    def get_equity_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return self._load_parquet(symbol, start, end)

    def get_index_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return self._load_parquet(symbol, start, end)

    def get_coverage(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Inspect date ranges and session counts from parquet fixtures."""
        if symbol:
            df = self._load_parquet(symbol, "1970-01-01", "2099-12-31")
            if df.empty:
                return []
            return [
                {
                    "symbol": symbol.upper(),
                    "first_date": str(df["date"].min()),
                    "last_date": str(df["date"].max()),
                    "rows": int(len(df)),
                }
            ]

        if not self.fixtures_dir.exists():
            return []

        results: list[dict[str, Any]] = []
        seen_symbols: set[str] = set()
        files = list(self.fixtures_dir.glob("*.parquet"))
        tiny_dir = self.fixtures_dir / "tiny_universe"
        if tiny_dir.is_dir():
            files.extend(tiny_dir.glob("*.parquet"))

        for p in sorted(files, key=lambda f: f.name):
            stem = p.stem.upper()
            if stem == "CONSTITUENTS" or stem in seen_symbols:
                continue
            df = self._load_parquet(p.stem, "1970-01-01", "2099-12-31")
            if not df.empty:
                seen_symbols.add(stem)
                results.append(
                    {
                        "symbol": stem,
                        "first_date": str(df["date"].min()),
                        "last_date": str(df["date"].max()),
                        "rows": int(len(df)),
                    }
                )
        return results


class YFinanceSource(PriceSource):
    """Source fetching live or historical data from Yahoo Finance."""

    def _normalize_ticker(self, symbol: str, is_index: bool = False) -> str:
        s = symbol.strip().upper()
        if is_index:
            if s in ["NIFTY", "NIFTY50", "NIFTY_50", "^NSEI"]:
                return "^NSEI"
            return s if s.startswith("^") else f"^{s}"
        else:
            if s.endswith(".NS") or s.endswith(".BO"):
                return s
            return f"{s}.NS"

    def _fetch_from_yfinance(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        import yfinance as yf

        df = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
        )

        if df.empty:
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "adj_close", "volume"]
            )

        # Handle MultiIndex columns if returned
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        # Rename columns to standard schema
        rename_map = {
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
        df.rename(columns=rename_map, inplace=True)

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        if "adj_close" not in df.columns and "close" in df.columns:
            df["adj_close"] = df["close"]

        cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        existing = [c for c in cols if c in df.columns]
        df = df[existing].sort_values(by="date", ascending=True)
        return df.reset_index(drop=True)

    def get_equity_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        ticker = self._normalize_ticker(symbol, is_index=False)
        return self._fetch_from_yfinance(ticker, start, end)

    def get_index_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        ticker = self._normalize_ticker(symbol, is_index=True)
        return self._fetch_from_yfinance(ticker, start, end)

    def get_coverage(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Inspect date ranges and session counts from Yahoo Finance."""
        if not symbol:
            return []

        try:
            df = self.get_equity_prices(symbol, "1970-01-01", "2099-12-31")
            if df.empty:
                df = self.get_index_prices(symbol, "1970-01-01", "2099-12-31")
            if df.empty:
                return []
            return [
                {
                    "symbol": symbol.upper(),
                    "first_date": str(df["date"].min()),
                    "last_date": str(df["date"].max()),
                    "rows": int(len(df)),
                }
            ]
        except Exception:
            return []


def get_price_source(source_type: str | None = None) -> PriceSource:
    """Factory returning configured PriceSource instance."""
    stype = (source_type or settings.DATA_SOURCE).strip().upper()
    if stype in ["CSV", "PARQUET", "FIXTURE", "FIXTURES"]:
        return CSVSource()
    return YFinanceSource()
