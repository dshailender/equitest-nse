from unittest.mock import patch

import pandas as pd
import pytest

from app.data.source import (
    CSVSource,
    PriceSource,
    YFinanceSource,
    get_price_source,
)


def test_price_source_is_abstract():
    """Verify PriceSource cannot be directly instantiated."""
    with pytest.raises(TypeError):
        PriceSource()  # type: ignore


def test_get_price_source_factory():
    """Verify factory returns appropriate PriceSource subclass instances."""
    assert isinstance(get_price_source("CSV"), CSVSource)
    assert isinstance(get_price_source("parquet"), CSVSource)
    assert isinstance(get_price_source("fixtures"), CSVSource)
    assert isinstance(get_price_source("yfinance"), YFinanceSource)


def test_yfinance_source_get_coverage_acceptance_criteria():
    """Verify AUD-F-001 acceptance criteria:

    get_price_source("yfinance").get_coverage() executes cleanly without
    throwing an AttributeError.
    """
    src = get_price_source("yfinance")
    assert isinstance(src, YFinanceSource)
    cov = src.get_coverage()
    assert isinstance(cov, list)
    assert cov == []


def test_yfinance_source_get_coverage_with_data():
    """Verify YFinanceSource.get_coverage returns valid coverage structure."""
    src = YFinanceSource()
    mock_df = pd.DataFrame(
        {
            "date": ["2023-01-02", "2023-01-03", "2023-01-04"],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [99.0, 100.0, 101.0],
            "close": [104.0, 105.0, 106.0],
            "adj_close": [104.0, 105.0, 106.0],
            "volume": [10000.0, 12000.0, 11000.0],
        }
    )

    with patch.object(src, "_fetch_from_yfinance", return_value=mock_df):
        cov = src.get_coverage("RELIANCE")
        assert len(cov) == 1
        item = cov[0]
        assert item["symbol"] == "RELIANCE"
        assert item["first_date"] == "2023-01-02"
        assert item["last_date"] == "2023-01-04"
        assert item["rows"] == 3


def test_yfinance_source_get_coverage_empty_or_error():
    """Verify YFinanceSource.get_coverage returns empty list on error/empty."""
    src = YFinanceSource()
    with patch.object(src, "_fetch_from_yfinance", return_value=pd.DataFrame()):
        cov = src.get_coverage("UNKNOWN_SYMBOL")
        assert cov == []

    with patch.object(
        src, "_fetch_from_yfinance", side_effect=RuntimeError("Network down")
    ):
        cov = src.get_coverage("RELIANCE")
        assert cov == []


def test_yfinance_ticker_normalization():
    """Verify YFinanceSource ticker normalization for equity and index symbols."""
    src = YFinanceSource()
    assert src._normalize_ticker("RELIANCE") == "RELIANCE.NS"
    assert src._normalize_ticker("reliance.ns") == "RELIANCE.NS"
    assert src._normalize_ticker("TCS.BO") == "TCS.BO"
    assert src._normalize_ticker("NIFTY", is_index=True) == "^NSEI"
    assert src._normalize_ticker("NIFTY50", is_index=True) == "^NSEI"
    assert src._normalize_ticker("NIFTY_50", is_index=True) == "^NSEI"
    assert src._normalize_ticker("^NSEI", is_index=True) == "^NSEI"
    assert src._normalize_ticker("CNX500", is_index=True) == "^CNX500"


def test_csv_source_get_coverage():
    """Verify CSVSource.get_coverage provides coverage for fixtures."""
    src = CSVSource()
    all_cov = src.get_coverage()
    assert len(all_cov) > 0

    reliance_item = next(
        (item for item in all_cov if item["symbol"] == "RELIANCE"), None
    )
    assert reliance_item is not None
    assert reliance_item["first_date"] is not None
    assert reliance_item["last_date"] is not None
    assert reliance_item["rows"] > 0

    # Single symbol query
    single = src.get_coverage("RELIANCE")
    assert len(single) == 1
    assert single[0]["symbol"] == "RELIANCE"
    assert single[0]["rows"] == reliance_item["rows"]

    # Nonexistent symbol query
    nonexistent = src.get_coverage("NONEXISTENT_XYZ_123")
    assert nonexistent == []
