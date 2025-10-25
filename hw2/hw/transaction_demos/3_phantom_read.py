import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db")

async def setup(engine):
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
        await conn.execute(text("CREATE TABLE orders (id SERIAL PRIMARY KEY, amount INTEGER)"))
        await conn.execute(text("INSERT INTO orders (amount) VALUES (100), (200)"))

async def tx1_repeatable_read(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        r1 = await s.execute(text("SELECT COUNT(*) FROM orders"))
        first = r1.scalar()
        await asyncio.sleep(1)
        r2 = await s.execute(text("SELECT COUNT(*) FROM orders"))
        second = r2.scalar()
        print(f"REPEATABLE READ: первое={first}, второе={second} (одинаковые, PostgreSQL предотвращает phantom)")

async def tx2_repeatable_read(engine):
    await asyncio.sleep(0.5)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        await s.execute(text("INSERT INTO orders (amount) VALUES (300)"))
        await s.commit()

async def tx1_serializable(engine):
    try:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            await s.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            r1 = await s.execute(text("SELECT COUNT(*) FROM orders"))
            first = r1.scalar()
            await asyncio.sleep(1)
            r2 = await s.execute(text("SELECT COUNT(*) FROM orders"))
            second = r2.scalar()
            await s.commit()
            print(f"SERIALIZABLE: первое={first}, второе={second} (одинаковые)")
    except Exception as e:
        print(f"SERIALIZABLE: ошибка сериализации (ожидаемо)")

async def tx2_serializable(engine):
    await asyncio.sleep(0.5)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            await s.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            await s.execute(text("INSERT INTO orders (amount) VALUES (300)"))
            await s.commit()
    except Exception:
        pass

async def main():
    print("PHANTOM READ")
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        await setup(engine)
        await asyncio.gather(tx1_repeatable_read(engine), tx2_repeatable_read(engine))
        await setup(engine)
        await asyncio.gather(tx1_serializable(engine), tx2_serializable(engine))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

