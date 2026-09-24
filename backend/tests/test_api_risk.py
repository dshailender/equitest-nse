"""Integration tests for risk management and position sizing REST endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_api_risk_size_baseline_500k():
    """Verify /api/v1/risk/size returns expected qty and capital for 500k corpus."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/risk/size",
            json={
                "corpus": 500000.0,
                "entry": 100.0,
                "sl_pct": 0.07,
                "risk_pct": 0.02,
                "lot_size": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["qty"] == 1428
        assert data["capital_required"] == 142800.0
        assert data["sl_price"] == 93.0
        assert data["risk_amount"] == 10000.0


@pytest.mark.asyncio
async def test_api_risk_size_100k():
    """Verify /api/v1/risk/size returns qty=285 and capital=28500 for 100k corpus."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/risk/size",
            json={
                "corpus": 100000.0,
                "entry": 100.0,
                "sl_pct": 0.07,
                "risk_pct": 0.02,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["qty"] == 285
        assert data["capital_required"] == 28500.0
        assert data["sl_price"] == 93.0
        assert data["risk_amount"] == 2000.0


@pytest.mark.asyncio
async def test_api_risk_size_input_validation():
    """Verify /api/v1/risk/size validates inputs and rejects invalid fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Negative corpus
        resp_neg_corpus = await client.post(
            "/api/v1/risk/size",
            json={"corpus": -50000.0, "entry": 100.0},
        )
        assert resp_neg_corpus.status_code == 422

        # Zero or negative entry
        resp_zero_entry = await client.post(
            "/api/v1/risk/size",
            json={"corpus": 500000.0, "entry": 0.0},
        )
        assert resp_zero_entry.status_code == 422

        # Invalid sl_pct (> 1 or <= 0)
        resp_bad_sl = await client.post(
            "/api/v1/risk/size",
            json={"corpus": 500000.0, "entry": 100.0, "sl_pct": 1.5},
        )
        assert resp_bad_sl.status_code == 422

        # Invalid risk_pct (<= 0)
        resp_bad_risk = await client.post(
            "/api/v1/risk/size",
            json={"corpus": 500000.0, "entry": 100.0, "risk_pct": 0.0},
        )
        assert resp_bad_risk.status_code == 422

        # Invalid lot_size (< 1)
        resp_bad_lot = await client.post(
            "/api/v1/risk/size",
            json={"corpus": 500000.0, "entry": 100.0, "lot_size": 0},
        )
        assert resp_bad_lot.status_code == 422


@pytest.mark.asyncio
async def test_api_risk_config_endpoint():
    """Verify /api/v1/risk/config returns default risk configuration parameters."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/risk/config")
        assert response.status_code == 200
        data = response.json()
        assert data["corpus"] == 500000.0
        assert data["risk_pct"] == 0.02
        assert data["stop_loss_pct"] == 0.07
        assert data["lot_size"] == 1
        assert data["cost_bps"] == 10.0
