import asyncio
from sqlalchemy import text
from scripts.common import async_session

# Этот скрипт демонстрирует "фантомное чтение" (phantom read) —
# ситуацию, когда при повторном выполнении одного и того же запроса
# в рамках одной транзакции появляются новые строки, вставленные
# другой транзакцией.

# В PostgreSQL:
#   - На уровне READ COMMITTED фантомы возможны.
#   - На уровнях REPEATABLE READ и SERIALIZABLE — фантомы не должны возникать,
#     потому что PostgreSQL использует snapshot isolation.(насколько я знаю и понимаю)

# поэтому  сначала покажу фантом на READ COMMITTED,
# а затем, что его нет на REPEATABLE READ.

async def demonstrate_phantom_reads():

    # Часть 1: READ COMMITTED
    async with async_session() as main_tx:
        # Подготовка таблицы 
        await main_tx.execute(text("DROP TABLE IF EXISTS test_table;"))
        await main_tx.execute(text("CREATE TABLE test_table (id SERIAL PRIMARY KEY, value INT);"))
        await main_tx.execute(text("INSERT INTO test_table (value) VALUES (55);"))
        await main_tx.commit()
        print("Таблица создана, в ней одна запись со значением 55.")

        # Отдельная сессия для наблюдателя
        async with async_session() as obs:
            # Явно начинаю транзакцию с нужным уровнем через SQL
            await obs.execute(text("BEGIN ISOLATION LEVEL READ COMMITTED;"))

            result = await obs.execute(text("SELECT COUNT(*) FROM test_table;"))
            count1 = result.scalar()
            print(f"READ COMMITTED — первое количество строк: {count1}")

            # Другая транзакция добавляет строку
            await main_tx.execute(text("INSERT INTO test_table (value) VALUES (888);"))
            await main_tx.commit()
            print("Основная транзакция добавила новую строку со значением 888.")

            result = await obs.execute(text("SELECT COUNT(*) FROM test_table;"))
            count2 = result.scalar()
            print(f"READ COMMITTED — второе количество строк: {count2}")

            if count2 > count1:
                print(" Обнаружено фантомное чтение: появилась новая строка!")
            else:
                print("Фантомное чтение не обнаружено.")

            await obs.execute(text("ROLLBACK;"))


    # Часть 2: REPEATABLE READ
    async with async_session() as main_tx2:
        # Убедимся, что таблица чистая
        await main_tx2.execute(text("DELETE FROM test_table WHERE value = 888;"))
        await main_tx2.commit()
        print("\nТаблица снова содержит только одну запись (55).")

        async with async_session() as obs2:
            # КЛЮЧЕВОЕ: используем BEGIN с указанием уровня изоляции ВНУТРИ SQL
            await obs2.execute(text("BEGIN ISOLATION LEVEL REPEATABLE READ;"))

            result = await obs2.execute(text("SELECT COUNT(*) FROM test_table;"))
            count1 = result.scalar()
            print(f"REPEATABLE READ — первое количество строк: {count1}")

            # Добавляем новую строку извне
            await main_tx2.execute(text("INSERT INTO test_table (value) VALUES (888);"))
            await main_tx2.commit()
            print("Основная транзакция снова добавила строку (888).")

            result = await obs2.execute(text("SELECT COUNT(*) FROM test_table;"))
            count2 = result.scalar()
            print(f"REPEATABLE READ — второе количество строк: {count2}")

            if count2 == count1:
                print("Фантомное чтение отсутствует: количество строк не изменилось.")
            else:
                print("Фантом обнаружен (в postgreSQL такого быть не должно).")

            await obs2.execute(text("ROLLBACK;"))

    print("\nВывод:")
    print("- В PostgreSQL фантомное чтение возможно только на уровне READ COMMITTED.")
    print("- На уровнях REPEATABLE READ и SERIALIZABLE оно блокируется автоматически.")
    print("- Это делает PostgreSQL более строгим, чем требует стандарт SQL.")


if __name__ == "__main__":
    asyncio.run(demonstrate_phantom_reads())
