import logging
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from app.core.logging import JSONFormatter, setup_logging
from app.db.session import get_session, init_db
from app.main import export_openapi


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient):
    """Test that /health returns status 200 with ok and version 0.1.0."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "version": "0.1.0"}
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_request_id_header_forwarded(async_client: AsyncClient):
    """Test that custom X-Request-ID is preserved in response headers."""
    custom_id = "test-request-id-12345"
    response = await async_client.get("/health", headers={"x-request-id": custom_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    """Test that /api/v1/health returns status 200 with ok and version 0.1.0."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "version": "0.1.0"}


def test_fixture_data_paths(fixture_data_paths: Path):
    """Test that fixture data path exists and is accessible."""
    assert fixture_data_paths.exists()
    assert fixture_data_paths.is_dir()


def test_config_settings():
    """Test default settings configuration."""
    s = Settings()
    assert s.APP_ENV in ["development", "testing", "production"]
    assert s.DATABASE_URL.startswith("sqlite")
    assert s.LOG_LEVEL == "INFO"
    assert s.APP_VERSION == "0.1.0"


def test_db_session_and_init():
    """Test database initialization and session dependency."""
    init_db()
    session_gen = get_session()
    session = next(session_gen)
    assert session is not None
    session.close()


def test_json_logging_formatter():
    """Test JSON log formatter output."""
    setup_logging("DEBUG")
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "timestamp" in formatted
    assert "Test log message" in formatted
    assert "INFO" in formatted


def test_export_openapi_schema(tmp_path: Path):
    """Test OpenAPI schema export utility."""
    out_file = tmp_path / "openapi_test.json"
    export_openapi(out_file)
    assert out_file.exists()
    assert out_file.stat().st_size > 0
