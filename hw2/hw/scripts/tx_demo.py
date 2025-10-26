from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://shop:shop@localhost:5432/shop")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def bootstrap_schema() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS demo_items (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL,
                    price NUMERIC NOT NULL
                );
                """
            )
        )
        conn.execute(text("DELETE FROM demo_items"))
        conn.execute(text("INSERT INTO demo_items (category, price) VALUES ('A', 100), ('A', 200), ('B', 300)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS oncall (
                    id SERIAL PRIMARY KEY,
                    doctor TEXT UNIQUE NOT NULL,
                    on_call BOOLEAN NOT NULL
                );
                """
            )
        )
        conn.execute(text("DELETE FROM oncall"))
        conn.execute(
            text("INSERT INTO oncall (doctor, on_call) VALUES ('alice', TRUE), ('bob', TRUE)")
        )


@contextmanager
def tx_conn(isolation: str) -> Connection:
    conn = engine.connect().execution_options(isolation_level=isolation)
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()


def show(title: str, value) -> None:
    print(f"\n=== {title} ===\n{value}")


def non_repeatable_read_at_read_committed() -> None:
    print("\n--- Non-repeatable read at READ COMMITTED ---")

    def t1():
        with tx_conn("READ COMMITTED") as c1:
            price1 = c1.execute(text("SELECT price FROM demo_items WHERE id = 1")).scalar()
            show("T1 first read price id=1", price1)
            time.sleep(1.0)
            price2 = c1.execute(text("SELECT price FROM demo_items WHERE id = 1")).scalar()
            show("T1 second read price id=1", price2)

    def t2():
        time.sleep(0.3)
        with tx_conn("READ COMMITTED") as c2:
            c2.execute(text("UPDATE demo_items SET price = price + 50 WHERE id = 1"))
            show("T2 updated price id=1", "commit")

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def repeatable_read_prevents_non_repeatable() -> None:
    print("\n--- No non-repeatable read at REPEATABLE READ ---")

    def t1():
        with tx_conn("REPEATABLE READ") as c1:
            price1 = c1.execute(text("SELECT price FROM demo_items WHERE id = 2")).scalar()
            show("T1 first read price id=2", price1)
            time.sleep(1.0)
            price2 = c1.execute(text("SELECT price FROM demo_items WHERE id = 2")).scalar()
            show("T1 second read price id=2", price2)

    def t2():
        time.sleep(0.3)
        with tx_conn("READ COMMITTED") as c2:
            c2.execute(text("UPDATE demo_items SET price = price + 50 WHERE id = 2"))
            show("T2 updated price id=2", "commit")

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def phantom_read_at_read_committed() -> None:
    print("\n--- Phantom read at READ COMMITTED ---")

    def t1():
        with tx_conn("READ COMMITTED") as c1:
            count1 = c1.execute(text("SELECT COUNT(*) FROM demo_items WHERE category = 'A'"))
            count1 = count1.scalar()
            show("T1 first count category=A", count1)
            time.sleep(1.0)
            count2 = c1.execute(text("SELECT COUNT(*) FROM demo_items WHERE category = 'A'"))
            count2 = count2.scalar()
            show("T1 second count category=A", count2)

    def t2():
        time.sleep(0.3)
        with tx_conn("READ COMMITTED") as c2:
            c2.execute(text("INSERT INTO demo_items (category, price) VALUES ('A', 123)"))
            show("T2 inserted new row in category A", "commit")

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def repeatable_read_prevents_phantom() -> None:
    print("\n--- No phantom read at REPEATABLE READ (Postgres) ---")

    def t1():
        with tx_conn("REPEATABLE READ") as c1:
            count1 = c1.execute(text("SELECT COUNT(*) FROM demo_items WHERE category = 'B'"))
            count1 = count1.scalar()
            show("T1 first count category=B", count1)
            time.sleep(1.0)
            count2 = c1.execute(text("SELECT COUNT(*) FROM demo_items WHERE category = 'B'"))
            count2 = count2.scalar()
            show("T1 second count category=B", count2)

    def t2():
        time.sleep(0.3)
        with tx_conn("READ COMMITTED") as c2:
            c2.execute(text("INSERT INTO demo_items (category, price) VALUES ('B', 999)"))
            show("T2 inserted new row in category B", "commit")

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def serializable_prevents_write_skew() -> None:
    print("\n--- SERIALIZABLE prevents write skew (one tx may abort) ---")

    errors: list[Exception] = []

    def tx_doctor(name: str):
        try:
            with tx_conn("SERIALIZABLE") as c:
                others_on = c.execute(text("SELECT COUNT(*) FROM oncall WHERE doctor <> :d AND on_call"), {"d": name}).scalar()
                show(f"{name} sees others on call", others_on)
                time.sleep(0.5)
                c.execute(text("UPDATE oncall SET on_call = FALSE WHERE doctor = :d"), {"d": name})
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=tx_doctor, args=("alice",))
    t2 = threading.Thread(target=tx_doctor, args=("bob",))
    t1.start(); t2.start(); t1.join(); t2.join()

    show("Errors (expected >=1 under SERIALIZABLE)", [type(e).__name__ + ": " + str(e) for e in errors])


def dirty_read_note() -> None:
    print("\n--- Dirty read at READ UNCOMMITTED ---")
    print("Postgres treats READ UNCOMMITTED as READ COMMITTED; dirty reads are not possible.")


def main() -> None:
    bootstrap_schema()
    dirty_read_note()
    non_repeatable_read_at_read_committed()
    repeatable_read_prevents_non_repeatable()
    phantom_read_at_read_committed()
    repeatable_read_prevents_phantom()
    serializable_prevents_write_skew()


if __name__ == "__main__":
    main()


