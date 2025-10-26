import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://shop_user:shop_pass@localhost:5432/shop_db"
engine = create_async_engine(DATABASE_URL)

async def test_db():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1;"))
        print(result.fetchall())

asyncio.run(test_db())
