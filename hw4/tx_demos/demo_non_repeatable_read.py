import asyncio
from sqlalchemy import text
from tx_demos.db_setup import prepare, engine


async def non_repeatable_demo(isolation_level: str):
    async with engine.connect() as conn1:
        trans1 = await conn1.begin()
        try:
            await conn1.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            print(f"\n=== Уровень изоляции: {isolation_level} ===")
            print("[T1] Первое чтение значения price из таблицы carts")

            res1 = await conn1.execute(text("SELECT price FROM carts WHERE id = 1"))
            r1 = res1.first()[0]
            print(f"[T1] Результат первого чтения: {r1}")

            async with engine.connect() as conn2:
                trans2 = await conn2.begin()
                try:
                    print("[T2] Обновляю carts.price -> 200 и фиксирую изменения")
                    await conn2.execute(text("UPDATE carts SET price = 200 WHERE id = 1"))
                    await trans2.commit()
                    print("[T2] Транзакция зафиксирована")
                except Exception as e:
                    await trans2.rollback()
                    print(f"[T2] Ошибка: {e}. Транзакция отменена")

            print("[T1] Второе чтение значения price после фиксации изменений во второй транзакции")
            res2 = await conn1.execute(text("SELECT price FROM carts WHERE id = 1"))
            r2 = res2.first()[0]
            print(f"[T1] Результат второго чтения: {r2}")

            if r1 != r2:
                print("[T1] Обнаружено non repeatable read (значение изменилось между запросами)")
            else:
                print("[T1] Значение не изменилось. Non repeatable read не произошло")

            await trans1.commit()
            print("[T1] Транзакция зафиксирована")
        except Exception as e:
            await trans1.rollback()
            print(f"[T1] Ошибка: {e}. Транзакция отменена")


async def main_async():
    print("Подготовка базы данных: создание таблиц и тестовых данных")
    await prepare()

    print("\n--- Демонстрация non repeatable read (READ COMMITTED) ---")
    await non_repeatable_demo("READ COMMITTED")

    print("\n--- Демонстрация предотвращения non repeatable read (REPEATABLE READ) ---")
    await non_repeatable_demo("REPEATABLE READ")

    print("\nЗавершено")


if __name__ == "__main__":
    asyncio.run(main_async())
