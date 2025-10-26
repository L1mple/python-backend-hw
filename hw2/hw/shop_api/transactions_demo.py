"""
Демонстрация проблем изоляции транзакций на PostgreSQL через SQLAlchemy.
Перед запуском нужно убедиться, что таблица items существует (Shop API уже создал её).
"""

import time

from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:postgres@db:5432/shop_db"

engine = create_engine(DB_URL, echo=False, future=True)


# ----------------------------------------------------------
# DIRTY READ (грязное чтение)
# ----------------------------------------------------------


def dirty_read():
    print("\n=== DIRTY READ (демонстрация) ===")
    conn1 = engine.connect()
    conn2 = engine.connect()

    conn1.execute(text("BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;"))
    conn1.execute(text("UPDATE items SET price = price + 100 WHERE id = 1;"))

    conn2.execute(text("BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;"))
    try:
        val = conn2.execute(text("SELECT price FROM items WHERE id = 1;")).scalar()
        print("Dirty read (READ UNCOMMITTED):", val)
    except Exception as e:
        print("Dirty read blocked / prevented:", e)

    conn1.execute(text("ROLLBACK;"))
    conn2.execute(text("COMMIT;"))
    conn1.close()
    conn2.close()

    print("В PostgreSQL dirty read предотвращается даже при READ UNCOMMITTED.")


# ----------------------------------------------------------
# NON-REPEATABLE READ (неповторяемое чтение)
# ----------------------------------------------------------


def non_repeatable_read():
    print("\n=== NON-REPEATABLE READ ===")
    conn1 = engine.connect()
    conn2 = engine.connect()

    conn1.execute(text("BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;"))
    val1 = conn1.execute(text("SELECT price FROM items WHERE id = 1;")).scalar()
    print("First read:", val1)

    conn2.execute(text("BEGIN;"))
    conn2.execute(text("UPDATE items SET price = price + 50 WHERE id = 1;"))
    conn2.execute(text("COMMIT;"))

    val2 = conn1.execute(text("SELECT price FROM items WHERE id = 1;")).scalar()
    print("Second read (changed):", val2)

    conn1.execute(text("COMMIT;"))
    conn1.close()
    conn2.close()

    print("Non-repeatable read: значение изменилось между двумя SELECT.")


def non_repeatable_read_fixed():
    print("\n=== NON-REPEATABLE READ FIXED (REPEATABLE READ) ===")
    conn1 = engine.connect()
    conn2 = engine.connect()

    conn1.execute(text("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;"))
    val1 = conn1.execute(text("SELECT price FROM items WHERE id = 1;")).scalar()
    print("First read:", val1)

    conn2.execute(text("BEGIN;"))
    conn2.execute(text("UPDATE items SET price = price + 50 WHERE id = 1;"))
    try:
        conn2.execute(text("COMMIT;"))
    except Exception as e:
        print("Update blocked due to REPEATABLE READ:", e)

    val2 = conn1.execute(text("SELECT price FROM items WHERE id = 1;")).scalar()
    print("Second read (same):", val2)

    conn1.execute(text("COMMIT;"))
    conn1.close()
    conn2.close()

    print("REPEATABLE READ предотвращает non-repeatable read.")


# ----------------------------------------------------------
# PHANTOM READ (фантомные строки)
# ----------------------------------------------------------


def phantom_read():
    print("\n=== PHANTOM READ ===")
    conn1 = engine.connect()
    conn2 = engine.connect()

    conn1.execute(text("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;"))
    val1 = conn1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100;")).scalar()
    print("Initial count:", val1)

    conn2.execute(text("BEGIN;"))
    conn2.execute(text("INSERT INTO items (name, price, deleted) VALUES ('phantom1', 150, false);"))
    conn2.execute(text("COMMIT;"))

    val2 = conn1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100;")).scalar()
    print("Second count (phantom appears?):", val2)

    conn1.execute(text("COMMIT;"))
    conn1.close()
    conn2.close()

    print("При REPEATABLE READ фантом может появиться.")


def phantom_read_fixed():
    print("\n=== PHANTOM READ FIXED (SERIALIZABLE) ===")
    conn1 = engine.connect()
    conn2 = engine.connect()

    conn1.execute(text("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;"))
    val1 = conn1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100;")).scalar()
    print("Initial count:", val1)

    conn2.execute(text("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;"))
    conn2.execute(text("INSERT INTO items (name, price, deleted) VALUES ('phantom2', 200, false);"))
    try:
        conn2.execute(text("COMMIT;"))
    except Exception as e:
        print("Insert blocked or rolled back:", e)

    val2 = conn1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100;")).scalar()
    print("Second count (should be same):", val2)

    conn1.execute(text("COMMIT;"))
    conn1.close()
    conn2.close()

    print("SERIALIZABLE предотвращает phantom read.")


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------

if __name__ == "__main__":
    print("Демонстрация уровней изоляции транзакций PostgreSQL\n")

    dirty_read()
    time.sleep(1)

    non_repeatable_read()
    time.sleep(1)

    non_repeatable_read_fixed()
    time.sleep(1)

    phantom_read()
    time.sleep(1)

    phantom_read_fixed()
