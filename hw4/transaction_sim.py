import time
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

DATABASE_URL = "postgresql://user:password@localhost:5432/shopdb"
engine = create_engine(DATABASE_URL)

def setup_database():
    """Пересоздает и заполняет таблицу начальными данными."""
    with engine.connect() as connection:
        if inspect(engine).has_table("accounts"):
            connection.execute(text("DROP TABLE accounts;"))
        connection.execute(text("""
            CREATE TABLE accounts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50),
                balance INT
            );
        """))
        connection.execute(text("INSERT INTO accounts (name, balance) VALUES ('Alice', 1000);"))
        connection.commit()
    print("--- БД готова. Alice, баланс: 1000 ---\n")

def show_dirty_read():
    """
    PostgreSQL не поддерживает READ UNCOMMITTED и повышает его до READ COMMITTED.
    Поэтому мы сразу демонстрируем, как READ COMMITTED решает проблему 'грязного чтения'.
    """
    print("="*20)
    print("1. Dirty Read (на READ COMMITTED)")
    print("="*20)
    setup_database()
    print("Сценарий: T1 пытается прочесть незакоммиченные изменения от T2.")

    with engine.connect().execution_options(isolation_level="READ COMMITTED") as conn1, conn1.begin():
        print("T1: Начала транзакцию.")

        with engine.connect().execution_options(isolation_level="READ COMMITTED") as conn2, conn2.begin():
            print("  T2: Начала транзакцию, обновила баланс Alice на 500 (без commit).")
            conn2.execute(text("UPDATE accounts SET balance = 500 WHERE name = 'Alice';"))

            print("T1: Читает баланс Alice...")
            balance = conn1.execute(text("SELECT balance FROM accounts WHERE name = 'Alice';")).scalar()
            print(f"T1: Видит баланс: {balance} (старое значение, т.к. T2 не сделала commit).")

            print("  T2: Делает ROLLBACK.")
        # Транзакция T2 автоматически откатывается при выходе из with

        balance = conn1.execute(text("SELECT balance FROM accounts WHERE name = 'Alice';")).scalar()
        print(f"T1: Итоговый баланс после отката T2: {balance}.")

    print("\nИТОГ: READ COMMITTED предотвращает 'грязное чтение'. T1 не видит изменения T2 до commit.")

def show_non_repeatable_read():
    print("="*20)
    print("2. Non-Repeatable Read (на READ COMMITTED)")
    print("="*20)
    setup_database()
    print("Сценарий: T1 читает данные до и после того, как T2 их изменит и закоммитит.")

    with engine.connect().execution_options(isolation_level="READ COMMITTED") as conn1, conn1.begin():
        print("T1: Начала транзакцию.")
        balance1 = conn1.execute(text("SELECT balance FROM accounts WHERE name = 'Alice';")).scalar()
        print(f"T1: Чтение 1: баланс = {balance1}")

        time.sleep(1)

        with engine.connect().execution_options(isolation_level="READ COMMITTED") as conn2, conn2.begin():
            print("  T2: Обновляет баланс Alice на 500 и делает COMMIT.")
            conn2.execute(text("UPDATE accounts SET balance = 500 WHERE name = 'Alice';"))
            # conn2.commit() происходит автоматически

        balance2 = conn1.execute(text("SELECT balance FROM accounts WHERE name = 'Alice';")).scalar()
        print(f"T1: Чтение 2: баланс = {balance2}")

    print(f"\nИТОГ: Non-Repeatable Read. T1 получила разные результаты ({balance1} != {balance2}) в одной транзакции.")

def fix_non_repeatable_read():
    print("="*20)
    print("3. РЕШЕНИЕ: Non-Repeatable Read (на REPEATABLE READ)")
    print("="*20)
    setup_database()
    print("Сценарий: Аналогичен предыдущему, но уровень изоляции повышен.")

    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn1, conn1.begin():
        print("T1: Начала транзакцию.")
        balance1 = conn1.execute(text("SELECT balance FROM accounts WHERE name = 'Alice';")).scalar()
        print(f"T1: Чтение 1: баланс = {balance1}")

        time.sleep(1)

        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn2, conn2.begin():
            print("  T2: Обновляет баланс Alice на 500 и делает COMMIT.")
            conn2.execute(text("UPDATE accounts SET balance = 500 WHERE name = 'Alice';"))

        balance2 = conn1.execute(text("SELECT balance FROM accounts WHERE name = 'Alice';")).scalar()
        print(f"T1: Чтение 2: баланс = {balance2}")

    print(f"\nИТОГ: Проблема решена. T1 видит одни и те же данные ({balance1} == {balance2}) благодаря 'снимку' данных.")

def show_phantom_read():
    print("="*20)
    print("4. Phantom Read (на REPEATABLE READ)")
    print("="*20)
    setup_database()
    print("Сценарий: T1 дважды выбирает диапазон строк, а T2 добавляет новую строку в этот диапазон.")

    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn1, conn1.begin():
        print("T1: Начала транзакцию.")
        accounts1 = conn1.execute(text("SELECT * FROM accounts WHERE balance > 500;")).fetchall()
        print(f"T1: Чтение 1: найдено {len(accounts1)} строк.")

        time.sleep(1)

        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn2, conn2.begin():
            print("  T2: Добавляет 'Bob' с балансом 2000 и делает COMMIT.")
            conn2.execute(text("INSERT INTO accounts (name, balance) VALUES ('Bob', 2000);"))

        accounts2 = conn1.execute(text("SELECT * FROM accounts WHERE balance > 500;")).fetchall()
        print(f"T1: Чтение 2: найдено {len(accounts2)} строк.")

    print(f"\nИТОГ: Phantom Read. Количество строк изменилось ({len(accounts1)} -> {len(accounts2)}) в одной транзакции.")

def fix_phantom_read():
    print("="*20)
    print("5. РЕШЕНИЕ: Phantom Read (на SERIALIZABLE)")
    print("="*20)
    setup_database()
    print("Сценарий: Аналогичен предыдущему, но с уровнем SERIALIZABLE.")

    with engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn1, conn1.begin():
        print("T1: Начала транзакцию.")
        accounts1 = conn1.execute(text("SELECT * FROM accounts WHERE balance > 500;")).fetchall()
        print(f"T1: Чтение 1: найдено {len(accounts1)} строк.")

        time.sleep(1)

        try:
            with engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn2, conn2.begin():
                print("  T2: Пытается добавить 'Bob'...")
                # Эта операция вызовет ошибку, так как T1 уже прочитала этот диапазон
                conn2.execute(text("INSERT INTO accounts (name, balance) VALUES ('Bob', 2000);"))
        except OperationalError as e:
            print(f"  T2: ОШИБКА! Транзакция T2 не удалась ({e.orig.__class__.__name__}). Это ожидаемо.")

        accounts2 = conn1.execute(text("SELECT * FROM accounts WHERE balance > 500;")).fetchall()
        print(f"T1: Чтение 2: найдено {len(accounts2)} строк.")

    print(f"\nИТОГ: Проблема решена. SERIALIZABLE не позволил T2 вставить 'фантома'. Результаты T1 стабильны ({len(accounts1)} == {len(accounts2)}).")

if __name__ == "__main__":
    show_dirty_read()
    input("\nНажмите Enter для продолжения...")
    show_non_repeatable_read()
    input("\nНажмите Enter для продолжения...")
    fix_non_repeatable_read()
    input("\nНажмите Enter для продолжения...")
    show_phantom_read()
    input("\nНажмите Enter для продолжения...")
    fix_phantom_read()