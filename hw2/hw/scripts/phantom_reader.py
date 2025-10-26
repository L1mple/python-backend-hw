from sqlalchemy import create_engine, text
import threading
import time
from __init__ import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.begin() as conn:
    conn.execute(
        text(
            """
        DROP TABLE IF EXISTS orders
    """
        )
    )
    conn.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS orders (
            id     SERIAL PRIMARY KEY,
            amount INT NOT NULL
        )
    """
        )
    )
    conn.execute(text("TRUNCATE orders"))
    conn.execute(text("INSERT INTO orders(amount) VALUES (120), (80), (50)"))


def reset_orders():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE orders"))
        conn.execute(text("INSERT INTO orders(amount) VALUES (120), (80), (50)"))


def tx_a_range_count(isolation="READ COMMITTED"):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))
        c1 = conn.execute(
            text("SELECT COUNT(*) FROM orders WHERE amount > 100")
        ).scalar_one()
        print(f"[A] first count ({isolation}):", c1)
        time.sleep(4)
        c2 = conn.execute(
            text("SELECT COUNT(*) FROM orders WHERE amount > 100")
        ).scalar_one()
        print(f"[A] second count ({isolation}):", c2)
        trans.commit()
    finally:
        conn.close()


def tx_b_insert():
    time.sleep(1)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO orders(amount) VALUES (200)"))
        print("[B] inserted amount=200")


def run_all():
    print("\n=== TEST READ COMMITTED ===")
    t1 = threading.Thread(
        target=tx_a_range_count, kwargs={"isolation": "READ COMMITTED"}
    )
    t2 = threading.Thread(target=tx_b_insert)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE orders"))
        conn.execute(text("INSERT INTO orders(amount) VALUES (120), (80), (50)"))
    reset_orders()

    print("\n=== TEST REPEATABLE READ ===")
    # Works the same as SERIALIZABLE in this case. No phantom reads.
    # serializable snapshot isolation, SSI
    t1 = threading.Thread(
        target=tx_a_range_count, kwargs={"isolation": "REPEATABLE READ"}
    )
    t2 = threading.Thread(target=tx_b_insert)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    reset_orders()

    print("\n=== TEST SERIALIZABLE ===")
    t1 = threading.Thread(target=tx_a_range_count, kwargs={"isolation": "SERIALIZABLE"})
    t2 = threading.Thread(target=tx_b_insert)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    reset_orders()
