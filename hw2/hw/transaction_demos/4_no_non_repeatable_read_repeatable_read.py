import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")

def demo_no_non_repeatable_read():
    """
    Демонстрация отсутствия non-repeatable read на уровне REPEATABLE READ.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Отсутствие non-repeatable read на уровне REPEATABLE READ")
    print("="*80)
    print("\nREPEATABLE READ - транзакция видит снимок данных на момент первого запроса.")
    print("Повторные чтения одной строки всегда возвращают одинаковый результат.\n")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    # Создаем тестовую таблицу
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_repeatable_read"))
        conn.execute(text("""
            CREATE TABLE test_repeatable_read (
                id INTEGER PRIMARY KEY,
                balance FLOAT
            )
        """))
        conn.execute(text("INSERT INTO test_repeatable_read (id, balance) VALUES (1, 1000.0)"))
        conn.commit()

    print("Начальное состояние: balance = 1000.0\n")

    results = {
        'transaction1_first_read': None,
        'transaction1_second_read': None,
        'transaction2_updated_to': None
    }

    def transaction1_reader():
        """Транзакция 1: Читает данные дважды на уровне REPEATABLE READ"""
        session = SessionLocal()
        try:
            # Устанавливаем уровень изоляции REPEATABLE READ
            session.execute(text("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

            print("[Транзакция 1] Начало транзакции с уровнем REPEATABLE READ")

            # Первое чтение (создает snapshot)
            result = session.execute(text("SELECT balance FROM test_repeatable_read WHERE id = 1")).fetchone()
            balance1 = result[0] if result else None
            results['transaction1_first_read'] = balance1
            print(f"[Транзакция 1] Первое чтение: balance = {balance1}")
            print("[Транзакция 1] Создан снимок данных (snapshot) на этот момент времени")

            print("[Транзакция 1] Ожидание 2 секунды, пока транзакция 2 изменит данные...")
            time.sleep(2)

            # Второе чтение той же строки
            result = session.execute(text("SELECT balance FROM test_repeatable_read WHERE id = 1")).fetchone()
            balance2 = result[0] if result else None
            results['transaction1_second_read'] = balance2
            print(f"[Транзакция 1] Второе чтение: balance = {balance2}")

            session.commit()
            print("[Транзакция 1] Транзакция закоммичена")
        except Exception as e:
            print(f"[Транзакция 1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2_writer():
        """Транзакция 2: Изменяет данные между двумя чтениями транзакции 1"""
        session = SessionLocal()
        try:
            print("[Транзакция 2] Ожидание 1 секунду перед началом...")
            time.sleep(1)

            session.execute(text("BEGIN"))
            print("[Транзакция 2] Начало транзакции")

            # Изменяем данные
            session.execute(text("UPDATE test_repeatable_read SET balance = 2000.0 WHERE id = 1"))
            results['transaction2_updated_to'] = 2000.0
            print("[Транзакция 2] Изменено значение на 2000.0")

            # Коммитим изменения
            session.commit()
            print("[Транзакция 2] Транзакция ЗАКОММИЧЕНА")
            print("[Транзакция 2] Но транзакция 1 НЕ увидит это изменение!")
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
        result = conn.execute(text("SELECT balance FROM test_repeatable_read WHERE id = 1")).fetchone()
        final_balance = result[0] if result else None

    print("\n" + "-"*80)
    print("РЕЗУЛЬТАТЫ:")
    print("-"*80)
    print(f"Транзакция 1, первое чтение: {results['transaction1_first_read']}")
    print(f"Транзакция 2 изменила значение на: {results['transaction2_updated_to']} и закоммитила")
    print(f"Транзакция 1, второе чтение: {results['transaction1_second_read']}")
    print(f"Финальное значение в БД: {final_balance}")
    print()

    if results['transaction1_first_read'] == results['transaction1_second_read']:
        print("✓  NON-REPEATABLE READ НЕ ПРОИЗОШЕЛ!")
        print("   Транзакция 1 прочитала одну и ту же строку дважды")
        print("   и получила одинаковое значение оба раза:")
        print(f"   - Первое чтение: {results['transaction1_first_read']}")
        print(f"   - Второе чтение: {results['transaction1_second_read']}")
        print("\n   Уровень REPEATABLE READ гарантирует стабильность чтений,")
        print("   используя snapshot isolation (снимок данных).")
    else:
        print("⚠️  ОШИБКА: Non-repeatable read произошел!")
        print("   Это не должно было произойти на уровне REPEATABLE READ.")

    # Очистка
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_repeatable_read"))
        conn.commit()

    print("\nВЫВОД: На уровне REPEATABLE READ non-repeatable reads невозможны.\n")


if __name__ == "__main__":
    demo_no_non_repeatable_read()
