"""Tests for NSE India data source ingestion provider (NSE India Provider)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from app.core.config import Settings, get_fixtures_dir, get_repo_root
from app.data.source import (
    CSVSource,
    NSEIndiaSource,
    YFinanceSource,
    get_price_source,
)


def test_nse_source_initialization(tmp_path):
    """Verify NSEIndiaSource initializes with custom and default paths and headers."""
    cache_dir = tmp_path / "custom_cache"
    fixtures_dir = tmp_path / "custom_fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    source = NSEIndiaSource(cache_dir=cache_dir, fixtures_dir=fixtures_dir)
    assert source.cache_dir == cache_dir
    assert source.fixtures_dir == fixtures_dir
    assert cache_dir.exists()

    # Verify HTTP/1.1 base headers
    assert "User-Agent" in source.headers
    assert "Chrome" in source.headers["User-Agent"]
    assert "Accept" in source.headers
    assert "Accept-Language" in source.headers

    # Default constructor
    default_source = NSEIndiaSource()
    assert default_source.cache_dir == get_repo_root() / "data" / "cache" / "nse"
    assert default_source.fixtures_dir == get_fixtures_dir()
    assert default_source.cache_dir.exists()


def test_nse_source_date_formatting(tmp_path):
    """Verify _fetch_bhavcopy_for_date converts YYYY-MM-DD to ddmmyyyy."""
    source = NSEIndiaSource(cache_dir=tmp_path / "cache")

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 404

        source._fetch_bhavcopy_for_date("2024-01-05")
        mock_get.assert_called_with(
            "https://nsearchives.nseindia.com/products/content/"
            "sec_bhavdata_full_05012024.csv",
            headers=source.headers,
            timeout=10,
        )

    # Reset network status for index test
    source._network_reachable = None
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 404

        source._fetch_index_for_date("2024-01-05")
        mock_get.assert_called_with(
            "https://nsearchives.nseindia.com/content/indices/"
            "ind_close_all_05012024.csv",
            headers=source.headers,
            timeout=10,
        )


def test_nse_source_bhavcopy_csv_parsing_and_caching(tmp_path):
    """Verify bhavcopy CSV parsing, series filtering, and parquet caching."""
    cache_dir = tmp_path / "cache"
    source = NSEIndiaSource(cache_dir=cache_dir)

    raw_csv = (
        " SYMBOL , SERIES , DATE1 , OPEN_PRICE , HIGH_PRICE , LOW_PRICE , "
        "CLOSE_PRICE , TTL_TRD_QNTY \n"
        "RELIANCE , EQ , 05-Jan-2024 , 2600.00 , 2620.00 , 2590.00 , "
        "2610.50 , 1500000 \n"
        "HDFCBANK , EQ , 05-Jan-2024 , 1650.00 , 1670.00 , 1640.00 , "
        "1665.00 , 2000000 \n"
        "RELIANCE , IL , 05-Jan-2024 , 2605.00 , 2625.00 , 2595.00 , "
        "2615.00 , 50000 \n"
        "TCS , BE , 05-Jan-2024 , 3800.00 , 3850.00 , 3790.00 , "
        "3820.00 , 800000 \n"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = raw_csv

    with patch("requests.get", return_value=mock_resp):
        df = source._fetch_bhavcopy_for_date("2024-01-05")

    assert df is not None
    assert len(df) == 3  # EQ (RELIANCE, HDFCBANK) and BE (TCS), excluding IL
    assert "RELIANCE" in df["symbol"].values
    assert "HDFCBANK" in df["symbol"].values
    assert "TCS" in df["symbol"].values

    rel = df[df["symbol"] == "RELIANCE"].iloc[0]
    assert rel["date"] == "2024-01-05"
    assert rel["open"] == 2600.00
    assert rel["high"] == 2620.00
    assert rel["low"] == 2590.00
    assert rel["close"] == 2610.50
    assert rel["adj_close"] == 2610.50
    assert rel["volume"] == 1500000.0

    # Verify cached parquet file was written
    cached_file = cache_dir / "bhav_2024-01-05.parquet"
    assert cached_file.exists()

    # Second call should load from cache without making network request
    with patch("requests.get") as mock_get:
        cached_df = source._fetch_bhavcopy_for_date("2024-01-05")
        mock_get.assert_not_called()
        assert cached_df is not None
        assert len(cached_df) == 3


def test_nse_source_index_csv_parsing_and_caching(tmp_path):
    """Verify index CSV parsing, comma handling, volume normalization, and caching."""
    cache_dir = tmp_path / "cache"
    source = NSEIndiaSource(cache_dir=cache_dir)

    raw_csv = (
        "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,"
        "Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.)\n"
        'Nifty 50,05-01-2024,"21,500.50","21,700.00","21,450.00","21,680.25",'
        '150.00,0.70,"250,000,000",12000.50\n'
        'Nifty Next 50,05-01-2024,"52,000.00","52,400.00","51,900.00","52,350.00",'
        "200.00,0.38,-,3000.00\n"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = raw_csv

    with patch("requests.get", return_value=mock_resp):
        df = source._fetch_index_for_date("2024-01-05")

    assert df is not None
    assert len(df) == 2
    nifty = df[df["symbol"] == "Nifty 50"].iloc[0]
    assert nifty["date"] == "2024-01-05"
    assert nifty["open"] == 21500.50
    assert nifty["high"] == 21700.00
    assert nifty["low"] == 21450.00
    assert nifty["close"] == 21680.25
    assert nifty["adj_close"] == 21680.25
    assert nifty["volume"] == 250000000.0

    # Dash volume handled as 0.0
    nifty_next = df[df["symbol"] == "Nifty Next 50"].iloc[0]
    assert nifty_next["volume"] == 0.0

    # Verify cached parquet file was written
    cached_file = cache_dir / "index_2024-01-05.parquet"
    assert cached_file.exists()

    # Second call reads from cache
    with patch("requests.get") as mock_get:
        cached_df = source._fetch_index_for_date("2024-01-05")
        mock_get.assert_not_called()
        assert cached_df is not None
        assert len(cached_df) == 2


def test_nse_source_get_equity_prices_from_bhavcopy(tmp_path):
    """Verify get_equity_prices fetches and filters across date range."""
    cache_dir = tmp_path / "cache"
    source = NSEIndiaSource(cache_dir=cache_dir)

    df_day1 = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-02"],
            "symbol": ["RELIANCE", "TCS"],
            "open": [2500.0, 3700.0],
            "high": [2550.0, 3750.0],
            "low": [2490.0, 3690.0],
            "close": [2540.0, 3740.0],
            "adj_close": [2540.0, 3740.0],
            "volume": [1000000.0, 500000.0],
        }
    )
    df_day2 = pd.DataFrame(
        {
            "date": ["2024-01-03", "2024-01-03"],
            "symbol": ["RELIANCE", "TCS"],
            "open": [2545.0, 3745.0],
            "high": [2580.0, 3780.0],
            "low": [2530.0, 3730.0],
            "close": [2570.0, 3770.0],
            "adj_close": [2570.0, 3770.0],
            "volume": [1200000.0, 600000.0],
        }
    )

    def mock_fetch(d_str):
        if d_str == "2024-01-02":
            return df_day1
        if d_str == "2024-01-03":
            return df_day2
        return None

    with patch.object(source, "_fetch_bhavcopy_for_date", side_effect=mock_fetch):
        prices = source.get_equity_prices("RELIANCE.NS", "2024-01-02", "2024-01-03")

    assert len(prices) == 2
    assert list(prices["date"]) == ["2024-01-02", "2024-01-03"]
    assert list(prices["close"]) == [2540.0, 2570.0]
    expected_cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    assert list(prices.columns) == expected_cols


def test_nse_source_equity_prices_fixture_fallback(tmp_path):
    """Verify fallback to fixtures on network error or offline mode."""
    cache_dir = tmp_path / "empty_cache"
    source = NSEIndiaSource(cache_dir=cache_dir)

    # Force network failure
    source._network_reachable = False

    df = source.get_equity_prices("RELIANCE", "2021-01-01", "2021-01-10")
    assert not df.empty
    assert "date" in df.columns
    assert "close" in df.columns
    assert df["date"].iloc[0] >= "2021-01-01"
    assert df["date"].iloc[-1] <= "2021-01-10"


def test_nse_source_index_prices_and_normalization(tmp_path):
    """Verify get_index_prices symbol normalization and fixture fallback."""
    cache_dir = tmp_path / "cache"
    source = NSEIndiaSource(cache_dir=cache_dir)

    assert source._normalize_index_symbol("^NSEI") == "Nifty 50"
    assert source._normalize_index_symbol("NIFTY") == "Nifty 50"
    assert source._normalize_index_symbol("NIFTY50") == "Nifty 50"
    assert source._normalize_index_symbol("Nifty 50") == "Nifty 50"

    source._network_reachable = False
    df = source.get_index_prices("^NSEI", "2021-01-01", "2021-01-10")
    assert not df.empty
    assert "date" in df.columns
    assert "close" in df.columns


def test_nse_source_get_coverage(tmp_path):
    """Verify NSEIndiaSource.get_coverage inspecting fixtures and cache."""
    cache_dir = tmp_path / "cache"
    source = NSEIndiaSource(cache_dir=cache_dir)

    cov = source.get_coverage("RELIANCE")
    assert len(cov) == 1
    assert cov[0]["symbol"] == "RELIANCE"
    assert cov[0]["rows"] > 0

    all_cov = source.get_coverage()
    assert len(all_cov) > 0

    unknown = source.get_coverage("NONEXISTENT_STOCK_999")
    assert unknown == []


def test_get_price_source_factory():
    """Verify get_price_source returns appropriate source instances."""
    assert isinstance(get_price_source("CSV"), CSVSource)
    assert isinstance(get_price_source("parquet"), CSVSource)
    assert isinstance(get_price_source("fixtures"), CSVSource)
    assert isinstance(get_price_source("nse"), NSEIndiaSource)
    assert isinstance(get_price_source("NSEINDIA"), NSEIndiaSource)
    assert isinstance(get_price_source("BHAVCOPY"), NSEIndiaSource)
    assert isinstance(get_price_source("yfinance"), YFinanceSource)
    assert isinstance(get_price_source("yahoo"), YFinanceSource)
    assert isinstance(get_price_source("UNKNOWN_CUSTOM"), NSEIndiaSource)


def test_settings_data_source_defaults(monkeypatch):
    """Verify Settings.DATA_SOURCE defaults to nse, or CSV under testing/pytest."""
    # Under pytest execution, default is CSV
    s_test = Settings()
    assert s_test.DATA_SOURCE == "CSV"

    # Explicit value in kwargs overrides
    s_explicit = Settings(DATA_SOURCE="nse")
    assert s_explicit.DATA_SOURCE == "nse"

    # When PYTEST_CURRENT_TEST is unset and APP_ENV is development
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("DATA_SOURCE", raising=False)
    s_dev = Settings(APP_ENV="development")
    assert s_dev.DATA_SOURCE == "nse"

    # When APP_ENV is testing, defaults to CSV
    s_testing = Settings(APP_ENV="testing")
    assert s_testing.DATA_SOURCE == "CSV"


def test_yfinance_source_graceful_exception_handling():
    """Verify YFinanceSource catches exceptions gracefully without raising."""
    src = YFinanceSource()
    with patch(
        "yfinance.download", side_effect=requests.exceptions.ConnectionError("Offline")
    ):
        df = src._fetch_from_yfinance("RELIANCE.NS", "2024-01-01", "2024-01-05")
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == [
            "date",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
        ]
