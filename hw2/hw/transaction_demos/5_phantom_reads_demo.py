import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")

def demo_phantom_reads_attempt():
    """
    Попытка продемонстрировать phantom reads на уровне REPEATABLE READ.
    В PostgreSQL это НЕ сработает - phantom reads невозможны даже на этом уровне.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Попытка phantom reads на уровне REPEATABLE READ")
    print("="*80)
    print("\nВАЖНО: В PostgreSQL phantom reads невозможны на уровне REPEATABLE READ!")
    print("PostgreSQL использует snapshot isolation, который строже стандарта SQL.\n")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    # Создаем тестовую таблицу
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_phantom"))
        conn.execute(text("""
            CREATE TABLE test_phantom (
                id INTEGER PRIMARY KEY,
                balance FLOAT
            )
        """))
        # Начальные данные: две строки с балансом > 500
        conn.execute(text("INSERT INTO test_phantom (id, balance) VALUES (1, 1000.0)"))
        conn.execute(text("INSERT INTO test_phantom (id, balance) VALUES (2, 800.0)"))
        conn.commit()

    print("Начальное состояние: 2 строки с balance > 500\n")

    results = {
        'transaction1_first_count': None,
        'transaction1_second_count': None,
        'transaction2_inserted': False
    }

    def transaction1_reader():
        """Транзакция 1: Выполняет один и тот же запрос дважды"""
        session = SessionLocal()
        try:
            # Устанавливаем уровень изоляции REPEATABLE READ
            session.execute(text("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

            print("[Транзакция 1] Начало транзакции с уровнем REPEATABLE READ")

            # Первый запрос: считаем строки с balance > 500
            result = session.execute(text("SELECT COUNT(*) FROM test_phantom WHERE balance > 500")).fetchone()
            count1 = result[0] if result else 0
            results['transaction1_first_count'] = count1
            print(f"[Транзакция 1] Первый запрос: найдено {count1} строк с balance > 500")

            print("[Транзакция 1] Ожидание 2 секунды, пока транзакция 2 добавит новую строку...")
            time.sleep(2)

            # Второй запрос: снова считаем строки с balance > 500
            result = session.execute(text("SELECT COUNT(*) FROM test_phantom WHERE balance > 500")).fetchone()
            count2 = result[0] if result else 0
            results['transaction1_second_count'] = count2
            print(f"[Транзакция 1] Второй запрос: найдено {count2} строк с balance > 500")

            session.commit()
            print("[Транзакция 1] Транзакция закоммичена")
        except Exception as e:
            print(f"[Транзакция 1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2_writer():
        """Транзакция 2: Добавляет новую строку между двумя запросами транзакции 1"""
        session = SessionLocal()
        try:
            print("[Транзакция 2] Ожидание 1 секунду перед началом...")
            time.sleep(1)

            session.execute(text("BEGIN"))
            print("[Транзакция 2] Начало транзакции")

            # Добавляем новую строку, удовлетворяющую условию balance > 500
            session.execute(text("INSERT INTO test_phantom (id, balance) VALUES (3, 1500.0)"))
            results['transaction2_inserted'] = True
            print("[Транзакция 2] Добавлена новая строка: id=3, balance=1500.0")

            # Коммитим изменения
            session.commit()
            print("[Транзакция 2] Транзакция ЗАКОММИЧЕНА")
            print("[Транзакция 2] Но транзакция 1 НЕ должна увидеть эту новую строку!")
        except Exception as e:
            print(f"[Транзакция 2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1_reader)
    t2 = threading.Thread(target=transaction2_writer)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Проверяем финальное состояние
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM test_phantom WHERE balance > 500")).fetchone()
        final_count = result[0] if result else 0

    print("\n" + "-"*80)
    print("РЕЗУЛЬТАТЫ:")
    print("-"*80)
    print(f"Транзакция 1, первый запрос: {results['transaction1_first_count']} строк")
    print(f"Транзакция 2 добавила новую строку: {'Да' if results['transaction2_inserted'] else 'Нет'}")
    print(f"Транзакция 1, второй запрос: {results['transaction1_second_count']} строк")
    print(f"Финальное количество строк в БД: {final_count}")
    print()

    if results['transaction1_first_count'] != results['transaction1_second_count']:
        print("⚠️  PHANTOM READ ПРОИЗОШЕЛ!")
        print("   Транзакция 1 выполнила один и тот же запрос дважды,")
        print("   но получила разное количество строк:")
        print(f"   - Первый запрос: {results['transaction1_first_count']} строк")
        print(f"   - Второй запрос: {results['transaction1_second_count']} строк")
        print("\n   Это означает, что появилась 'фантомная' строка.")
    else:
        print("✓  PHANTOM READ НЕ ПРОИЗОШЕЛ!")
        print("   Транзакция 1 выполнила один и тот же запрос дважды")
        print("   и получила одинаковое количество строк оба раза:")
        print(f"   - Первый запрос: {results['transaction1_first_count']} строк")
        print(f"   - Второй запрос: {results['transaction1_second_count']} строк")
        print("\n   PostgreSQL защитил от phantom reads благодаря snapshot isolation,")
        print("   хотя по стандарту SQL это не гарантируется на уровне REPEATABLE READ.")

    # Очистка
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_phantom"))
        conn.commit()

    print("\nВЫВОД: В PostgreSQL phantom reads невозможны даже на уровне REPEATABLE READ.\n")


if __name__ == "__main__":
    demo_phantom_reads_attempt()
