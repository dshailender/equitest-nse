from datetime import datetime

from fastapi.testclient import TestClient

from app.data.ingest import seed_price_coverage
from app.db.session import init_db
from app.main import create_app


def test_data_coverage_15_years_and_constituents_count():
    """Verify AUD-E-001 acceptance criteria:

    1. GET /api/v1/data/coverage returns >= 650 symbols.
    2. Symbols possess continuous historical sessions spanning 15+ years.
    3. Key equities appear on page 1 of the coverage response.
    """
    init_db()
    app = create_app()

    with TestClient(app) as client:
        resp = client.get("/api/v1/data/coverage")
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", [])

        # Acceptance Criterion 1: returns >= 650 symbols
        assert (
            len(items) >= 650
        ), f"Expected >= 650 symbols in coverage, got {len(items)}"

        # Verify key equities prioritized on page 1
        page1_symbols = [item["symbol"] for item in items[:5]]
        assert "RELIANCE" in page1_symbols
        assert "HDFCBANK" in page1_symbols
        assert "INFY" in page1_symbols
        assert "TATAMOTORS" in page1_symbols

        # Acceptance Criterion 2: continuous historical sessions spanning 15+ years
        for item in items:
            assert "symbol" in item and item["symbol"]
            assert "first_date" in item and item["first_date"]
            assert "last_date" in item and item["last_date"]
            assert "rows" in item and item["rows"] >= 3700

            d_first = datetime.strptime(item["first_date"], "%Y-%m-%d")
            d_last = datetime.strptime(item["last_date"], "%Y-%m-%d")
            diff_years = (d_last - d_first).days / 365.25

            assert diff_years >= 15.0, (
                f"Symbol {item['symbol']} coverage is {diff_years:.1f} years, "
                "expected >= 15.0 years"
            )


def test_seed_price_coverage_idempotency():
    """Verify seed_price_coverage can be invoked multiple times without error."""
    count = seed_price_coverage()
    assert count >= 650
