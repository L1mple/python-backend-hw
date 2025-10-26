import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")

def demo_dirty_read_attempt():
    """
    Попытка продемонстрировать dirty read на уровне READ UNCOMMITTED.
    В PostgreSQL это не сработает - dirty read невозможны.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Попытка dirty read на уровне READ UNCOMMITTED")
    print("="*80)
    print("\nВАЖНО: PostgreSQL не поддерживает READ UNCOMMITTED.")
    print("Даже при указании этого уровня используется READ COMMITTED,")
    print("который предотвращает dirty reads.\n")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    # Создаем тестовую таблицу
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_dirty_read"))
        conn.execute(text("""
            CREATE TABLE test_dirty_read (
                id INTEGER PRIMARY KEY,
                balance FLOAT
            )
        """))
        conn.execute(text("INSERT INTO test_dirty_read (id, balance) VALUES (1, 1000.0)"))
        conn.commit()

    print("Начальное состояние: balance = 1000.0\n")

    results = {'transaction1_read': None, 'transaction2_changed_to': None}

    def transaction1_reader():
        """Транзакция 1: Пытается прочитать незакоммиченные данные"""
        session = SessionLocal()
        try:
            # Устанавливаем уровень изоляции READ UNCOMMITTED
            # (PostgreSQL автоматически использует READ COMMITTED)
            session.execute(text("BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))

            print("[Транзакция 1] Начало транзакции с уровнем READ UNCOMMITTED")
            print("[Транзакция 1] Ожидание 1 секунду, пока транзакция 2 изменит данные...")
            time.sleep(1)

            # Читаем данные
            result = session.execute(text("SELECT balance FROM test_dirty_read WHERE id = 1")).fetchone()
            balance = result[0] if result else None
            results['transaction1_read'] = balance

            print(f"[Транзакция 1] Прочитано значение: {balance}")
            print("[Транзакция 1] Ожидание 1 секунду перед коммитом...")
            time.sleep(1)

            session.commit()
            print("[Транзакция 1] Транзакция закоммичена")
        except Exception as e:
            print(f"[Транзакция 1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2_writer():
        """Транзакция 2: Изменяет данные и откатывается"""
        session = SessionLocal()
        try:
            session.execute(text("BEGIN"))
            print("[Транзакция 2] Начало транзакции")

            time.sleep(0.5)

            # Изменяем данные
            session.execute(text("UPDATE test_dirty_read SET balance = 5000.0 WHERE id = 1"))
            results['transaction2_changed_to'] = 5000.0
            print("[Транзакция 2] Изменено значение на 5000.0 (НЕ ЗАКОММИЧЕНО)")

            print("[Транзакция 2] Ожидание 1.5 секунды перед откатом...")
            time.sleep(1.5)

            # Откатываем изменения
            session.rollback()
            print("[Транзакция 2] Транзакция откачена (ROLLBACK)")
        except Exception as e:
            print(f"[Транзакция 2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1_reader)
    t2 = threading.Thread(target=transaction2_writer)

    t2.start()
    t1.start()

    t1.join()
    t2.join()

    # Проверяем финальное состояние
    with engine.connect() as conn:
        result = conn.execute(text("SELECT balance FROM test_dirty_read WHERE id = 1")).fetchone()
        final_balance = result[0] if result else None

    print("\n" + "-"*80)
    print("РЕЗУЛЬТАТЫ:")
    print("-"*80)
    print(f"Транзакция 2 изменила значение на: {results['transaction2_changed_to']}")
    print(f"Транзакция 1 прочитала значение: {results['transaction1_read']}")
    print(f"Финальное значение в БД после отката: {final_balance}")
    print()

    if results['transaction1_read'] == 5000.0:
        print("⚠️  DIRTY READ ПРОИЗОШЕЛ!")
        print("   Транзакция 1 прочитала незакоммиченные данные транзакции 2.")
    elif results['transaction1_read'] == 1000.0:
        print("✓  DIRTY READ НЕ ПРОИЗОШЕЛ!")
        print("   PostgreSQL защитил от dirty read, несмотря на уровень READ UNCOMMITTED.")
        print("   Транзакция 1 прочитала только закоммиченные данные.")

    # Очистка
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_dirty_read"))
        conn.commit()

    print("\nВЫВОД: PostgreSQL НЕ ПОЗВОЛЯЕТ dirty reads даже на уровне READ UNCOMMITTED.\n")


if __name__ == "__main__":
    demo_dirty_read_attempt()
