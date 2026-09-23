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
