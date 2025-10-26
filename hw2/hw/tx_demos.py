from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import OperationalError, DBAPIError

DATABASE_URL = "postgresql+psycopg2://user:password@db:5432/hw2_db"

def wait_for_db(engine: Engine, attempts: int = 60, pause: float = 1.0) -> None:
    for _ in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            time.sleep(pause)
    raise RuntimeError("DB is not ready after wait")


def reset_accounts(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS accounts"))
        conn.execute(
            text(
                """
                CREATE TABLE accounts(
                    id SERIAL PRIMARY KEY,
                    balance INT NOT NULL
                )
                """
            )
        )
        conn.execute(text("INSERT INTO accounts(balance) VALUES (100), (200), (300)"))
        conn.commit()


def dump_accounts(engine: Engine, label: str) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, balance FROM accounts ORDER BY id")).all()
        print(label, [{"id": r.id, "balance": r.balance} for r in rows])


@contextmanager
def tx(engine: Engine, isolation: str) -> Iterator[Connection]:
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


def demo_non_repeatable_read(engine: Engine) -> None:
    print("\nNon-Repeatable Read READ COMMITTED")
    with tx(engine, "READ COMMITTED") as t1, tx(engine, "READ COMMITTED") as t2:
        v1 = t1.execute(text("SELECT balance FROM accounts WHERE id=1")).scalar_one()
        print(f"T1: first read (id=1) = {v1}")

        t2.execute(text("UPDATE accounts SET balance = balance + 50 WHERE id=1"))
        # t2 коммитится внутри контекста при выходе

        v2 = t1.execute(text("SELECT balance FROM accounts WHERE id=1")).scalar_one()
        print(f"T1: second read (id=1) = {v2}  -> изменилось? {'YES' if v2 != v1 else 'NO'}")


def demo_repeatable_read_snapshot(engine: Engine) -> None:
    print("\nSnapshot REPEATABLE READ (non-repeatable отсутствует в PG)")
    with tx(engine, "REPEATABLE READ") as t1, tx(engine, "READ COMMITTED") as t2:
        v1 = t1.execute(text("SELECT balance FROM accounts WHERE id=2")).scalar_one()
        print(f"T1: first read (id=2) = {v1}")

        t2.execute(text("UPDATE accounts SET balance = balance + 100 WHERE id=2"))
        # t2 коммитится при выходе

        v2 = t1.execute(text("SELECT balance FROM accounts WHERE id=2")).scalar_one()
        print(f"T1: second read (id=2) = {v2}  -> осталось прежним? {'YES' if v2 == v1 else 'NO'}")


def demo_phantom_repeatable(engine: Engine) -> None:
    print("\nPhantom REPEATABLE READ (в PG фантомов нет)")
    with tx(engine, "REPEATABLE READ") as t1, tx(engine, "READ COMMITTED") as t2:
        c1 = t1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar_one()
        print(f"T1: count BEFORE insert (balance>=100) = {c1}")

        t2.execute(text("INSERT INTO accounts(balance) VALUES (150)"))
        # t2 коммитится при выходе

        c2 = t1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar_one()
        print(f"T1: count AFTER insert (balance>=100)  = {c2}  -> совпало? {'YES' if c2 == c1 else 'NO'}")


def demo_serializable(engine: Engine) -> None:
    print("\nSERIALIZABLE (возможен serialization failure у конкурента)")
    with tx(engine, "SERIALIZABLE") as t1:
        c1 = t1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar_one()
        print(f"T1: count BEFORE = {c1}")

        # Отдельная транзакция T2 — попробует вставить конфликтующую запись
        try:
            with tx(engine, "SERIALIZABLE") as t2:
                t2.execute(text("INSERT INTO accounts(balance) VALUES (999)"))
                print("T2: INSERT 999 committed")
        except DBAPIError as e:
            # SQLSTATE '40001' / 'Serialization failure' — нормальная ситуация
            print(f"T2: serialization failure -> rolled back ({e.__class__.__name__}: {e})")

        c2 = t1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar_one()
        print(f"T1: count AFTER  = {c2}  -> инвариант сериализуемости соблюдён")


def main() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    wait_for_db(engine)

    reset_accounts(engine)
    dump_accounts(engine, "Initial data:")

    demo_non_repeatable_read(engine)
    demo_repeatable_read_snapshot(engine)
    demo_phantom_repeatable(engine)
    demo_serializable(engine)

    dump_accounts(engine, "Final data:")


if __name__ == "__main__":
    main()
