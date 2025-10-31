"""Pytest configuration and fixtures for all tests

Provides fixtures for different test types:
- unit tests: use mocks and isolated components
- integration tests: use real database session (SQLite in-memory)
- e2e tests: use HTTP client with full application stack
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shop_api.main import app
from shop_api.database import get_db
from shop_api.data.db_models import Base


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests - fast, isolated, use mocks"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - test multiple components with database"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests - test complete HTTP API flow"
    )


def pytest_collection_modifyitems(items):
    """Automatically apply markers based on test location"""
    for item in items:
        # Get test file path
        test_path = str(item.fspath)

        # Apply markers based on directory
        if "/unit/" in test_path or "\\unit\\" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path or "\\integration\\" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in test_path or "\\e2e\\" in test_path:
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def event_loop():
    """Creates event loop for pytest-asyncio (prevents 'attached to a different loop' error)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Async test client fixture for API tests (uses real PostgreSQL)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def db_session():
    """Creates temporary in-memory SQLite DB for each unit test."""
    # Use SQLite in memory to avoid transaction conflicts
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        yield session
        await session.rollback()  # Clean up changes

    await engine.dispose()
