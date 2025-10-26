"""
Демонстрация phantom reads и его решения

Phantom reads - при повторном запросе в рамках одной транзакции
появляются новые строки, добавленные другой транзакцией
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


async def transaction1_repeatable_read(session: AsyncSession):
    """Транзакция 1: делает два SELECT с REPEATABLE READ"""
    print("T1: Начинаем транзакцию с REPEATABLE READ")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

    result = await session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50"))
    count1 = result.scalar()
    print(f"T1: Первый запрос: найдено {count1} товаров с ценой > 50")

    await asyncio.sleep(2)

    result = await session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50"))
    count2 = result.scalar()
    print(f"T1: Второй запрос: найдено {count2} товаров с ценой > 50")

    if count1 != count2:
        print(f"T1: PHANTOM READ! Количество изменилось с {count1} на {count2}")
    else:
        print(f"T1: Данные стабильны: {count1} товаров (нет phantom reads)")

    await session.commit()


async def transaction2_inserter(session: AsyncSession):
    """Транзакция 2: добавляет новую запись"""
    await asyncio.sleep(1)

    print("T2: Добавляем новый товар с ценой 100")
    await session.execute(
        text("INSERT INTO items (name, price) VALUES ('New Item', 100.00)")
    )
    await session.commit()
    print("T2: Товар добавлен и закоммичен")


async def transaction1_serializable(session: AsyncSession):
    """Транзакция 1: делает два SELECT с SERIALIZABLE"""
    print("\nT1: Начинаем транзакцию с SERIALIZABLE")
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

    result = await session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50"))
    count1 = result.scalar()
    print(f"T1: Первый запрос: найдено {count1} товаров с ценой > 50")

    await asyncio.sleep(2)

    result = await session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50"))
    count2 = result.scalar()
    print(f"T1: Второй запрос: найдено {count2} товаров с ценой > 50")

    if count1 == count2:
        print(f"T1: Данные стабильны: {count1} товаров (нет phantom reads)")

    await session.commit()


async def demo_phantom_reads():
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ: Phantom Reads при REPEATABLE READ")
    print("=" * 60)

    # Очищаем и добавляем начальные данные
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM cart_items"))
        await session.execute(text("DELETE FROM items"))
        await session.execute(text("INSERT INTO items (id, name, price) VALUES (1, 'Item 1', 100.00)"))
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        try:
            await asyncio.gather(
                transaction1_repeatable_read(session1),
                transaction2_inserter(session2)
            )
        except Exception as e:
            print(f"Ошибка: {e}")


async def demo_no_phantom_reads():
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ: Нет Phantom Reads при SERIALIZABLE")
    print("=" * 60)

    # Очищаем и добавляем начальные данные
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM cart_items"))
        await session.execute(text("DELETE FROM items"))
        await session.execute(text("INSERT INTO items (id, name, price) VALUES (1, 'Item 1', 100.00)"))
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        try:
            await asyncio.gather(
                transaction1_serializable(session1),
                transaction2_inserter(session2)
            )
        except Exception as e:
            print(f"Транзакция отклонена из-за конфликта сериализации: {e}")


async def main():
    await demo_phantom_reads()
    await demo_no_phantom_reads()

    print("\n" + "=" * 60)
    print("ЗАМЕТКА: В PostgreSQL:")
    print("- REPEATABLE READ предотвращает phantom reads")
    print("- SERIALIZABLE обеспечивает полную изоляцию")
    print("- При конфликтах SERIALIZABLE откатывает транзакцию")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
