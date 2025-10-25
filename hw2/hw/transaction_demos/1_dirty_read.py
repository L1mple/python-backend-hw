import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db")

async def setup(engine):
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS accounts CASCADE"))
        await conn.execute(text("CREATE TABLE accounts (id SERIAL PRIMARY KEY, balance INTEGER)"))
        await conn.execute(text("INSERT INTO accounts (balance) VALUES (1000)"))

async def tx1_uncommitted(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        await s.execute(text("UPDATE accounts SET balance = 2000"))
        await asyncio.sleep(1)
        await s.rollback()

async def tx2_uncommitted(engine):
    await asyncio.sleep(0.5)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        r = await s.execute(text("SELECT balance FROM accounts"))
        print(f"READ UNCOMMITTED: {r.scalar()} (ожидаем 1000, PostgreSQL не поддерживает READ UNCOMMITTED)")

async def tx1_committed(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("UPDATE accounts SET balance = 2000"))
        await asyncio.sleep(1)
        await s.rollback()

async def tx2_committed(engine):
    await asyncio.sleep(0.5)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        r = await s.execute(text("SELECT balance FROM accounts"))
        print(f"READ COMMITTED: {r.scalar()} (ожидаем 1000)")

async def main():
    print("DIRTY READ")
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        await setup(engine)
        await asyncio.gather(tx1_uncommitted(engine), tx2_uncommitted(engine))
        await setup(engine)
        await asyncio.gather(tx1_committed(engine), tx2_committed(engine))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

