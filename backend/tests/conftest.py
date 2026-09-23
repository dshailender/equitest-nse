from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.session import get_session
from app.main import create_app


@pytest.fixture(scope="session")
def fixture_data_paths() -> Path:
    """Returns the path to project test fixtures."""
    fixtures_dir = Path(__file__).parent.parent.parent / "data" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    return fixtures_dir


@pytest.fixture
def temp_db() -> Generator[Session, None, None]:
    """Provides a fresh, isolated in-memory SQLite session for testing."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session


@pytest_asyncio.fixture
async def async_client(temp_db: Session) -> AsyncGenerator[AsyncClient, None]:
    """Provides an asynchronous HTTP test client for the FastAPI app."""
    test_app = create_app()

    # Override get_session dependency with isolated test session
    def override_get_session():
        yield temp_db

    test_app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
