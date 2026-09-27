from sqlmodel import Session, func, select

from app.data.ingest import ingest_market_data
from app.data.source import CSVSource
from app.db.models import IndexPrice, Price, UniverseMembership


def test_ingest_idempotency(temp_db: Session):
    """Verify running ingest twice for same range produces identical row counts."""
    source = CSVSource()
    symbols = ["RELIANCE", "INFY"]
    start = "2020-01-01"
    end = "2020-06-30"

    # First run
    res1 = ingest_market_data(
        session=temp_db,
        start=start,
        end=end,
        symbols=symbols,
        source=source,
    )
    assert res1["status"] == "completed"
    assert res1["symbols_ingested"] == 2
    assert res1["rows_ingested"] > 0

    first_price_count = temp_db.exec(select(func.count(Price.date))).one()
    first_idx_count = temp_db.exec(select(func.count(IndexPrice.date))).one()
    first_univ_count = temp_db.exec(select(func.count(UniverseMembership.symbol))).one()

    # Second run (exact same parameters)
    res2 = ingest_market_data(
        session=temp_db,
        start=start,
        end=end,
        symbols=symbols,
        source=source,
    )
    assert res2["status"] == "completed"
    assert (
        res2["rows_ingested"] == 0
    ), "Second ingestion run should insert 0 new rows (idempotency)"

    second_price_count = temp_db.exec(select(func.count(Price.date))).one()
    second_idx_count = temp_db.exec(select(func.count(IndexPrice.date))).one()
    second_univ_count = temp_db.exec(
        select(func.count(UniverseMembership.symbol))
    ).one()

    assert first_price_count == second_price_count
    assert first_idx_count == second_idx_count
    assert first_univ_count == second_univ_count


def test_corporate_action_split_adjustment():
    """Verify RELIANCE fixture split preserves continuous adjusted close."""
    source = CSVSource()
    df = source.get_equity_prices("RELIANCE", "2021-05-25", "2021-06-05")
    assert not df.empty

    # Find the split date 2021-06-01
    split_row = df[df["date"] >= "2021-06-01"].iloc[0]
    pre_split_row = df[df["date"] < "2021-06-01"].iloc[-1]

    # Unadjusted close dropped ~50%
    ratio = pre_split_row["close"] / split_row["close"]
    assert (
        1.8 <= ratio <= 2.2
    ), f"Expected 2:1 price drop on unadjusted close, got ratio {ratio}"

    # Adjusted close ratio is close to 1 (economic continuity)
    adj_ratio = pre_split_row["adj_close"] / split_row["adj_close"]
    assert (
        0.95 <= adj_ratio <= 1.05
    ), f"Expected continuous adjusted close, got ratio {adj_ratio}"


def test_ingest_purges_synthetic_universe_constituents(temp_db: Session):
    """Verify market data ingestion purges legacy synthetic universe constituents."""
    # Seed legacy synthetic records into temp_db
    temp_db.add(
        UniverseMembership(date="2020-01-01", symbol="MIDCAP_STOCK_101", rank=101)
    )
    temp_db.add(UniverseMembership(date="2020-01-01", symbol="TOP_1", rank=1))
    temp_db.commit()

    source = CSVSource()
    res = ingest_market_data(
        session=temp_db,
        start="2020-01-01",
        end="2020-01-02",
        symbols=["RELIANCE"],
        source=source,
    )
    assert res["status"] == "completed"

    # Confirm synthetic constituents were purged and authentic ones populated
    synthetic_count = temp_db.exec(
        select(func.count(UniverseMembership.symbol)).where(
            UniverseMembership.symbol.like("MIDCAP_STOCK_%")  # type: ignore
            | UniverseMembership.symbol.like("TOP_%")  # type: ignore
        )
    ).one()
    assert synthetic_count == 0

    # Ensure authentic records exist
    total_count = temp_db.exec(
        select(func.count(UniverseMembership.symbol)).where(
            UniverseMembership.date == "2020-01-01"
        )
    ).one()
    assert total_count == 750


def test_ingest_diagnostics_empty_symbols_and_index(temp_db: Session, tmp_path):
    """Verify empty DataFrame for equity and index records descriptive errors and failed status."""
    source = CSVSource(fixtures_dir=tmp_path)
    res = ingest_market_data(
        session=temp_db,
        start="2020-01-01",
        end="2020-01-02",
        symbols=["NON_EXISTENT_SYMBOL_XYZ"],
        source=source,
    )
    assert res["status"] == "failed"
    assert res["rows_ingested"] == 0
    assert any("No price data available for symbol 'NON_EXISTENT_SYMBOL_XYZ'" in e for e in res["errors"])
    assert any("No price data available for benchmark index '^NSEI'" in e for e in res["errors"])


def test_ingest_partial_status(temp_db: Session):
    """Verify partial status when some symbols ingest successfully while others are empty."""
    source = CSVSource()
    res = ingest_market_data(
        session=temp_db,
        start="2020-01-01",
        end="2020-01-05",
        symbols=["RELIANCE", "NON_EXISTENT_TICKER_123"],
        source=source,
    )
    assert res["status"] == "partial"
    assert res["rows_ingested"] > 0
    assert any("No price data available for symbol 'NON_EXISTENT_TICKER_123'" in e for e in res["errors"])


def test_seed_universe_constituents_code_fallback(temp_db: Session, monkeypatch, tmp_path):
    """Verify seed_universe_constituents generates 2,250 rows when parquet fixture does not exist."""
    from app.data.ingest import seed_universe_constituents

    # Point fixtures dir to an empty temporary path
    monkeypatch.setenv("FIXTURES_DIR", str(tmp_path))

    raw_conn = temp_db.connection()
    count = seed_universe_constituents(raw_conn)
    assert count == 2250

    cursor = raw_conn.connection.cursor()
    cursor.execute("SELECT count(*) FROM universe_membership")
    assert cursor.fetchone()[0] == 2250

