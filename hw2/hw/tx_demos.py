from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, text


DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://shop:shop@localhost:5432/shop")
engine = create_engine(DB_URL, future=True)


@contextmanager
def tx(iso: str):
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level=iso)
        trans = conn.begin()
        try:
            yield conn
            trans.commit()
        except Exception:
            trans.rollback()
            raise


def setup_schema():
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS demo (id int primary key, val int)"))
        conn.execute(text("INSERT INTO demo (id, val) VALUES (1, 100) ON CONFLICT (id) DO UPDATE SET val=excluded.val"))


def dirty_read_demo():
    setup_schema()
    def t1():
        with tx("READ UNCOMMITTED") as c:
            r1 = c.execute(text("SELECT val FROM demo WHERE id=1")).scalar_one()
            time.sleep(0.6)
            r2 = c.execute(text("SELECT val FROM demo WHERE id=1")).scalar_one()
            print(f"T1 read-before={r1} read-after={r2}")

    def t2():
        time.sleep(0.2)
        with tx("READ UNCOMMITTED") as c:
            c.execute(text("UPDATE demo SET val=val+1 WHERE id=1"))
            time.sleep(0.6)
            # rollback
            raise RuntimeError("rollback to simulate dirty write")

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=lambda: (t2()))
    th1.start(); th2.start(); th1.join();
    try:
        th2.join()
    except Exception:
        pass


def non_repeatable_read_demo():
    setup_schema()
    def t1():
        with tx("READ COMMITTED") as c:
            r1 = c.execute(text("SELECT val FROM demo WHERE id=1")).scalar_one()
            time.sleep(0.6)
            r2 = c.execute(text("SELECT val FROM demo WHERE id=1")).scalar_one()
            print(f"T1 RC before={r1} after={r2}")

    def t2():
        time.sleep(0.2)
        with tx("READ COMMITTED") as c:
            c.execute(text("UPDATE demo SET val=val+1 WHERE id=1"))

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def prevent_non_repeatable_read_demo():
    setup_schema()
    def t1():
        with tx("REPEATABLE READ") as c:
            r1 = c.execute(text("SELECT val FROM demo WHERE id=1")).scalar_one()
            time.sleep(0.6)
            r2 = c.execute(text("SELECT val FROM demo WHERE id=1")).scalar_one()
            print(f"T1 RR before={r1} after={r2}")

    def t2():
        time.sleep(0.2)
        with tx("READ COMMITTED") as c:
            c.execute(text("UPDATE demo SET val=val+1 WHERE id=1"))

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def phantom_demo():
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS demo_ph"))
        c.execute(text("CREATE TABLE demo_ph(id int primary key)"))
        c.execute(text("INSERT INTO demo_ph(id) VALUES (1),(2),(3)"))

    def t1():
        with tx("REPEATABLE READ") as c:
            r1 = c.execute(text("SELECT COUNT(*) FROM demo_ph")).scalar_one()
            time.sleep(0.6)
            r2 = c.execute(text("SELECT COUNT(*) FROM demo_ph")).scalar_one()
            print(f"T1 RR count before={r1} after={r2}")

    def t2():
        time.sleep(0.2)
        with tx("READ COMMITTED") as c:
            c.execute(text("INSERT INTO demo_ph(id) VALUES (4)"))

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


def prevent_phantom_demo():
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS demo_ph2"))
        c.execute(text("CREATE TABLE demo_ph2(id int primary key)"))
        c.execute(text("INSERT INTO demo_ph2(id) VALUES (1),(2),(3)"))

    def t1():
        with tx("SERIALIZABLE") as c:
            r1 = c.execute(text("SELECT COUNT(*) FROM demo_ph2")).scalar_one()
            time.sleep(0.6)
            r2 = c.execute(text("SELECT COUNT(*) FROM demo_ph2")).scalar_one()
            print(f"T1 SR count before={r1} after={r2}")

    def t2():
        time.sleep(0.2)
        with tx("READ COMMITTED") as c:
            c.execute(text("INSERT INTO demo_ph2(id) VALUES (4)"))

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()


if __name__ == "__main__":
    print("Dirty read @ RU (expect change due to uncommitted):")
    try:
        dirty_read_demo()
    except Exception as e:
        print(f"Dirty read demo error: {e}")

    print("Non-repeatable read @ RC (expect change):")
    non_repeatable_read_demo()

    print("Prevent non-repeatable @ RR (expect same):")
    prevent_non_repeatable_read_demo()

    print("Phantom @ RR (expect count grows):")
    phantom_demo()

    print("Prevent phantom @ SR (expect same or serialization error):")
    prevent_phantom_demo()

