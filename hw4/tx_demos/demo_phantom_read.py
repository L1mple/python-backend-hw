import asyncio
from sqlalchemy import text
from tx_demos.db_setup import prepare, engine


async def phantom_demo(isolation_level: str):
    async with engine.connect() as conn1:
        trans1 = await conn1.begin()
        try:
            await conn1.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            print(f"\n=== Уровень изоляции: {isolation_level} ===")

            print("[T1] Выполняю первый подсчет записей, где deleted = FALSE")
            res1 = await conn1.execute(text("SELECT COUNT(*) FROM items WHERE deleted = FALSE"))
            c1 = res1.first()[0]
            print(f"[T1] Количество записей при первом чтении: {c1}")

            async with engine.connect() as conn2:
                trans2 = await conn2.begin()
                try:
                    print("[T2] Добавляю новую запись (deleted = FALSE) и фиксирую изменения")
                    await conn2.execute(
                        text("INSERT INTO items (name, price, deleted) VALUES ('PhantomItem', 50.0, FALSE)")
                    )
                    await trans2.commit()
                    print("[T2] Транзакция зафиксирована")
                except Exception as e:
                    await trans2.rollback()
                    print(f"[T2] Ошибка: {e}. Транзакция отменена")

            print("[T1] Повторяю подсчет записей, где deleted = FALSE, после фиксации второй транзакции")
            res2 = await conn1.execute(text("SELECT COUNT(*) FROM items WHERE deleted = FALSE"))
            c2 = res2.first()[0]
            print(f"[T1] Количество записей при втором чтении: {c2}")

            if c1 != c2:
                print("[T1] Обнаружено phantom read (в результате появилась новая запись)")
            else:
                print("[T1] Phantom read не зафиксировано, результаты совпадают")

            await trans1.commit()
            print("[T1] Транзакция зафиксирована")
        except Exception as e:
            await trans1.rollback()
            print(f"[T1] Ошибка: {e}. Транзакция отменена")


async def main():
    print("Подготовка базы данных: создание таблиц и начальных данных")
    await prepare()

    print("\n--- Демонстрация phantom read (READ COMMITTED) ---")
    await phantom_demo("READ COMMITTED")

    print("\n--- Демонстрация предотвращения phantom read (REPEATABLE READ) ---")
    await phantom_demo("REPEATABLE READ")

    print("\n--- Полная изоляция (SERIALIZABLE) ---")
    await phantom_demo("SERIALIZABLE")

    print("\nЗавершено")


if __name__ == "__main__":
    asyncio.run(main())
