import pytest
import asyncio


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Создаем и очищаем таблицы перед тестами"""
    from shop_api.database import engine, Base
    
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    
    # Запускаем в новом event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    loop.close()
    
    yield
    
    # Очищаем после всех тестов
    async def cleanup_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cleanup_db())
    loop.close()

