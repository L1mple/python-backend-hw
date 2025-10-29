from __future__ import annotations
import threading
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker

import os

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@postgres:5432/postgres",
)

engine = create_engine(DB_URL, isolation_level="READ COMMITTED", future=True)
Session = sessionmaker(engine, future=True)


@contextmanager
def tx(isolation: str = "READ COMMITTED"):
    eng = create_engine(DB_URL, isolation_level=isolation, future=True)
    with eng.connect() as conn:
        trans = conn.begin()
        try:
            yield conn
            trans.commit()
        except:
            trans.rollback()
            raise
        finally:
            conn.close()


def prepare():
    with engine.begin() as c:
        c.execute(text("""
            CREATE TABLE IF NOT EXISTS demo_kv(
              id INT PRIMARY KEY,
              val INT NOT NULL
            );
        """))
        c.execute(text("DELETE FROM demo_kv;"))
        c.execute(text("INSERT INTO demo_kv(id,val) VALUES (1, 100);"))


def non_repeatable_read_read_committed():
    prepare()

    def t1():
        with tx("READ COMMITTED") as c:
            r1 = c.execute(
                text("SELECT val FROM demo_kv WHERE id=1")).scalar_one()
            print(f"[T1] first read val={r1}")
            time.sleep(2)
            r2 = c.execute(
                text("SELECT val FROM demo_kv WHERE id=1")).scalar_one()
            print(f"[T1] second read val={r2}")

    def t2():
        time.sleep(0.5)
        with tx("READ COMMITTED") as c:
            c.execute(text("UPDATE demo_kv SET val = val + 1 WHERE id=1"))
            print("[T2] committed UPDATE")
    threading.Thread(target=t1).start()
    threading.Thread(target=t2).start()


def non_repeatable_read_repeatable_read():
    prepare()

    def t1():
        with tx("REPEATABLE READ") as c:
            r1 = c.execute(
                text("SELECT val FROM demo_kv WHERE id=1")).scalar_one()
            print(f"[T1] first read val={r1}")
            time.sleep(2)
            r2 = c.execute(
                text("SELECT val FROM demo_kv WHERE id=1")).scalar_one()
            print(f"[T1] second read val={r2}")

    def t2():
        time.sleep(0.5)
        with tx("READ COMMITTED") as c:
            c.execute(text("UPDATE demo_kv SET val = val + 1 WHERE id=1"))
            print("[T2] committed UPDATE")
    threading.Thread(target=t1).start()
    threading.Thread(target=t2).start()


def phantom_read_read_committed():
    prepare()
    with engine.begin() as c:
        c.execute(text("DELETE FROM demo_kv;"))
        c.execute(text("INSERT INTO demo_kv(id,val) VALUES (1,100), (2,100);"))

    def t1():
        with tx("READ COMMITTED") as c:
            r1 = c.execute(
                text("SELECT COUNT(*) FROM demo_kv WHERE val=100")).scalar_one()
            print(f"[T1] first count={r1}")
            time.sleep(2)
            r2 = c.execute(
                text("SELECT COUNT(*) FROM demo_kv WHERE val=100")).scalar_one()
            print(f"[T1] second count={r2}")

    def t2():
        time.sleep(0.5)
        with tx("READ COMMITTED") as c:
            c.execute(text("INSERT INTO demo_kv(id,val) VALUES (3,100)"))
            print("[T2] committed INSERT")
    threading.Thread(target=t1).start()
    threading.Thread(target=t2).start()


def phantom_read_repeatable_read():
    prepare()
    with engine.begin() as c:
        c.execute(text("DELETE FROM demo_kv;"))
        c.execute(text("INSERT INTO demo_kv(id,val) VALUES (1,100), (2,100);"))

    def t1():
        with tx("REPEATABLE READ") as c:
            r1 = c.execute(
                text("SELECT COUNT(*) FROM demo_kv WHERE val=100")).scalar_one()
            print(f"[T1] first count={r1}")
            time.sleep(2)
            r2 = c.execute(
                text("SELECT COUNT(*) FROM demo_kv WHERE val=100")).scalar_one()
            print(f"[T1] second count={r2}")

    def t2():
        time.sleep(0.5)
        with tx("READ COMMITTED") as c:
            c.execute(text("INSERT INTO demo_kv(id,val) VALUES (3,100)"))
            print("[T2] committed INSERT")
    threading.Thread(target=t1).start()
    threading.Thread(target=t2).start()


def serializable_example_no_anomalies():
    prepare()

    def t1():
        with tx("SERIALIZABLE") as c:
            r1 = c.execute(
                text("SELECT val FROM demo_kv WHERE id=1 FOR UPDATE")).scalar_one()
            c.execute(text("UPDATE demo_kv SET val=:v WHERE id=1"),
                      {"v": r1 + 10})
            print("[T1] bump +10 committed")

    def t2():
        time.sleep(0.2)
        try:
            with tx("SERIALIZABLE") as c:
                r1 = c.execute(
                    text("SELECT val FROM demo_kv WHERE id=1 FOR UPDATE")).scalar_one()
                c.execute(text("UPDATE demo_kv SET val=:v WHERE id=1"), {
                          "v": r1 + 20})
                print("[T2] bump +20 committed")
        except Exception as e:
            print(f"[T2] serialization failure -> {e}")
    threading.Thread(target=t1).start()
    threading.Thread(target=t2).start()


SCENARIOS = {
    "nrr_rc": non_repeatable_read_read_committed,
    "nrr_rr": non_repeatable_read_repeatable_read,
    "phantom_rc": phantom_read_read_committed,
    "phantom_rr": phantom_read_repeatable_read,
    "serializable": serializable_example_no_anomalies,
}

if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "nrr_rc"
    print(f"Running scenario: {name}")
    SCENARIOS[name]()
    time.sleep(4)
