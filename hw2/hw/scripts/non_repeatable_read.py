from sqlalchemy import create_engine, text
import threading
import time
from __init__ import DATABASE_URL


engine = create_engine(DATABASE_URL)
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
        CREATE TABLE IF NOT EXISTS accounts (
            id INT PRIMARY KEY,
            balance INT NOT NULL
        )
    """
        )
    )
    conn.execute(
        text(
            """
        INSERT INTO accounts (id, balance) VALUES (1, 1000)
        ON CONFLICT (id) DO UPDATE SET balance = EXCLUDED.balance
    """
        )
    )


def tx_a_read_twice(isolation="READ COMMITTED"):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))
        r1 = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1")
        ).scalar_one()
        print(f"[A] first read ({isolation}):", r1)
        time.sleep(4)
        r2 = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1")
        ).scalar_one()
        print(f"[A] second read ({isolation}):", r2)
        trans.commit()
    finally:
        conn.close()


def tx_b_update():
    time.sleep(1)
    with engine.begin() as conn:
        conn.execute(text("UPDATE accounts SET balance = balance + 50 WHERE id = 1"))
        print("[B] updated balance by +50")


def run_all():
    print("\n=== TEST READ COMMITTED ===")
    t1 = threading.Thread(
        target=tx_a_read_twice, kwargs={"isolation": "READ COMMITTED"}
    )
    t2 = threading.Thread(target=tx_b_update)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    with engine.begin() as conn:
        conn.execute(text("UPDATE accounts SET balance = 1000 WHERE id = 1"))

    print("\n=== TEST REPEATABLE READ ===")
    t1 = threading.Thread(
        target=tx_a_read_twice, kwargs={"isolation": "REPEATABLE READ"}
    )
    t2 = threading.Thread(target=tx_b_update)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
