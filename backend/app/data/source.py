import io
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from app.core.config import get_fixtures_dir, get_repo_root, settings

logger = logging.getLogger(__name__)


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
            self.fixtures_dir = get_fixtures_dir()

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


class NSEIndiaSource(PriceSource):
    """Source fetching authentic NSE India bhavcopy data with local parquet caching.

    Includes resilient fallback to fixtures.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        fixtures_dir: Path | str | None = None,
    ):
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = get_repo_root() / "data" / "cache" / "nse"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if fixtures_dir:
            self.fixtures_dir = Path(fixtures_dir)
        else:
            self.fixtures_dir = get_fixtures_dir()

        self.csv_fallback = CSVSource(fixtures_dir=self.fixtures_dir)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self._network_reachable: bool | None = None

    def _fetch_bhavcopy_for_date(self, date_str: str) -> pd.DataFrame | None:
        """Fetch bhavcopy for single date (YYYY-MM-DD), caching as parquet."""
        try:
            dt = pd.to_datetime(date_str)
            clean_date = dt.strftime("%Y-%m-%d")
            ddmmyyyy = dt.strftime("%d%m%Y")
        except Exception:
            return None

        cached_file = self.cache_dir / f"bhav_{date_str}.parquet"
        if not cached_file.exists() and date_str != clean_date:
            cached_alt = self.cache_dir / f"bhav_{clean_date}.parquet"
            if cached_alt.exists():
                cached_file = cached_alt

        if cached_file.exists():
            try:
                return pd.read_parquet(cached_file)
            except Exception as e:
                logger.warning(f"Error reading cached bhavcopy {cached_file}: {e}")

        if self._network_reachable is False:
            return None

        url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                if resp.status_code in [401, 403, 500, 502, 503]:
                    self._network_reachable = False
                return None

            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = df.columns.str.strip()

            if "SERIES" in df.columns:
                df["SERIES"] = df["SERIES"].astype(str).str.strip()
                df = df[df["SERIES"].isin(["EQ", "BE", "GS"])]

            if "SYMBOL" in df.columns:
                df["symbol"] = df["SYMBOL"].astype(str).str.strip().str.upper()

            if "DATE1" in df.columns:
                df["date"] = (
                    pd.to_datetime(
                        df["DATE1"].astype(str).str.strip(),
                        format="mixed",
                        dayfirst=True,
                        errors="coerce",
                    )
                    .dt.strftime("%Y-%m-%d")
                    .fillna(clean_date)
                )
            else:
                df["date"] = clean_date

            if "OPEN_PRICE" in df.columns:
                df["open"] = pd.to_numeric(df["OPEN_PRICE"], errors="coerce")
            if "HIGH_PRICE" in df.columns:
                df["high"] = pd.to_numeric(df["HIGH_PRICE"], errors="coerce")
            if "LOW_PRICE" in df.columns:
                df["low"] = pd.to_numeric(df["LOW_PRICE"], errors="coerce")
            if "CLOSE_PRICE" in df.columns:
                df["close"] = pd.to_numeric(df["CLOSE_PRICE"], errors="coerce")
                df["adj_close"] = df["close"]
            if "TTL_TRD_QNTY" in df.columns:
                df["volume"] = pd.to_numeric(
                    df["TTL_TRD_QNTY"], errors="coerce"
                ).fillna(0)

            cols = [
                "date",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
            ]
            avail = [c for c in cols if c in df.columns]
            df = (
                df[avail]
                .dropna(subset=["date", "symbol", "close"])
                .reset_index(drop=True)
            )
            if not df.empty:
                save_file = self.cache_dir / f"bhav_{date_str}.parquet"
                df.to_parquet(save_file, index=False)
                if save_file != self.cache_dir / f"bhav_{clean_date}.parquet":
                    df.to_parquet(
                        self.cache_dir / f"bhav_{clean_date}.parquet", index=False
                    )
                return df
            return None
        except Exception as exc:
            self._network_reachable = False
            logger.warning(f"Failed fetching bhavcopy for {clean_date}: {exc}")
            return None

    def _fetch_index_for_date(self, date_str: str) -> pd.DataFrame | None:
        """Fetch index bhavcopy for single date (YYYY-MM-DD), caching as parquet."""
        try:
            dt = pd.to_datetime(date_str)
            clean_date = dt.strftime("%Y-%m-%d")
            ddmmyyyy = dt.strftime("%d%m%Y")
        except Exception:
            return None

        cached_file = self.cache_dir / f"index_{date_str}.parquet"
        if not cached_file.exists() and date_str != clean_date:
            cached_alt = self.cache_dir / f"index_{clean_date}.parquet"
            if cached_alt.exists():
                cached_file = cached_alt

        if cached_file.exists():
            try:
                return pd.read_parquet(cached_file)
            except Exception as e:
                logger.warning(f"Error reading cached index file {cached_file}: {e}")

        if self._network_reachable is False:
            return None

        url = f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{ddmmyyyy}.csv"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                if resp.status_code in [401, 403, 500, 502, 503]:
                    self._network_reachable = False
                return None

            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = df.columns.str.strip()

            rename_map = {
                "Index Name": "symbol",
                "Index Date": "date",
                "Open Index Value": "open",
                "High Index Value": "high",
                "Low Index Value": "low",
                "Closing Index Value": "close",
                "Volume": "volume",
            }
            df.rename(columns=rename_map, inplace=True)

            if "symbol" in df.columns:
                df["symbol"] = df["symbol"].astype(str).str.strip()

            if "date" in df.columns:
                df["date"] = (
                    pd.to_datetime(
                        df["date"].astype(str).str.strip(),
                        format="mixed",
                        dayfirst=True,
                        errors="coerce",
                    )
                    .dt.strftime("%Y-%m-%d")
                    .fillna(clean_date)
                )
            else:
                df["date"] = clean_date

            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col]
                        .astype(str)
                        .str.replace(",", "")
                        .str.replace("-", "0")
                        .str.strip(),
                        errors="coerce",
                    )

            if "adj_close" not in df.columns and "close" in df.columns:
                df["adj_close"] = df["close"]

            cols = [
                "date",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
            ]
            avail = [c for c in cols if c in df.columns]
            df = (
                df[avail]
                .dropna(subset=["date", "symbol", "close"])
                .reset_index(drop=True)
            )
            if not df.empty:
                save_file = self.cache_dir / f"index_{date_str}.parquet"
                df.to_parquet(save_file, index=False)
                if save_file != self.cache_dir / f"index_{clean_date}.parquet":
                    df.to_parquet(
                        self.cache_dir / f"index_{clean_date}.parquet", index=False
                    )
                return df
            return None
        except Exception as exc:
            self._network_reachable = False
            logger.warning(f"Failed fetching index data for {clean_date}: {exc}")
            return None

    def get_equity_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        clean_symbol = (
            symbol.replace("^", "")
            .replace(".NS", "")
            .replace(".BO", "")
            .strip()
            .upper()
        )

        fixture_candidates = [
            self.fixtures_dir / f"{symbol}.parquet",
            self.fixtures_dir / f"{clean_symbol}.parquet",
            self.fixtures_dir / "tiny_universe" / f"{symbol}.parquet",
            self.fixtures_dir / "tiny_universe" / f"{clean_symbol}.parquet",
        ]
        has_fixture = any(c.exists() for c in fixture_candidates)
        is_testing = (
            bool(os.environ.get("PYTEST_CURRENT_TEST"))
            or getattr(settings, "APP_ENV", None) == "testing"
        )
        is_offline = bool(os.environ.get("OFFLINE"))

        if (
            self._network_reachable is False or is_offline or is_testing
        ) and has_fixture:
            fix_df = self.csv_fallback.get_equity_prices(symbol, start, end)
            if not fix_df.empty:
                return fix_df

        records: list[pd.DataFrame] = []
        try:
            dates = pd.bdate_range(start, end)
        except Exception:
            dates = []

        consecutive_failures = 0
        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            bhav = self._fetch_bhavcopy_for_date(date_str)
            if bhav is not None and not bhav.empty:
                consecutive_failures = 0
                match = bhav[bhav["symbol"].str.upper() == clean_symbol]
                if not match.empty:
                    records.append(match)
            else:
                consecutive_failures += 1
                if consecutive_failures >= 3 and not records:
                    break

        if not records:
            fix_df = self.csv_fallback.get_equity_prices(symbol, start, end)
            if not fix_df.empty:
                return fix_df
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "adj_close", "volume"]
            )

        combined = pd.concat(records, ignore_index=True)
        cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        combined = combined[[c for c in cols if c in combined.columns]]
        combined.sort_values(by="date", ascending=True, inplace=True)
        combined.drop_duplicates(subset=["date"], inplace=True)
        return combined.reset_index(drop=True)

    def _normalize_index_symbol(self, symbol: str) -> str:
        s = symbol.strip().upper().replace("^", "")
        if s in ["NSEI", "NIFTY", "NIFTY50", "NIFTY_50", "NIFTY 50"]:
            return "Nifty 50"
        return symbol.strip()

    def get_index_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        norm_sym = self._normalize_index_symbol(symbol)

        fixture_candidates = [
            self.fixtures_dir / f"{symbol}.parquet",
            self.fixtures_dir / "^NSEI.parquet",
            self.fixtures_dir / "NIFTY50.parquet",
        ]
        has_fixture = any(c.exists() for c in fixture_candidates)
        is_testing = (
            bool(os.environ.get("PYTEST_CURRENT_TEST"))
            or getattr(settings, "APP_ENV", None) == "testing"
        )
        is_offline = bool(os.environ.get("OFFLINE"))

        if (
            self._network_reachable is False or is_offline or is_testing
        ) and has_fixture:
            fix_df = self.csv_fallback.get_index_prices(symbol, start, end)
            if not fix_df.empty:
                return fix_df

        records: list[pd.DataFrame] = []
        try:
            dates = pd.bdate_range(start, end)
        except Exception:
            dates = []

        consecutive_failures = 0
        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            idx_df = self._fetch_index_for_date(date_str)
            if idx_df is not None and not idx_df.empty:
                consecutive_failures = 0
                match = idx_df[idx_df["symbol"].str.upper() == norm_sym.upper()]
                if not match.empty:
                    records.append(match)
            else:
                consecutive_failures += 1
                if consecutive_failures >= 3 and not records:
                    break

        if not records:
            return self.csv_fallback.get_index_prices(symbol, start, end)

        combined = pd.concat(records, ignore_index=True)
        cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        combined = combined[[c for c in cols if c in combined.columns]]
        combined.sort_values(by="date", ascending=True, inplace=True)
        combined.drop_duplicates(subset=["date"], inplace=True)
        return combined.reset_index(drop=True)

    def get_coverage(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Inspect coverage for symbol from cache or fixtures.

        Returns symbol, first_date, last_date, rows.
        """
        if symbol:
            clean_sym = (
                symbol.replace("^", "")
                .replace(".NS", "")
                .replace(".BO", "")
                .strip()
                .upper()
            )
            cov = self.csv_fallback.get_coverage(symbol)
            if cov:
                return cov
            bhav_files = list(self.cache_dir.glob("bhav_*.parquet"))
            matching_dates = []
            for bf in sorted(bhav_files):
                try:
                    df = pd.read_parquet(bf)
                    if (
                        "symbol" in df.columns
                        and clean_sym in df["symbol"].str.upper().values
                    ):
                        matching_dates.append(bf.stem.replace("bhav_", ""))
                except Exception:
                    continue
            if matching_dates:
                return [
                    {
                        "symbol": clean_sym,
                        "first_date": matching_dates[0],
                        "last_date": matching_dates[-1],
                        "rows": len(matching_dates),
                    }
                ]
            return []

        return self.csv_fallback.get_coverage(None)


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

        try:
            df = yf.download(
                ticker,
                start=start,
                end=end,
                progress=False,
                auto_adjust=False,
            )

            if df.empty:
                return pd.DataFrame(
                    columns=[
                        "date",
                        "open",
                        "high",
                        "low",
                        "close",
                        "adj_close",
                        "volume",
                    ]
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
        except Exception as exc:
            logger.warning(f"Failed to fetch data from yfinance for {ticker}: {exc}")
            return pd.DataFrame(
                columns=["date", "open", "high", "low", "close", "adj_close", "volume"]
            )

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
        return CSVSource(fixtures_dir=get_fixtures_dir())
    if stype in ["NSE", "NSEINDIA", "BHAVCOPY"]:
        return NSEIndiaSource()
    if stype in ["YFINANCE", "YAHOO"]:
        return YFinanceSource()
    return NSEIndiaSource()
