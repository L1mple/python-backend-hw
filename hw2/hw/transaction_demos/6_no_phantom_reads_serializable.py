import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")

def demo_no_phantom_reads_serializable():
    """
    Демонстрация отсутствия phantom reads на уровне SERIALIZABLE.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Отсутствие phantom reads на уровне SERIALIZABLE")
    print("="*80)
    print("\nSERIALIZABLE - самый строгий уровень изоляции.")
    print("Гарантирует отсутствие всех аномалий чтения, включая phantom reads.\n")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    # Создаем тестовую таблицу
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_serializable"))
        conn.execute(text("""
            CREATE TABLE test_serializable (
                id INTEGER PRIMARY KEY,
                balance FLOAT
            )
        """))
        # Начальные данные: две строки с балансом > 500
        conn.execute(text("INSERT INTO test_serializable (id, balance) VALUES (1, 1000.0)"))
        conn.execute(text("INSERT INTO test_serializable (id, balance) VALUES (2, 800.0)"))
        conn.commit()

    print("Начальное состояние: 2 строки с balance > 500\n")

    results = {
        'transaction1_first_count': None,
        'transaction1_second_count': None,
        'transaction2_inserted': False,
        'transaction1_error': None,
        'transaction2_error': None
    }

    def transaction1_reader():
        """Транзакция 1: Выполняет один и тот же запрос дважды на уровне SERIALIZABLE"""
        session = SessionLocal()
        try:
            # Устанавливаем уровень изоляции SERIALIZABLE
            session.execute(text("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

            print("[Транзакция 1] Начало транзакции с уровнем SERIALIZABLE")

            # Первый запрос: считаем строки с balance > 500
            result = session.execute(text("SELECT COUNT(*) FROM test_serializable WHERE balance > 500")).fetchone()
            count1 = result[0] if result else 0
            results['transaction1_first_count'] = count1
            print(f"[Транзакция 1] Первый запрос: найдено {count1} строк с balance > 500")

            print("[Транзакция 1] Ожидание 2 секунды, пока транзакция 2 добавит новую строку...")
            time.sleep(2)

            # Второй запрос: снова считаем строки с balance > 500
            result = session.execute(text("SELECT COUNT(*) FROM test_serializable WHERE balance > 500")).fetchone()
            count2 = result[0] if result else 0
            results['transaction1_second_count'] = count2
            print(f"[Транзакция 1] Второй запрос: найдено {count2} строк с balance > 500")

            session.commit()
            print("[Транзакция 1] Транзакция закоммичена")
        except Exception as e:
            error_msg = str(e)
            results['transaction1_error'] = error_msg
            print(f"[Транзакция 1] Ошибка: {error_msg}")
            if "could not serialize" in error_msg.lower():
                print("[Транзакция 1] Получена ошибка сериализации - это нормально для SERIALIZABLE")
            session.rollback()
        finally:
            session.close()

    def transaction2_writer():
        """Транзакция 2: Добавляет новую строку на уровне SERIALIZABLE"""
        session = SessionLocal()
        try:
            print("[Транзакция 2] Ожидание 1 секунду перед началом...")
            time.sleep(1)

            # Устанавливаем уровень изоляции SERIALIZABLE
            session.execute(text("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            print("[Транзакция 2] Начало транзакции с уровнем SERIALIZABLE")

            # Добавляем новую строку, удовлетворяющую условию balance > 500
            session.execute(text("INSERT INTO test_serializable (id, balance) VALUES (3, 1500.0)"))
            results['transaction2_inserted'] = True
            print("[Транзакция 2] Добавлена новая строка: id=3, balance=1500.0")

            # Коммитим изменения
            session.commit()
            print("[Транзакция 2] Транзакция ЗАКОММИЧЕНА")
        except Exception as e:
            error_msg = str(e)
            results['transaction2_error'] = error_msg
            print(f"[Транзакция 2] Ошибка: {error_msg}")
            if "could not serialize" in error_msg.lower():
                print("[Транзакция 2] Получена ошибка сериализации - это нормально для SERIALIZABLE")
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
        result = conn.execute(text("SELECT COUNT(*) FROM test_serializable WHERE balance > 500")).fetchone()
        final_count = result[0] if result else 0

    print("\n" + "-"*80)
    print("РЕЗУЛЬТАТЫ:")
    print("-"*80)
    print(f"Транзакция 1, первый запрос: {results['transaction1_first_count']} строк")
    print(f"Транзакция 2 добавила новую строку: {'Да' if results['transaction2_inserted'] else 'Нет'}")
    print(f"Транзакция 1, второй запрос: {results['transaction1_second_count']} строк")
    print(f"Финальное количество строк в БД: {final_count}")

    if results['transaction1_error']:
        print(f"\nТранзакция 1 завершилась с ошибкой (это может быть нормально)")
    if results['transaction2_error']:
        print(f"Транзакция 2 завершилась с ошибкой")
    print()

    if results['transaction1_first_count'] == results['transaction1_second_count']:
        print("✓  PHANTOM READ НЕ ПРОИЗОШЕЛ!")
        print("   Транзакция 1 выполнила один и тот же запрос дважды")
        print("   и получила одинаковое количество строк оба раза:")
        print(f"   - Первый запрос: {results['transaction1_first_count']} строк")
        print(f"   - Второй запрос: {results['transaction1_second_count']} строк")
        print("\n   SERIALIZABLE гарантирует полную изоляцию от всех аномалий.")
    elif results['transaction1_error'] and "could not serialize" in results['transaction1_error'].lower():
        print("✓  SERIALIZABLE ПРЕДОТВРАТИЛ КОНФЛИКТ!")
        print("   Одна из транзакций получила ошибку сериализации.")
        print("   Это механизм защиты SERIALIZABLE - вместо того, чтобы допустить")
        print("   аномалию, PostgreSQL прерывает транзакцию с ошибкой.")
        print("   В реальном приложении нужно повторить такую транзакцию.")
    else:
        print("⚠️  Неожиданный результат")

    # Очистка
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_serializable"))
        conn.commit()

    print("\nВЫВОД: На уровне SERIALIZABLE phantom reads невозможны.")
    print("       PostgreSQL может использовать ошибки сериализации для предотвращения аномалий.\n")


if __name__ == "__main__":
    demo_no_phantom_reads_serializable()
