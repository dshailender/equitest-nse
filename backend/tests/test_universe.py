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
        {"symbol": "TEST_STOCK_101", "rank": 101},
        {"symbol": "TEST_STOCK_102", "rank": 102},
        {"symbol": "TEST_STOCK_103", "rank": 103},
    ]


def test_fallback_generator():
    """Verify fallback constituent generator returns ranks 101 to 750."""
    fallback = get_default_fallback_constituents()
    assert len(fallback) == 650
    assert fallback[0]["rank"] == 101
    assert fallback[-1]["rank"] == 750
