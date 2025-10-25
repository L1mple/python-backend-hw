import pytest
import asyncio
from sqlalchemy import text
from shop_api.database import Base, engine, async_session_maker


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        async with async_session_maker() as session:
            await session.execute(text("DELETE FROM cart_items"))
            await session.execute(text("DELETE FROM carts"))
            await session.execute(text("DELETE FROM items"))
            await session.commit()
    
    asyncio.run(init_db())
    yield
    
    async def cleanup_db():
        await engine.dispose()
    
    asyncio.run(cleanup_db())

