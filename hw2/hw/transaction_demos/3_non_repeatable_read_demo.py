import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")

def demo_non_repeatable_read():
    """
    Демонстрация non-repeatable read на уровне READ COMMITTED.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Non-repeatable read на уровне READ COMMITTED")
    print("="*80)
    print("\nNon-repeatable read - это когда одна транзакция читает строку дважды,")
    print("но получает разные значения из-за изменений другой транзакции.\n")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    # Создаем тестовую таблицу
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_non_repeatable"))
        conn.execute(text("""
            CREATE TABLE test_non_repeatable (
                id INTEGER PRIMARY KEY,
                balance FLOAT
            )
        """))
        conn.execute(text("INSERT INTO test_non_repeatable (id, balance) VALUES (1, 1000.0)"))
        conn.commit()

    print("Начальное состояние: balance = 1000.0\n")

    results = {
        'transaction1_first_read': None,
        'transaction1_second_read': None,
        'transaction2_updated_to': None
    }

    def transaction1_reader():
        """Транзакция 1: Читает данные дважды"""
        session = SessionLocal()
        try:
            session.execute(text("BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED"))

            print("[Транзакция 1] Начало транзакции с уровнем READ COMMITTED")

            # Первое чтение
            result = session.execute(text("SELECT balance FROM test_non_repeatable WHERE id = 1")).fetchone()
            balance1 = result[0] if result else None
            results['transaction1_first_read'] = balance1
            print(f"[Транзакция 1] Первое чтение: balance = {balance1}")

            print("[Транзакция 1] Ожидание 2 секунды, пока транзакция 2 изменит и закоммитит данные...")
            time.sleep(2)

            # Второе чтение той же строки
            result = session.execute(text("SELECT balance FROM test_non_repeatable WHERE id = 1")).fetchone()
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
            session.execute(text("UPDATE test_non_repeatable SET balance = 2000.0 WHERE id = 1"))
            results['transaction2_updated_to'] = 2000.0
            print("[Транзакция 2] Изменено значение на 2000.0")

            # Коммитим изменения (это ключевой момент!)
            session.commit()
            print("[Транзакция 2] Транзакция ЗАКОММИЧЕНА")
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
        result = conn.execute(text("SELECT balance FROM test_non_repeatable WHERE id = 1")).fetchone()
        final_balance = result[0] if result else None

    print("\n" + "-"*80)
    print("РЕЗУЛЬТАТЫ:")
    print("-"*80)
    print(f"Транзакция 1, первое чтение: {results['transaction1_first_read']}")
    print(f"Транзакция 2 изменила значение на: {results['transaction2_updated_to']} и закоммитила")
    print(f"Транзакция 1, второе чтение: {results['transaction1_second_read']}")
    print(f"Финальное значение в БД: {final_balance}")
    print()

    if results['transaction1_first_read'] != results['transaction1_second_read']:
        print("⚠️  NON-REPEATABLE READ ПРОИЗОШЕЛ!")
        print("   Транзакция 1 прочитала одну и ту же строку дважды,")
        print("   но получила разные значения:")
        print(f"   - Первое чтение: {results['transaction1_first_read']}")
        print(f"   - Второе чтение: {results['transaction1_second_read']}")
        print("\n   Это нормальное поведение для уровня READ COMMITTED.")
    else:
        print("✓  Non-repeatable read НЕ произошел.")
        print("   Оба чтения вернули одинаковое значение.")

    # Очистка
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_non_repeatable"))
        conn.commit()

    print("\nВЫВОД: На уровне READ COMMITTED возможны non-repeatable reads.\n")


if __name__ == "__main__":
    demo_non_repeatable_read()
