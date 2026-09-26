from sqlmodel import Session

from app.data.universe import get_default_fallback_constituents, get_universe


def test_universe_with_point_in_time_fixture():
    """Verify resolver returns ranks 101 to 750 on 3 dates without bias."""
    dates = ["2020-01-01", "2022-01-01", "2024-01-01"]

    for d in dates:
        tickers, survivorship_bias, details = get_universe(d)
        assert (
            not survivorship_bias
        ), f"Expected no survivorship bias for fixture date {d}"
        assert (
            len(tickers) == 650
        ), f"Expected exactly 650 tickers (ranks 101-750), got {len(tickers)}"
        assert len(details) == 650

        # Ranks must strictly run from 101 to 750
        ranks = [item["rank"] for item in details]
        assert ranks[0] == 101
        assert ranks[-1] == 750
        assert ranks == list(range(101, 751))

        # None of the top 100 stocks should be in the returned universe
        for item in details:
            assert not item["symbol"].startswith(
                "TOP_"
            ), f"Top 100 stock found in universe: {item['symbol']}"


def test_universe_fallback_survivorship_bias():
    """Verify missing point-in-time constituent records returns bias flag."""
    # Year 2010 has no point-in-time records
    tickers, survivorship_bias, details = get_universe("2010-01-01")
    assert survivorship_bias is True
    assert len(tickers) == 650
    assert len(details) == 650


def test_universe_with_database_session(temp_db: Session):
    """Verify universe resolver accurately queries database membership records."""
    from app.db.models import UniverseMembership

    # Seed 3 records in temp_db for 2023-05-01
    temp_db.add(
        UniverseMembership(date="2023-05-01", symbol="TEST_STOCK_101", rank=101)
    )
    temp_db.add(
        UniverseMembership(date="2023-05-01", symbol="TEST_STOCK_102", rank=102)
    )
    temp_db.add(
        UniverseMembership(date="2023-05-01", symbol="TEST_STOCK_103", rank=103)
    )
    temp_db.commit()

    tickers, survivorship_bias, details = get_universe("2023-05-01", session=temp_db)
    assert not survivorship_bias
    assert tickers == ["TEST_STOCK_101", "TEST_STOCK_102", "TEST_STOCK_103"]
    assert details == [
        {
            "symbol": "TEST_STOCK_101",
            "name": "Test Stock 101 Ltd",
            "rank": 101,
            "sector": "Diversified",
        },
        {
            "symbol": "TEST_STOCK_102",
            "name": "Test Stock 102 Ltd",
            "rank": 102,
            "sector": "Diversified",
        },
        {
            "symbol": "TEST_STOCK_103",
            "name": "Test Stock 103 Ltd",
            "rank": 103,
            "sector": "Diversified",
        },
    ]


def test_fallback_generator():
    """Verify fallback constituent generator returns ranks 101 to 750."""
    fallback = get_default_fallback_constituents()
    assert len(fallback) == 650
    assert fallback[0]["rank"] == 101
    assert fallback[0]["name"] == "Vodafone Idea Ltd"
    assert fallback[0]["sector"] == "Telecommunication"
    assert fallback[-1]["rank"] == 750


def test_universe_company_names_metadata():
    """Verify universe constituents contain company names and sectors (AUD-B-001)."""
    # 1. Fallback / default constituents
    tickers, survivorship_bias, details = get_universe("2010-01-01")
    assert survivorship_bias is True
    assert len(details) == 650
    for item in details:
        assert "symbol" in item and item["symbol"]
        assert "name" in item and item["name"]
        assert "rank" in item and 101 <= item["rank"] <= 750
        assert "sector" in item and item["sector"]

    # Spot-check known midcaps
    first = details[0]
    assert first["symbol"] == "IDEA"
    assert first["name"] == "Vodafone Idea Ltd"
    assert first["rank"] == 101
    assert first["sector"] == "Telecommunication"

    second = details[1]
    assert second["symbol"] == "YESBANK"
    assert second["name"] == "Yes Bank Ltd"
    assert second["rank"] == 102
    assert second["sector"] == "Financial Services"

    # 2. Point-in-time fixture
    tickers_pit, bias_pit, details_pit = get_universe("2022-01-01")
    assert not bias_pit
    assert len(details_pit) == 650
    for item in details_pit:
        assert item["name"] != ""
        assert item["sector"] != ""


def test_universe_authentic_constituents_no_synthetic_tokens():
    """Verify ranks 101 to 750 use authentic NSE tickers (AUD-B-002)."""
    # 1. Point-in-time fixture dates
    for d in ["2020-01-01", "2022-01-01", "2024-01-01"]:
        tickers, survivorship_bias, details = get_universe(d)
        assert not survivorship_bias
        assert len(tickers) == 650
        assert len(set(tickers)) == 650
        assert all(not sym.startswith("MIDCAP_STOCK_") for sym in tickers)
        assert all(not sym.startswith("TOP_") for sym in tickers)
        assert all("_" not in sym for sym in tickers)
        for item in details:
            assert item["symbol"]
            assert item["name"]
            assert item["sector"]
            assert 101 <= item["rank"] <= 750

    # 2. Fallback generator date
    tickers_fb, survivorship_bias_fb, details_fb = get_universe("2015-01-01")
    assert survivorship_bias_fb
    assert len(tickers_fb) == 650
    assert len(set(tickers_fb)) == 650
    assert all(not sym.startswith("MIDCAP_STOCK_") for sym in tickers_fb)
    assert all(not sym.startswith("TOP_") for sym in tickers_fb)
    assert all("_" not in sym for sym in tickers_fb)
    for item in details_fb:
        assert item["symbol"]
        assert item["name"]
        assert item["sector"]
        assert 101 <= item["rank"] <= 750


def test_sample_midcaps_deduplicated():
    """Verify sample_midcaps list contains no duplicate tickers (AUD-B-003)."""
    from app.data.universe import (
        SAMPLE_MIDCAPS,
        get_default_fallback_constituents,
        sample_midcaps,
    )

    # 1. Acceptance criteria: len(sample_midcaps) == len(set(sample_midcaps))
    assert len(sample_midcaps) == len(set(sample_midcaps))
    assert len(SAMPLE_MIDCAPS) == len(set(SAMPLE_MIDCAPS))
    assert sample_midcaps == SAMPLE_MIDCAPS

    # 2. Specifically verify 'TATACOMM' appears exactly once
    assert sample_midcaps.count("TATACOMM") == 1
    assert SAMPLE_MIDCAPS.count("TATACOMM") == 1

    # 3. Fallback constituent generator contains no duplicates and exactly one TATACOMM
    fallback = get_default_fallback_constituents()
    fallback_symbols = [item["symbol"] for item in fallback]
    assert len(fallback_symbols) == len(set(fallback_symbols)) == 650
    assert fallback_symbols.count("TATACOMM") == 1


def test_universe_db_session_point_in_time_and_synthetic_filtering(
    temp_db: Session,
):
    """Verify DB session resolves PIT date and filters synthetic tokens."""
    from app.db.models import UniverseMembership

    # Seed mix of authentic and legacy synthetic tokens for 2022-01-01
    temp_db.add(
        UniverseMembership(date="2022-01-01", symbol="MIDCAP_STOCK_101", rank=101)
    )
    temp_db.add(UniverseMembership(date="2022-01-01", symbol="TOP_1", rank=1))
    temp_db.add(UniverseMembership(date="2022-01-01", symbol="TATAELXSI", rank=101))
    temp_db.add(UniverseMembership(date="2022-01-01", symbol="FEDERALBNK", rank=102))
    temp_db.commit()

    # 1. Exact date resolution
    tickers, bias, details = get_universe("2022-01-01", session=temp_db)
    assert not bias
    assert tickers == ["TATAELXSI", "FEDERALBNK"]
    assert details[0]["name"] == "Tata Elxsi Ltd"
    assert details[0]["sector"] == "Information Technology"
    assert details[1]["name"] == "Federal Bank Ltd"
    assert details[1]["sector"] == "Financial Services"

    # 2. Point-in-time date resolution (2022-06-15 uses 2022-01-01 constituents)
    tickers_pit, bias_pit, details_pit = get_universe("2022-06-15", session=temp_db)
    assert not bias_pit
    assert tickers_pit == ["TATAELXSI", "FEDERALBNK"]


def test_seed_universe_constituents(temp_db: Session):
    """Verify seed_universe_constituents purges synthetic records and seeds data."""
    from app.data.ingest import seed_universe_constituents
    from app.db.models import UniverseMembership

    # Add synthetic records
    temp_db.add(
        UniverseMembership(date="2022-01-01", symbol="MIDCAP_STOCK_101", rank=101)
    )
    temp_db.add(UniverseMembership(date="2022-01-01", symbol="TOP_1", rank=1))
    temp_db.commit()

    raw_conn = temp_db.connection()
    count = seed_universe_constituents(raw_conn)
    assert count == 2250

    # Ensure no synthetic records remain
    cursor = raw_conn.connection.cursor()
    cursor.execute(
        "SELECT count(*) FROM universe_membership "
        "WHERE symbol LIKE 'MIDCAP_STOCK_%' OR symbol LIKE 'TOP_%'"
    )
    assert cursor.fetchone()[0] == 0
