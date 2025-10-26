"""
Демонстрация non-repeatable read и его решения

Non-repeatable read - при повторном чтении в рамках одной транзакции
данные изменились из-за коммита другой транзакции
"""
import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/hw4_db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def transaction1_read_committed(session: AsyncSession):
    """Транзакция 1: читает дважды с READ COMMITTED"""
    print("T1: Начинаем транзакцию с READ COMMITTED")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    price1 = result.scalar()
    print(f"T1: Первое чтение: цена = {price1}")

    await asyncio.sleep(2)

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    price2 = result.scalar()
    print(f"T1: Второе чтение: цена = {price2}")

    if price1 != price2:
        print(f"T1: NON-REPEATABLE READ! Цена изменилась с {price1} на {price2}")

    await session.commit()


async def transaction2_updater(session: AsyncSession):
    """Транзакция 2: обновляет данные"""
    await asyncio.sleep(1)

    print("T2: Обновляем цену")
    await session.execute(text("UPDATE items SET price = 200.00 WHERE id = 1"))
    await session.commit()
    print("T2: Изменения закоммичены")


async def transaction1_repeatable_read(session: AsyncSession):
    """Транзакция 1: читает дважды с REPEATABLE READ"""
    print("\nT1: Начинаем транзакцию с REPEATABLE READ")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    price1 = result.scalar()
    print(f"T1: Первое чтение: цена = {price1}")

    await asyncio.sleep(2)

    result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
    price2 = result.scalar()
    print(f"T1: Второе чтение: цена = {price2}")

    if price1 == price2:
        print(f"T1: Данные стабильны: цена = {price1} (нет non-repeatable read)")

    await session.commit()


async def demo_non_repeatable_read():
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ: Non-Repeatable Read при READ COMMITTED")
    print("=" * 60)

    # Сбрасываем цену
    async with async_session_maker() as session:
        await session.execute(text("UPDATE items SET price = 100.00 WHERE id = 1"))
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        await asyncio.gather(
            transaction1_read_committed(session1),
            transaction2_updater(session2)
        )


async def demo_no_non_repeatable_read():
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ: Нет Non-Repeatable Read при REPEATABLE READ")
    print("=" * 60)

    # Сбрасываем цену
    async with async_session_maker() as session:
        await session.execute(text("UPDATE items SET price = 100.00 WHERE id = 1"))
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        await asyncio.gather(
            transaction1_repeatable_read(session1),
            transaction2_updater(session2)
        )


async def main():
    # Создаем тестовую запись
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM items WHERE id = 1"))
        await session.execute(text("INSERT INTO items (id, name, price) VALUES (1, 'Test Item', 100.00)"))
        await session.commit()

    await demo_non_repeatable_read()
    await demo_no_non_repeatable_read()


if __name__ == "__main__":
    asyncio.run(main())
