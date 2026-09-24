import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_signals_symbol_happy_path(async_client: AsyncClient):
    """GET /api/v1/signals/{symbol} happy path returns full signal schema."""
    resp = await async_client.get(
        "/api/v1/signals/RELIANCE?start=2021-01-01&end=2021-12-31"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert data["count"] > 0
    assert len(data["signals"]) == data["count"]

    first_bar = data["signals"][0]
    expected_fields = [
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
        "regime_ok",
        "trend_ok",
        "near_52w_high",
        "crossover",
        "entry",
        "exit",
    ]
    for field in expected_fields:
        assert field in first_bar
        assert first_bar[field] is not None or "ema_" in field or "high_52w" in field

    # Confirm boolean types
    assert isinstance(first_bar["regime_ok"], bool)
    assert isinstance(first_bar["trend_ok"], bool)
    assert isinstance(first_bar["near_52w_high"], bool)
    assert isinstance(first_bar["crossover"], bool)
    assert isinstance(first_bar["entry"], bool)
    assert isinstance(first_bar["exit"], bool)


@pytest.mark.asyncio
async def test_api_signals_symbol_not_found(async_client: AsyncClient):
    """GET /api/v1/signals/{symbol} returns 404 for unknown symbol."""
    resp = await async_client.get("/api/v1/signals/UNKNOWN_XYZ_999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_signals_screen_fixture_date(async_client: AsyncClient):
    """GET /api/v1/signals/screen returns active entry tickers on fixture date."""

    resp = await async_client.get("/api/v1/signals/screen?date=2020-06-25")
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2020-06-25"
    assert data["survivorship_bias"] is False
    assert "MIDCAP_STOCK_101" in data["symbols"]
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_api_signals_screen_invalid_date(async_client: AsyncClient):
    """GET /api/v1/signals/screen returns 422 for malformed date parameter."""
    resp = await async_client.get("/api/v1/signals/screen?date=invalid-date")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_api_signals_screen_bear_market_zero_trades(async_client: AsyncClient):
    """GET /api/v1/signals/screen on a bear market date returns 0 trades."""
    # During March 2020 COVID crash, NIFTY was well below EMA 50 & 200
    resp = await async_client.get("/api/v1/signals/screen?date=2020-03-25")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["symbols"] == []
