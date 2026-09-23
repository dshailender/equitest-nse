import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_data_lifecycle(async_client: AsyncClient):
    """Test full API lifecycle: ingest, coverage, universe, prices, 404."""
    # 1. Initially coverage is empty
    cov_resp = await async_client.get("/api/v1/data/coverage")
    assert cov_resp.status_code == 200
    assert cov_resp.json() == {"items": []}

    # 2. Unknown symbol returns 404
    err_resp = await async_client.get("/api/v1/prices/UNKNOWN_SYMBOL_999")
    assert err_resp.status_code == 404

    # 3. Ingest market data using CSV fixture source
    ingest_payload = {
        "start": "2020-01-01",
        "end": "2021-12-31",
        "symbols": ["RELIANCE", "INFY"],
    }
    ingest_resp = await async_client.post("/api/v1/data/ingest", json=ingest_payload)
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["status"] == "completed"
    assert ingest_data["symbols_ingested"] == 2
    assert ingest_data["rows_ingested"] > 0
    assert len(ingest_data["errors"]) == 0

    # 4. Coverage now lists RELIANCE and INFY
    cov_after = await async_client.get("/api/v1/data/coverage")
    assert cov_after.status_code == 200
    symbols = [item["symbol"] for item in cov_after.json()["items"]]
    assert "RELIANCE" in symbols
    assert "INFY" in symbols

    # 5. Universe endpoint returns 650 tickers
    univ_resp = await async_client.get("/api/v1/universe?date=2020-01-01")
    assert univ_resp.status_code == 200
    univ_data = univ_resp.json()
    assert univ_data["count"] == 650
    assert len(univ_data["tickers"]) == 650
    assert univ_data["survivorship_bias"] is False

    # 6. Prices endpoint returns correct schema
    price_resp = await async_client.get("/api/v1/prices/RELIANCE")
    assert price_resp.status_code == 200
    price_data = price_resp.json()
    assert price_data["symbol"] == "RELIANCE"
    assert price_data["count"] > 0
    first_bar = price_data["prices"][0]
    for key in ["date", "open", "high", "low", "close", "adj_close", "volume"]:
        assert key in first_bar


@pytest.mark.asyncio
async def test_prices_no_lookahead_leak(async_client: AsyncClient):
    """Verify querying prices for date D returns only rows <= D (no leak)."""
    # Ingest full range
    await async_client.post(
        "/api/v1/data/ingest",
        json={"start": "2020-01-01", "end": "2022-12-31", "symbols": ["HDFCBANK"]},
    )

    # Query with end = 2021-06-30
    cutoff_date = "2021-06-30"
    resp = await async_client.get(f"/api/v1/prices/HDFCBANK?end={cutoff_date}")
    assert resp.status_code == 200
    prices = resp.json()["prices"]
    assert len(prices) > 0

    # Assert no row has date > cutoff_date
    for bar in prices:
        assert (
            bar["date"] <= cutoff_date
        ), f"Look-ahead leak detected: bar date {bar['date']} > {cutoff_date}"
