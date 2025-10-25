import pytest_asyncio
import asyncio
import asyncpg
from httpx import AsyncClient, ASGITransport
from hw2.hw.shop_api import app, get_conn, SCHEMA_SQL

DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_NAME = "shop"
DB_HOST = "localhost"
DB_PORT = 5432

@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
        min_size=1,
        max_size=10,
    )
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    yield pool
    await pool.close()

@pytest_asyncio.fixture
async def client(db_pool):
    async def override_get_conn():
        async with db_pool.acquire() as conn:
            yield conn

    app.dependency_overrides[get_conn] = override_get_conn

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
