import asyncio
from sqlalchemy import text
from tx_demos.db_setup import prepare, engine


async def dirty_read_demo(isolation_level: str):
    async with engine.connect() as conn1:
        trans1 = await conn1.begin()
        try:
            await conn1.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            print(f"[T1] Установлен уровень изоляции: {isolation_level}. Обновляю carts.price -> 999 (без фиксации)")
            await conn1.execute(text("UPDATE carts SET price = 999 WHERE id = 1"))

            async with engine.connect() as conn2:
                trans2 = await conn2.begin()
                try:
                    await conn2.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
                    print("[T2] Выполняю чтение значения price для корзины с id = 1")
                    res = await conn2.execute(text("SELECT price FROM carts WHERE id = 1"))
                    row = res.first()
                    print(f"[T2] Получено значение price: {row[0] if row else 'нет данных'}")
                    await trans2.commit()
                    print("[T2] Транзакция зафиксирована")
                except Exception as e:
                    await trans2.rollback()
                    print(f"[T2] Ошибка: {e}. Транзакция отменена")

            print("[T1] Отменяю изменения, фиксации не будет")
            await trans1.rollback()
        except Exception as e:
            print(f"[T1] Ошибка: {e}. Транзакция отменена")
            await trans1.rollback()


async def main():
    print("Подготовка базы данных: создание таблиц и тестовых данных")
    await prepare()

    print("\n=== Демонстрация dirty read (READ UNCOMMITTED) ===")
    await dirty_read_demo("READ UNCOMMITTED")

    print("\n=== Демонстрация без dirty read (READ COMMITTED) ===")
    await dirty_read_demo("READ COMMITTED")

    print("\nЗавершено")


if __name__ == "__main__":
    asyncio.run(main())
