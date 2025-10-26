"""
Демонстрация dirty read и его решения

Dirty read - чтение незакоммиченных данных из другой транзакции
"""
import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/hw4_db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def transaction1_dirty(session: AsyncSession):
    """Транзакция 1: обновляет цену, но не коммитит сразу"""
    print("T1: Начинаем транзакцию с READ UNCOMMITTED")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    original = result.scalar()
    print(f"T1: Исходная цена: {original}")

    await session.execute(text("UPDATE items SET price = 999.99 WHERE id = 1"))
    print("T1: Обновили цену на 999.99 (не закоммитили)")

    await asyncio.sleep(2)

    print("T1: Откатываем транзакцию")
    await session.rollback()


async def transaction2_dirty(session: AsyncSession):
    """Транзакция 2: пытается прочитать незакоммиченные данные"""
    await asyncio.sleep(1)

    print("T2: Начинаем транзакцию с READ UNCOMMITTED")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    price = result.scalar()
    print(f"T2: DIRTY READ! Прочитали цену: {price} (транзакция 1 не закоммитила)")

    await session.commit()


async def transaction1_fixed(session: AsyncSession):
    """Транзакция 1 с READ COMMITTED"""
    print("\nT1: Начинаем транзакцию с READ COMMITTED")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    original = result.scalar()
    print(f"T1: Исходная цена: {original}")

    await session.execute(text("UPDATE items SET price = 999.99 WHERE id = 1"))
    print("T1: Обновили цену на 999.99 (не закоммитили)")

    await asyncio.sleep(2)

    print("T1: Откатываем транзакцию")
    await session.rollback()


async def transaction2_fixed(session: AsyncSession):
    """Транзакция 2 с READ COMMITTED - не видит незакоммиченные данные"""
    await asyncio.sleep(1)

    print("T2: Начинаем транзакцию с READ COMMITTED")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    price = result.scalar()
    print(f"T2: Прочитали цену: {price} (видим только закоммиченные данные)")

    await session.commit()


async def demo_dirty_read():
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ: Dirty Read при READ UNCOMMITTED")
    print("=" * 60)

    async with async_session_maker() as session1, async_session_maker() as session2:
        await asyncio.gather(
            transaction1_dirty(session1),
            transaction2_dirty(session2)
        )


async def demo_no_dirty_read():
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ: Нет Dirty Read при READ COMMITTED")
    print("=" * 60)

    async with async_session_maker() as session1, async_session_maker() as session2:
        await asyncio.gather(
            transaction1_fixed(session1),
            transaction2_fixed(session2)
        )


async def main():
    # Создаем тестовую запись
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM items WHERE id = 1"))
        await session.execute(text("INSERT INTO items (id, name, price) VALUES (1, 'Test Item', 100.00)"))
        await session.commit()

    # PostgreSQL не поддерживает READ UNCOMMITTED, поэтому ведет себя как READ COMMITTED
    # Но для демонстрации покажем попытку
    await demo_dirty_read()
    await demo_no_dirty_read()

    print("\n" + "=" * 60)
    print("ВАЖНО: PostgreSQL не поддерживает READ UNCOMMITTED")
    print("Даже при установке READ UNCOMMITTED работает как READ COMMITTED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
