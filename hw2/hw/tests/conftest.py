import pytest_asyncio
from pytest_asyncio.plugin import Mode
from shop_api.core.db import init_db

def pytest_configure(config):
    config.option.asyncio_mode = Mode.AUTO

@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_database():
    await init_db()
