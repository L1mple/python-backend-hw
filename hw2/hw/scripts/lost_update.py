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


def reset_accounts():
    with engine.begin() as conn:
        conn.execute(text("UPDATE accounts SET balance = 1000 WHERE id = 1"))


def tx_a_lost_update():
    conn = engine.connect()
    trans = conn.begin()
    try:
        r1 = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1")
        ).scalar_one()
        print("[A] read:", r1)
        time.sleep(2)
        conn.execute(
            text("UPDATE accounts SET balance = :new WHERE id = 1"), {"new": r1 + 50}
        )
        print("[A] wrote:", r1 + 50)
        trans.commit()
    finally:
        conn.close()


def tx_b_lost_update():
    conn = engine.connect()
    trans = conn.begin()
    try:
        r1 = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1")
        ).scalar_one()
        print("[B] read:", r1)
        time.sleep(1)
        conn.execute(
            text("UPDATE accounts SET balance = :new WHERE id = 1"), {"new": r1 + 50}
        )
        print("[B] wrote:", r1 + 50)
        trans.commit()
    finally:
        conn.close()


def tx_a_lost_update_for_update():
    conn = engine.connect()
    tnans = conn.begin()
    try:
        r1 = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1 FOR UPDATE")
        ).scalar_one()
        print("[A] read:", r1)
        time.sleep(2)
        conn.execute(
            text("UPDATE accounts SET balance = :new WHERE id = 1"), {"new": r1 + 50}
        )
        print("[A] wrote:", r1 + 50)
        tnans.commit()
    finally:
        conn.close()


def tx_b_lost_update_for_update():
    conn = engine.connect()
    tnans = conn.begin()
    try:
        r1 = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1 FOR UPDATE")
        ).scalar_one()
        print("[B] read:", r1)
        time.sleep(1)
        conn.execute(
            text("UPDATE accounts SET balance = :new WHERE id = 1"), {"new": r1 + 50}
        )
        print("[B] wrote:", r1 + 50)
        tnans.commit()
    finally:
        conn.close()


def tx_a_lost_update_atomic():
    with engine.begin() as conn:
        new_balance = conn.execute(
            text(
                """
                UPDATE accounts
                SET balance = balance + :inc
                WHERE id = 1
                RETURNING balance
            """
            ),
            {"inc": 50},
        ).scalar_one()
        print("[A] atomic increment, new balance:", new_balance)


def tx_b_lost_update_atomic():
    with engine.begin() as conn:
        new_balance = conn.execute(
            text(
                """
                UPDATE accounts
                SET balance = balance + :inc
                WHERE id = 1
                RETURNING balance
            """
            ),
            {"inc": 50},
        ).scalar_one()
        print("[B] atomic increment, new balance:", new_balance)


def show_final(label="[final]"):
    conn = engine.connect()
    try:
        val = conn.execute(
            text("SELECT balance FROM accounts WHERE id = 1")
        ).scalar_one()
        print(f"{label} balance:", val)
        print("Final balance:", val, " (expected 1100, got WRONG if 1050)")
    finally:
        conn.close()


def run_all():
    print("\n=== LOST UPDATE (wrong behavior) ===")
    t1 = threading.Thread(target=tx_a_lost_update)
    t2 = threading.Thread(target=tx_b_lost_update)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    show_final()
    reset_accounts()

    print("\n=== LOST UPDATE with SELECT ... FOR UPDATE (correct behavior) ===")
    t1 = threading.Thread(target=tx_a_lost_update_for_update)
    t2 = threading.Thread(target=tx_b_lost_update_for_update)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    show_final()
    reset_accounts()

    print("\n=== LOST UPDATE with atomic UPDATE ... RETURNING (correct behavior) ===")
    t1 = threading.Thread(target=tx_a_lost_update_atomic)
    t2 = threading.Thread(target=tx_b_lost_update_atomic)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    show_final()
