import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_indicators_symbol_happy_path(async_client: AsyncClient):
    """Test GET /api/v1/indicators/{symbol} returns augmented OHLCV."""
    resp = await async_client.get(
        "/api/v1/indicators/RELIANCE?start=2021-01-01&end=2021-12-31"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "RELIANCE"
    assert data["count"] > 0
    assert len(data["indicators"]) == data["count"]

    first_item = data["indicators"][0]
    expected_keys = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "ema_20",
        "ema_50",
        "ema_150",
        "ema_200",
        "high_52w",
        "indicators",
    ]
    for key in expected_keys:
        assert key in first_item, f"Missing key {key} in IndicatorItem"

    # Because data starts in 2019/2020, by 2021-01-01 indicators are fully warmed up
    # Assert no NaNs / None in warmed-up series
    for item in data["indicators"]:
        assert item["ema_20"] is not None
        assert item["ema_50"] is not None
        assert item["ema_150"] is not None
        assert item["ema_200"] is not None
        assert item["high_52w"] is not None
        assert item["date"] >= "2021-01-01"
        assert item["date"] <= "2021-12-31"


@pytest.mark.asyncio
async def test_api_indicators_warmup_none_behavior(async_client: AsyncClient):
    """Verify rows before warm-up return null (None in Python)."""
    # Query from the very beginning of the series (2019-01-01)
    resp = await async_client.get(
        "/api/v1/indicators/RELIANCE?start=2019-01-01&end=2019-03-01"
    )
    assert resp.status_code == 200
    data = resp.json()

    items = data["indicators"]
    assert len(items) > 0

    # First row: EMA-20, EMA-50, EMA-150, EMA-200, high_52w must be null (None)
    assert items[0]["ema_20"] is None
    assert items[0]["ema_50"] is None
    assert items[0]["ema_200"] is None
    assert items[0]["high_52w"] is None

    # Row index 19 (row 20) should have valid ema_20, but ema_50 is still null
    if len(items) >= 20:
        assert items[19]["ema_20"] is not None
        assert items[19]["ema_50"] is None


@pytest.mark.asyncio
async def test_api_indicators_nifty(async_client: AsyncClient):
    """Test GET /api/v1/indicators/nifty returns 50 and 200 EMAs on benchmark."""
    resp = await async_client.get(
        "/api/v1/indicators/nifty?start=2021-01-01&end=2021-12-31"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "NIFTY50"
    assert data["count"] > 0

    first_item = data["indicators"][0]
    assert first_item["ema_50"] is not None
    assert first_item["ema_200"] is not None


@pytest.mark.asyncio
async def test_api_indicators_preview(async_client: AsyncClient):
    """Test POST /api/v1/indicators/preview with custom config."""
    payload = {
        "symbol": "INFY",
        "start": "2021-01-01",
        "end": "2021-06-30",
        "config": {
            "spans": [10, 30],
            "include_high_52w": True,
            "high_52w_lookback": 50,
        },
    }
    resp = await async_client.post("/api/v1/indicators/preview", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "INFY"
    assert data["count"] > 0

    first = data["indicators"][0]
    assert "ema_10" in first["indicators"]
    assert "ema_30" in first["indicators"]
    assert "high_52w" in first["indicators"]


@pytest.mark.asyncio
async def test_api_indicators_error_cases(async_client: AsyncClient):
    """Verify error cases: unknown symbol (404), invalid spans (422)."""
    # 404 for unknown symbol
    err_404 = await async_client.get("/api/v1/indicators/NONEXISTENT_SYMBOL_XYZ")
    assert err_404.status_code == 404

    # 422 for invalid spans string
    err_422 = await async_client.get("/api/v1/indicators/RELIANCE?spans=abc,-5")
    assert err_422.status_code == 422
