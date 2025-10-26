import asyncio
import pytest
import pytest_asyncio
import httpx
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from src.config import settings
from src.models import Base



test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    asyncio.run(_setup_db())
    yield
    asyncio.run(_teardown_db())


async def _setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _teardown_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def clean_db():
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"TRUNCATE {table.name} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def client():
    from src import main
    from src.db.deps import get_db

    async def override_get_db():
        async with TestingSessionLocal() as session:
            print(f"→ OPEN session {id(session)}")
            try:
                yield session
            finally:
                print(f"← CLOSE session {id(session)}")

    pg_app = main.pg_app
    pg_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=pg_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    pg_app.dependency_overrides.clear()