import asyncio
from sqlalchemy import text
from scripts.common import async_session

# Этот скрипт демонстрирует,  что в PostgreSQL невозможно прочитать
# незафиксированные данные другой транзакции — даже если явно запросить
# уровень изоляции READ UNCOMMITTED.

# Причина  проста: PostgreSQL игнорирует READ UNCOMMITTED  и  всегда работает
# как минимум на уровне READ COMMITTED. Это делает СУБД устойчивой к
# так называемому "грязному чтению" (dirty read) по умолчанию.


async def demonstrate_dirty_read_impossibility():

    # две независимые сессии: одна пишет, другая пытается читать
    async with async_session() as writer, async_session() as reader:

        # Подготовка чистой таблицы
        await writer.execute(text("DROP TABLE IF EXISTS test_table;"))
        await writer.execute(text("CREATE TABLE test_table (id SERIAL PRIMARY KEY, value INT);"))
        await writer.commit()
        print("Тестовая таблица готова к работе.")

        # Транзакция "писателя":  добавляет значение, но не сохраняет
        await writer.execute(
            text("BEGIN;"),
            execution_options={"isolation_level": "READ UNCOMMITTED"}
        )
        await writer.execute(text("INSERT INTO test_table (value) VALUES (777);"))
        print("Писатель: добавил значение 777, но пока не подтвердил изменения.")

        # транзакция "читателя": пытается увидеть незафиксированные данные
        await reader.execute(
            text("BEGIN;"),
            execution_options={"isolation_level": "READ UNCOMMITTED"}
        )
        result = await reader.execute(text("SELECT value FROM test_table;"))
        value = result.scalar()
        status = str(value) if value is not None else "ничего не обнаружено"
        print(f"Читатель (в режиме READ UNCOMMITTED): {status}")

        # Отменяем изменения -  данные исчезают
        await writer.execute(text("ROLLBACK;"))
        print("Писатель: отменил все изменения — значение 777 больше не существует.")

        # Проверяем состояние таблицы уже на безопасном уровне изоляции
        await reader.execute(
            text("BEGIN;"),
            execution_options={"isolation_level": "READ COMMITTED"}
        )
        result = await reader.execute(text("SELECT value FROM test_table;"))
        value = result.scalar()
        status = str(value) if value is not None else "таблица осталась пустой"
        print(f"Читатель (в режиме READ COMMITTED): {status}")

        print("\nИтог: так же и  при попытке использовать READ UNCOMMITTED,")
        print("PostgreSQL не показывает незафиксированные данные —")
        print("грязное чтение в ней не должно быть(в теории).")


if __name__ == "__main__":
    asyncio.run(demonstrate_dirty_read_impossibility())
    