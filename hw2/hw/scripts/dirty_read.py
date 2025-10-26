"""Dirty read demo using SQLAlchemy can not be performed in Postgres."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import threading
import time
from __init__ import DATABASE_URL


engine = create_engine(DATABASE_URL)
with engine.connect().execution_options(isolation_level="READ UNCOMMITTED"):
    pass

with engine.begin() as conn:
    conn.execute(
        text(
            """
        DROP TABLE IF EXISTS accounts
    """
        )
    )
    conn.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS accounts(
            id      integer PRIMARY KEY,
            balance integer NOT NULL
        )
    """
        )
    )
    conn.execute(
        text(
            """
        INSERT INTO accounts (id, balance)
        VALUES (1, 1000)
        ON CONFLICT (id) DO UPDATE SET balance = EXCLUDED.balance
    """
        )
    )


def tx_a_update_and_hold(commit=False, hold_secs=5):
    with Session(engine) as s:
        s.execute(text("UPDATE accounts SET balance = balance + 100 WHERE id = 1"))
        seen = s.execute(text("SELECT balance FROM accounts WHERE id = 1")).scalar_one()
        print("[A] (uncommitted) sees:", seen)

        time.sleep(hold_secs)

        if commit:
            s.commit()
            print("[A] committed")
        else:
            s.rollback()
            print("[A] rolled back")


def tx_b_plain_select(label="[B plain]"):
    """
    Read uncommitted is not supported in Postgres;
    it behaves like Read Committed.
    """
    with engine.connect() as conn:
        with conn.execution_options(isolation_level="READ UNCOMMITTED"):
            val = conn.execute(
                text("SELECT balance FROM accounts WHERE id = 1")
            ).scalar_one()
            print(f"{label} sees:", val)


def show_final(label="[final]"):
    with Session(engine) as s:
        val = s.execute(text("SELECT balance FROM accounts WHERE id = 1")).scalar_one()
        print(f"{label} balance:", val)


def run_all():
    print("\n=== TEST DIRTY READ ===")
    print(
        "NOTATION: Read Uncommitted is not supported in Postgres; it behaves like Read Committed.\n"
    )
    t_a = threading.Thread(
        target=tx_a_update_and_hold, kwargs={"commit": False, "hold_secs": 5}
    )
    t_a.start()
    time.sleep(1)
    tx_b_plain_select("[B during A]")  # saw 1000, NOT 1100
    t_a.join()
    show_final("[after A rollback]")  # again 1000

    # Case 2: A commit → B
    t_a2 = threading.Thread(
        target=tx_a_update_and_hold, kwargs={"commit": True, "hold_secs": 3}
    )
    t_a2.start()
    time.sleep(1)
    tx_b_plain_select("[B during A (commit case)]")
    t_a2.join()
    show_final("[after A commit]")
