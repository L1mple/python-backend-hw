import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db")

async def setup(engine):
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        await conn.execute(text("CREATE TABLE products (id SERIAL PRIMARY KEY, price INTEGER)"))
        await conn.execute(text("INSERT INTO products (price) VALUES (100)"))

async def tx1_read_committed(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        r1 = await s.execute(text("SELECT price FROM products"))
        first = r1.scalar()
        await asyncio.sleep(1)
        r2 = await s.execute(text("SELECT price FROM products"))
        second = r2.scalar()
        print(f"READ COMMITTED: первое={first}, второе={second} (разные значения)")

async def tx2_read_committed(engine):
    await asyncio.sleep(0.5)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("UPDATE products SET price = 200"))
        await s.commit()

async def tx1_repeatable_read(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        r1 = await s.execute(text("SELECT price FROM products"))
        first = r1.scalar()
        await asyncio.sleep(1)
        r2 = await s.execute(text("SELECT price FROM products"))
        second = r2.scalar()
        print(f"REPEATABLE READ: первое={first}, второе={second} (одинаковые)")

async def tx2_repeatable_read(engine):
    await asyncio.sleep(0.5)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("UPDATE products SET price = 200"))
        await s.commit()

async def main():
    print("NON-REPEATABLE READ")
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        await setup(engine)
        await asyncio.gather(tx1_read_committed(engine), tx2_read_committed(engine))
        await setup(engine)
        await asyncio.gather(tx1_repeatable_read(engine), tx2_repeatable_read(engine))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

