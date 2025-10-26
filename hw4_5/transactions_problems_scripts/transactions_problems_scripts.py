import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from config import settings
from models import Base, ItemModel



engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

ITEM_ID = UUID("edf925f2-c112-423a-ac24-a70c6faebffc")
NEW_ITEM_ID_1 = UUID("81e5a9ac-6362-47be-bc33-0d740cac83ca")
NEW_ITEM_ID_2 = UUID("dc90ee64-6010-4d75-9062-7fa1fe387014")


async def setup_test_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession() as session:
        session.add(ItemModel(id=ITEM_ID, name="Тестовый товар", price=100.0, deleted=False))
        await session.commit()


async def demo_1_dirty_read():
    print("\n=== 1. Dirty Read при READ UNCOMMITTED ===")
    print("В PostgreSQL уровень READ UNCOMMITTED автоматически повышается до READ COMMITTED")
    print("→ Грязное чтение НЕВОЗМОЖНО.")

    async with AsyncSession() as s1:
        async with s1.begin():
            await s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            await s1.execute(
                text("UPDATE items SET price = 50 WHERE id = :id"),
                {"id": str(ITEM_ID)}
            )
            print("T1: обновила цену на 50, но не коммитит")

            async with AsyncSession() as s2:
                async with s2.begin():
                    await s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
                    price = (await s2.execute(
                        text("SELECT price FROM items WHERE id = :id"),
                        {"id": str(ITEM_ID)}
                    )).scalar()
                    print(f"T2: прочитала цену = {price} (ожидаемо: 100.0)")

            await s1.rollback()


async def demo_2_no_dirty_read():
    print("\n=== 2. Отсутствие Dirty Read при READ COMMITTED ===")
    async with AsyncSession() as s1:
        async with s1.begin():
            await s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await s1.execute(
                text("UPDATE items SET price = 50 WHERE id = :id"),
                {"id": str(ITEM_ID)}
            )
            print("T1: обновила цену на 50, но не коммитит")

            async with AsyncSession() as s2:
                async with s2.begin():
                    await s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    price = (await s2.execute(
                        text("SELECT price FROM items WHERE id = :id"),
                        {"id": str(ITEM_ID)}
                    )).scalar()
                    print(f"T2: прочитала цену = {price}")  # → 100.0

            await s1.commit()


async def demo_3_non_repeatable_read():
    print("\n=== 3. Non-Repeatable Read при READ COMMITTED ===")
    async with AsyncSession() as s2:
        async with s2.begin():
            await s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            p1 = (await s2.execute(text("SELECT price FROM items WHERE id = :id"), {"id": str(ITEM_ID)})).scalar()
            print(f"T2: первое чтение = {p1}")

            async with AsyncSession() as s1:
                async with s1.begin():
                    await s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    await s1.execute(text("UPDATE items SET price = 200 WHERE id = :id"), {"id": str(ITEM_ID)})
                    await s1.commit()
                    print("T1: обновила и закоммитила")

            p2 = (await s2.execute(text("SELECT price FROM items WHERE id = :id"), {"id": str(ITEM_ID)})).scalar()
            print(f"T2: второе чтение = {p2}")


async def demo_4_no_non_repeatable_read():
    print("\n=== 4. Отсутствие Non-Repeatable Read при REPEATABLE READ ===")
    async with AsyncSession() as s2:
        async with s2.begin():
            await s2.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            p1 = (await s2.execute(text("SELECT price FROM items WHERE id = :id"), {"id": str(ITEM_ID)})).scalar()
            print(f"T2: первое чтение = {p1}")  # → 100.0

            async with AsyncSession() as s1:
                async with s1.begin():
                    await s1.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                    await s1.execute(text("UPDATE items SET price = 200 WHERE id = :id"), {"id": str(ITEM_ID)})
                    await s1.commit()
                    print("T1: обновила и закоммитила")

            p2 = (await s2.execute(text("SELECT price FROM items WHERE id = :id"), {"id": str(ITEM_ID)})).scalar()
            print(f"T2: второе чтение = {p2}")  # → 100.0


async def demo_5_phantom_read():
    print("\n=== 5. Phantom Read при READ COMMITTED ===")
    print("Условие: SELECT с WHERE price < 150")

    async with AsyncSession() as setup_sess:
        async with setup_sess.begin():
            await setup_sess.execute(text("DELETE FROM items"))
            await setup_sess.execute(text("""
                                          INSERT INTO items (id, name, price, deleted)
                                          VALUES ('11111111-1111-1111-1111-111111111111', 'Товар A', 100.0, false)
                                          """))

    async with AsyncSession() as s2:
        async with s2.begin():
            await s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))

            c1 = (await s2.execute(
                text("SELECT COUNT(*) FROM items WHERE price < 150")
            )).scalar()
            print(f"T2: первое количество = {c1}")  # → 1

            async with AsyncSession() as s1:
                async with s1.begin():
                    await s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                    await s1.execute(text("""
                                          INSERT INTO items (id, name, price, deleted)
                                          VALUES (:id, 'Новый товар', 120.0, false)
                                          """), {"id": str(UUID("33333333-3333-3333-3333-333333333333"))})
                    await s1.commit()
                    print("T1: добавила товар с price=120 (в диапазоне)")

            c2 = (await s2.execute(
                text("SELECT COUNT(*) FROM items WHERE price < 150")
            )).scalar()
            print(f"T2: второе количество = {c2}")  # → 2

            if c2 > c1:
                print("Phantom Read обнаружен: появилась новая строка в диапазоне!")


async def demo_6_no_phantom_read():
    print("\n=== 6. Отсутствие Phantom Read при SERIALIZABLE ===")
    async with AsyncSession() as s2:
        async with s2.begin():
            await s2.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            c1 = (await s2.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false"))).scalar()
            print(f"T2: первое количество = {c1}")  # → 2

            async with AsyncSession() as s1:
                async with s1.begin():
                    await s1.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                    await s1.execute(text("""
                        INSERT INTO items (id, name, price, deleted)
                        VALUES (:id, 'Ещё товар', 88.88, false)
                    """), {"id": str(NEW_ITEM_ID_2)})
                    await s1.commit()
                    print("T1: добавила товар")

            try:
                c2 = (await s2.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false"))).scalar()
                print(f"T2: второе количество = {c2}")  # → 2 или ошибка
            except Exception as e:
                print(f"T2: ошибка сериализации (ожидаемо): {type(e).__name__}")


async def main():
    print("Демонстрация уровней изоляции транзакций в PostgreSQL")
    print("Таблицы: items, carts, cart_items")

    await setup_test_data()

    await demo_1_dirty_read()
    await demo_2_no_dirty_read()
    await demo_3_non_repeatable_read()
    await demo_4_no_non_repeatable_read()
    await demo_5_phantom_read()
    await demo_6_no_phantom_read()

    print("\nВсе демонстрации завершены!")


if __name__ == "__main__":
    asyncio.run(main())