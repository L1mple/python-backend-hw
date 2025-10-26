import asyncio
import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db_test"

from shop_api.main import engine, Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("Test database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())
