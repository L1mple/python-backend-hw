import asyncio
from sqlalchemy import text
from scripts.common import async_session

# Этот скрипт показывает разницу между двумя уровнями изоляции транзакций в PostgreSQL:

# 1. READ COMMITTED — стандартный уровень, при котором транзакция может увидеть
#    изменения, сделанные другими транзакциями после начала своей работы.
#    Это приводит к так называемому "неповторяемому чтению" (non-repeatable read).

# 2. REPEATABLE READ — более строгий уровень, при котором транзакция видит
#    данные "на момент начала", и даже если другие транзакции что-то изменят,
#    эти изменения не будут видны до конца текущей транзакции.

# Мы создадим тестовую таблицу, вставим в неё число 100,
# а затем попробуем прочитать его дважды — сначала на уровне READ COMMITTED,
# потом на уровне REPEATABLE READ — и посмотрим, изменится ли результат
# после того, как другая транзакция обновит это число.

async def non_repeatable_read_demo():

    # oсновная сессия — она будет вносить изменения извне
    async with async_session() as main_session:
        
        # Подготавливаем чистую таблицу для теста
        await main_session.execute(text("DROP TABLE IF EXISTS test_table;"))
        await main_session.execute(text("CREATE TABLE test_table (id SERIAL PRIMARY KEY, value INT);"))
        await main_session.execute(text("INSERT INTO test_table (value) VALUES (100);"))
        await main_session.commit()
        print("Таблица создана, значение 100 вставлено и зафиксировано.")

        # --------------------------------------------------
        # Часть 1: тестируем уровень READ COMMITTED
        # --------------------------------------------------
        # Создаём отдельную транзакцию, которая будет читать данные
        async with async_session() as tx1:
            # Говорим PostgreSQL: используй уровень изоляции "read committed"
            await tx1.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;"))
            # Начинаем транзакцию
            await tx1.execute(text("BEGIN;"))

            # Читаем значение в первый раз
            first = await tx1.execute(text("SELECT value FROM test_table;"))
            print("READ COMMITTED — первое чтение:", first.scalar())  # должно быть 100

            # Теперь основная сессия (другая транзакция) меняет значение на 300 и сохраняет
            await main_session.execute(text("UPDATE test_table SET value = 300;"))
            await main_session.commit()
            print("Значение обновлено до 300 (извне)")

            # Читаем то же значение второй раз в той же транзакции
            second = await tx1.execute(text("SELECT value FROM test_table;"))
            print("READ COMMITTED — второе чтение:", second.scalar())  # будет 300 — данные изменились!

            # завершаем транзакцию без сохранения (хотя мы только читали)
            await tx1.execute(text("ROLLBACK;"))

        # Возвращаем значение обратно к 100, чтобы начать следующий тест с чистого листа
        await main_session.execute(text("UPDATE test_table SET value = 100;"))
        await main_session.commit()
        print("\nЗначение сброшено до 100 для следующего теста.")

        # --------------------------------------------------
        # Часть 2: тестируем уровень REPEATABLE READ
        # --------------------------------------------------
        # Создаём новую, независимую транзакцию
        async with async_session() as tx2:
            # Теперь просим PostgreSQL использовать более строгий уровень — "repeatable read"
            await tx2.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;"))
            await tx2.execute(text("BEGIN;"))

            # Первое чтение
            first = await tx2.execute(text("SELECT value FROM test_table;"))
            print("REPEATABLE READ — первое чтение:", first.scalar())  # 100

            # Снова меняем значение извне на 300
            await main_session.execute(text("UPDATE test_table SET value = 300;"))
            await main_session.commit()
            print("Значение снова обновлено до 300 (извне)")

            # Второе чтение в той же транзакции
            second = await tx2.execute(text("SELECT value FROM test_table;"))
            # На этот раз результат останется 100, потому что транзакция "не видит"
            # изменений, произошедших после её первого чтения
            print("REPEATABLE READ — второе чтение:", second.scalar())  # всё ещё 100!

            await tx2.execute(text("ROLLBACK;"))

        print("\n Демонстрация завершена.")


if __name__ == "__main__":
    asyncio.run(non_repeatable_read_demo())
    