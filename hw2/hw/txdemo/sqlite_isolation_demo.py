"""
Run with (from hw directory): python txdemo/sqlite_isolation_demo.py
"""
import time
import threading
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

from store.models import Base

DEMO_DB = "sqlite:///./isolation_models_demo.sqlite"

engine = create_engine(DEMO_DB, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)

def reset_data():
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM item")
        conn.exec_driver_sql("INSERT INTO item(id, name, price, deleted) VALUES (1, 'A', 10.0, 0)")
        conn.exec_driver_sql("INSERT INTO item(id, name, price, deleted) VALUES (2, 'B', 20.0, 0)")

def dirty_read():
    print("\n--- Dirty Read with models (SQLite) ---")
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA read_uncommitted = 1")

    def writer():
        s = SessionLocal()
        try:
            s.execute(text("BEGIN"))
            s.execute(text("UPDATE item SET price = price + 100 WHERE id = 1"))
            time.sleep(2.0)  # keep uncommitted
            s.rollback()
        finally:
            s.close()

    def reader(res: dict):
        s = SessionLocal()
        try:
            s.execute(text("BEGIN"))
            price = s.execute(text("SELECT price FROM item WHERE id = 1")).scalar_one()
            res["price"] = price
            s.commit()
        finally:
            s.close()

    reset_data()
    res = {}
    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader, args=(res,))
    t1.start(); time.sleep(0.2); t2.start()
    t2.join(); t1.join()
    print("Observed price (expected 10.0):", res["price"])

def non_repeatable_read():
    print("\n--- Non-Repeatable Read with models (SQLite) ---")
    def tx1(res: dict):
        s = SessionLocal()
        try:
            s.execute(text("BEGIN"))
            res["v1"] = s.execute(text("SELECT price FROM item WHERE id = 2")).scalar_one()
            time.sleep(1.0)  # allow concurrent commit
            res["v2"] = s.execute(text("SELECT price FROM item WHERE id = 2")).scalar_one()
            s.commit()
        finally:
            s.close()

    def tx2():
        s = SessionLocal()
        try:
            s.execute(text("BEGIN"))
            s.execute(text("UPDATE item SET price = price + 1 WHERE id = 2"))
            s.commit()
        finally:
            s.close()

    reset_data()
    res = {}
    t1 = threading.Thread(target=tx1, args=(res,))
    t2 = threading.Thread(target=tx2)
    t1.start(); time.sleep(0.2); t2.start()
    t1.join(); t2.join()
    print("First read:", res["v1"], "Second read (same tx):", res["v2"])

def phantom_read():
    print("\n--- Phantom Read with models (SQLite) ---")
    def tx1(res: dict):
        s = SessionLocal()
        try:
            s.execute(text("BEGIN"))
            c1 = s.execute(text("SELECT COUNT(*) FROM item WHERE price >= 15")).scalar_one()
            time.sleep(1.0)
            c2 = s.execute(text("SELECT COUNT(*) FROM item WHERE price >= 15")).scalar_one()
            s.commit()
            res["c1"], res["c2"] = c1, c2
        finally:
            s.close()

    def tx2():
        s = SessionLocal()
        try:
            s.execute(text("BEGIN"))
            s.execute(text("INSERT INTO item(name, price, deleted) VALUES('C', 100.0, 0)"))
            s.commit()
        finally:
            s.close()

    reset_data()
    res = {}
    t1 = threading.Thread(target=tx1, args=(res,))
    t2 = threading.Thread(target=tx2)
    t1.start(); time.sleep(0.2); t2.start()
    t1.join(); t2.join()
    print("Count first:", res["c1"], "second (same tx):", res["c2"])

if __name__ == "__main__":
    reset_data()
    dirty_read()
    non_repeatable_read()
    phantom_read()