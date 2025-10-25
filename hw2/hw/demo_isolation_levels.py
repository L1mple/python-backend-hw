"""
PostgreSQL поддерживает следующие уровни изоляции:
- READ UNCOMMITTED (в PostgreSQL работает как READ COMMITTED)
- READ COMMITTED (по умолчанию)
- REPEATABLE READ
- SERIALIZABLE
"""

import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from threading import Thread


DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://shop_user:shop_password@localhost:5432/shop_db')


def setup_test_table(engine):
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS accounts CASCADE"))
        conn.execute(text("""
            CREATE TABLE accounts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50),
                balance NUMERIC(10, 2)
            )
        """))
        conn.execute(text("""
            INSERT INTO accounts (name, balance) VALUES 
            ('Alice', 1000.00),
            ('Bob', 1000.00)
        """))
        conn.commit()
    print("Тестовая таблица accounts создана и заполнена\n")


def print_separator(title: str):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def demo_dirty_read_uncommitted():
    """
    1. Dirty Read при READ UNCOMMITTED
    
    Примечание: PostgreSQL не поддерживает настоящий READ UNCOMMITTED.
    Даже при установке READ UNCOMMITTED, PostgreSQL использует READ COMMITTED.
    Поэтому dirty reads в PostgreSQL невозможны.
    """
    print_separator("1. DIRTY READ при READ UNCOMMITTED (PostgreSQL)")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (READ UNCOMMITTED)")
            
            # Обновляем баланс, но НЕ коммитим
            session.execute(text("UPDATE accounts SET balance = 500 WHERE name = 'Alice'"))
            print("T1: Обновил баланс Alice на 500 (НЕ закоммичено)")
            
            time.sleep(2)
            
            # Откатываем изменения
            session.rollback()
            print("T1: ROLLBACK - откатил изменения")
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)  # Даем T1 начать первым
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (READ UNCOMMITTED)")
            
            # Пытаемся прочитать незакоммиченные данные
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            balance = result.scalar()
            print(f"T2: Прочитал баланс Alice = {balance}")
            
            session.commit()
            print("T2: COMMIT")
        finally:
            session.close()
    
    # Запускаем транзакции параллельно
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Проверяем финальное состояние
    session = SessionLocal()
    result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
    final_balance = result.scalar()
    session.close()
    
    print(f"\nРезультат: Финальный баланс Alice = {final_balance}")
    print("PostgreSQL НЕ поддерживает настоящий READ UNCOMMITTED")
    print("Dirty read НЕ произошел, так как PostgreSQL использует READ COMMITTED")
    
    engine.dispose()


def demo_no_dirty_read_committed():
    """
    2. Отсутствие Dirty Read при READ COMMITTED
    """
    print_separator("2. НЕТ DIRTY READ при READ COMMITTED")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (READ COMMITTED)")
            
            session.execute(text("UPDATE accounts SET balance = 500 WHERE name = 'Alice'"))
            print("T1: Обновил баланс Alice на 500 (НЕ закоммичено)")
            
            time.sleep(2)
            
            session.rollback()
            print("T1: ROLLBACK - откатил изменения")
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (READ COMMITTED)")
            
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            balance = result.scalar()
            print(f"T2: Прочитал баланс Alice = {balance}")
            
            session.commit()
            print("T2: COMMIT")
        finally:
            session.close()
    
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    session = SessionLocal()
    result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
    final_balance = result.scalar()
    session.close()
    
    print(f"\nРезультат: Финальный баланс Alice = {final_balance}")
    print("Dirty read НЕ произошел - T2 видит только закоммиченные данные")
    
    engine.dispose()


def demo_non_repeatable_read():
    """
    3. Non-Repeatable Read при READ COMMITTED
    """
    print_separator("3. NON-REPEATABLE READ при READ COMMITTED")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (READ COMMITTED)")
            
            # Первое чтение
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            balance1 = result.scalar()
            print(f"T1: Первое чтение - баланс Alice = {balance1}")
            
            time.sleep(2)  # Даем T2 изменить данные
            
            # Второе чтение
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            balance2 = result.scalar()
            print(f"T1: Второе чтение - баланс Alice = {balance2}")
            
            if balance1 != balance2:
                print(f"NON-REPEATABLE READ! Баланс изменился: {balance1} -> {balance2}")
            
            session.commit()
            print("T1: COMMIT")
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (READ COMMITTED)")
            
            session.execute(text("UPDATE accounts SET balance = 1500 WHERE name = 'Alice'"))
            print("T2: Обновил баланс Alice на 1500")
            
            session.commit()
            print("T2: COMMIT")
        finally:
            session.close()
    
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("\nРезультат: Non-Repeatable Read произошел")
    print("T1 прочитала разные значения в рамках одной транзакции")
    
    engine.dispose()


def demo_no_non_repeatable_read():
    """
    4. Отсутствие Non-Repeatable Read при REPEATABLE READ
    """
    print_separator("4. НЕТ NON-REPEATABLE READ при REPEATABLE READ")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (REPEATABLE READ)")
            
            # Первое чтение
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            balance1 = result.scalar()
            print(f"T1: Первое чтение - баланс Alice = {balance1}")
            
            time.sleep(2)  # Даем T2 изменить данные
            
            # Второе чтение
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            balance2 = result.scalar()
            print(f"T1: Второе чтение - баланс Alice = {balance2}")
            
            if balance1 == balance2:
                print(f"✅ Баланс НЕ изменился: {balance1} = {balance2}")
            else:
                print(f"⚠️ Баланс изменился: {balance1} -> {balance2}")
            
            session.commit()
            print("T1: COMMIT")
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (REPEATABLE READ)")
            
            session.execute(text("UPDATE accounts SET balance = 1500 WHERE name = 'Alice'"))
            print("T2: Обновил баланс Alice на 1500")
            
            session.commit()
            print("T2: COMMIT")
        finally:
            session.close()
    
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("\nРезультат: Non-Repeatable Read НЕ произошел")
    print("T1 видит снимок данных на момент начала транзакции")
    
    engine.dispose()


def demo_phantom_read():
    """
    5. Phantom Reads при REPEATABLE READ
    """
    print_separator("5. PHANTOM READS при REPEATABLE READ")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (REPEATABLE READ)")
            
            # Первый подсчет
            result = session.execute(text("SELECT COUNT(*) FROM accounts WHERE balance > 500"))
            count1 = result.scalar()
            print(f"T1: Первый подсчет - количество счетов с балансом > 500: {count1}")
            
            time.sleep(2)  # Даем T2 вставить новую запись
            
            # Второй подсчет
            result = session.execute(text("SELECT COUNT(*) FROM accounts WHERE balance > 500"))
            count2 = result.scalar()
            print(f"T1: Второй подсчет - количество счетов с балансом > 500: {count2}")
            
            if count1 != count2:
                print(f"⚠️  PHANTOM READ! Количество изменилось: {count1} -> {count2}")
            else:
                print(f"✅ Количество НЕ изменилось: {count1} = {count2}")
            
            session.commit()
            print("T1: COMMIT")
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (REPEATABLE READ)")
            
            session.execute(text("INSERT INTO accounts (name, balance) VALUES ('Charlie', 2000)"))
            print("T2: Вставил новый счет Charlie с балансом 2000")
            
            session.commit()
            print("T2: COMMIT")
        finally:
            session.close()
    
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("\nРезультат: В PostgreSQL REPEATABLE READ предотвращает Phantom Reads")
    
    engine.dispose()


def demo_no_phantom_read_serializable():
    """
    6. Отсутствие Phantom Reads при SERIALIZABLE
    """
    print_separator("6. НЕТ PHANTOM READS при SERIALIZABLE")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (SERIALIZABLE)")
            
            # Первый подсчет
            result = session.execute(text("SELECT COUNT(*) FROM accounts WHERE balance > 500"))
            count1 = result.scalar()
            print(f"T1: Первый подсчет - количество счетов с балансом > 500: {count1}")
            
            time.sleep(2)
            
            # Второй подсчет
            result = session.execute(text("SELECT COUNT(*) FROM accounts WHERE balance > 500"))
            count2 = result.scalar()
            print(f"T1: Второй подсчет - количество счетов с балансом > 500: {count2}")
            
            if count1 == count2:
                print(f"✅ Количество НЕ изменилось: {count1} = {count2}")
            
            session.commit()
            print("T1: COMMIT")
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (SERIALIZABLE)")
            
            try:
                session.execute(text("INSERT INTO accounts (name, balance) VALUES ('David', 3000)"))
                print("T2: Вставил новый счет David с балансом 3000")
                
                session.commit()
                print("T2: COMMIT")
            except Exception as e:
                print(f"T2: ❌ ОШИБКА - {e}")
                print("T2: Транзакция отменена из-за конфликта сериализации")
                session.rollback()
        finally:
            session.close()
    
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    engine.dispose()


def demo_serialization_conflict():
    """
    7. Демонстрация конфликта сериализации при SERIALIZABLE
    """
    print_separator("7. КОНФЛИКТ СЕРИАЛИЗАЦИИ при SERIALIZABLE")
    
    engine = create_engine(DATABASE_URL, echo=False)
    setup_test_table(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            session.execute(text("BEGIN"))
            
            print("T1: Начало транзакции (SERIALIZABLE)")
            
            # Читаем баланс Bob
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Bob'"))
            bob_balance = result.scalar()
            print(f"T1: Прочитал баланс Bob = {bob_balance}")
            
            time.sleep(1)
            
            # Обновляем Alice на основе баланса Bob
            new_balance = bob_balance + 100
            session.execute(text(f"UPDATE accounts SET balance = {new_balance} WHERE name = 'Alice'"))
            print(f"T1: Обновил баланс Alice на {new_balance}")
            
            time.sleep(1)
            
            try:
                session.commit()
                print("T1: ✅ COMMIT успешен")
            except Exception as e:
                print(f"T1: ❌ COMMIT не удался - {type(e).__name__}")
                session.rollback()
        finally:
            session.close()
    
    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(0.5)
            
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            session.execute(text("BEGIN"))
            
            print("T2: Начало транзакции (SERIALIZABLE)")
            
            # Читаем баланс Alice
            result = session.execute(text("SELECT balance FROM accounts WHERE name = 'Alice'"))
            alice_balance = result.scalar()
            print(f"T2: Прочитал баланс Alice = {alice_balance}")
            
            time.sleep(1)
            
            # Обновляем Bob на основе баланса Alice
            new_balance = alice_balance + 100
            session.execute(text(f"UPDATE accounts SET balance = {new_balance} WHERE name = 'Bob'"))
            print(f"T2: Обновил баланс Bob на {new_balance}")
            
            try:
                session.commit()
                print("T2: ✅ COMMIT успешен")
            except Exception as e:
                print(f"T2: ❌ COMMIT не удался - {type(e).__name__}")
                session.rollback()
        finally:
            session.close()
    
    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("\nРезультат: Одна из транзакций будет отменена")
    print("SERIALIZABLE обнаруживает циклические зависимости")
    print("Приложение должно повторить неудавшуюся транзакцию")
    
    engine.dispose()


if __name__ == "__main__":
    print("\n" + "🔬 ДЕМОНСТРАЦИЯ УРОВНЕЙ ИЗОЛЯЦИИ ТРАНЗАКЦИЙ В POSTGRESQL ".center(80, "="))
    print("\nПримечание: PostgreSQL использует MVCC (Multi-Version Concurrency Control)")
    print("Это делает некоторые уровни изоляции более строгими, чем в стандарте SQL\n")
    
    demos = [
        ("1", "Dirty Read при READ UNCOMMITTED (не работает в PostgreSQL)", demo_dirty_read_uncommitted),
        ("2", "Отсутствие Dirty Read при READ COMMITTED", demo_no_dirty_read_committed),
        ("3", "Non-Repeatable Read при READ COMMITTED", demo_non_repeatable_read),
        ("4", "Отсутствие Non-Repeatable Read при REPEATABLE READ", demo_no_non_repeatable_read),
        ("5", "Phantom Reads при REPEATABLE READ (не работает в PostgreSQL)", demo_phantom_read),
        ("6", "Отсутствие Phantom Reads при SERIALIZABLE", demo_no_phantom_read_serializable),
        ("7", "Конфликт сериализации при SERIALIZABLE", demo_serialization_conflict),
    ]
    
    print("Доступные демонстрации:")
    for num, desc, _ in demos:
        print(f"  {num}. {desc}")
    print("  0. Запустить все демонстрации")
    print("  q. Выход")
    
    choice = input("\nВыберите демонстрацию (0-7, q): ").strip()
    
    if choice == 'q':
        print("Выход...")
    elif choice == '0':
        for _, _, demo_func in demos:
            demo_func()
            time.sleep(1)
    else:
        for num, _, demo_func in demos:
            if choice == num:
                demo_func()
                break
        else:
            print("Неверный выбор!")
    
    print("\n" + "="*80)
    print("Демонстрация завершена!".center(80))
    print("="*80 + "\n")
