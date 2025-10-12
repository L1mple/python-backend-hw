from sqlalchemy import create_engine, text
import threading
import time
from __init__ import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.begin() as conn:
    conn.execute(
        text(
            """
        CREATE TABLE IF NOT EXISTS doctors (
            id     SERIAL PRIMARY KEY,
            name   TEXT NOT NULL,
            on_call BOOLEAN NOT NULL DEFAULT FALSE)
        """
        )
    )
    conn.execute(text("TRUNCATE doctors"))
    conn.execute(text("INSERT INTO doctors(name) VALUES ('Alice'), ('Bob')"))


def reset_doctors():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE doctors"))
        conn.execute(
            text(
                "INSERT INTO doctors(name, on_call) VALUES ('Alice', TRUE), ('Bob', TRUE)"
            )
        )


def tx_alice(isolation="REPEATABLE READ"):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))
        c1 = conn.execute(
            text("SELECT COUNT(*) FROM doctors WHERE on_call = TRUE")
        ).scalar_one()
        print(f"[A] first count ({isolation}):", c1)
        time.sleep(4)
        c2 = conn.execute(
            text("UPDATE doctors SET on_call = FALSE WHERE name = 'Alice'")
        )
        print(f"[A] set Alice on call, updated rows: {c2.rowcount}")
        print(f"[A] second count ({isolation}):", c2.rowcount)
        trans.commit()
        print("[ALICE] committed")
    except Exception as e:
        print("[ALICE] rolled back due to:", e)
        trans.rollback()
    finally:
        conn.close()


def tx_bob(isolation="REPEATABLE READ"):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))

        c1 = conn.execute(
            text("SELECT COUNT(*) FROM doctors WHERE on_call = TRUE")
        ).scalar_one()
        print(f"[BOB] first count ({isolation}):", c1)

        time.sleep(1)

        conn.execute(text("UPDATE doctors SET on_call = FALSE WHERE name = 'Bob'"))
        print("[BOB] sets Bob off-call")

        trans.commit()
        print("[BOB] committed")
    except Exception as e:
        print("[BOB] rolled back due to:", e)
        trans.rollback()
    finally:
        conn.close()


def tx_alice_for_update(isolation="REPEATABLE READ"):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))
        c1 = conn.execute(
            text("SELECT * FROM doctors WHERE on_call = TRUE FOR UPDATE")
        ).rowcount
        print(f"[A] first count ({isolation}):", c1)
        time.sleep(4)
        c2 = conn.execute(
            text("UPDATE doctors SET on_call = FALSE WHERE name = 'Alice'")
        )
        print(f"[A] set Alice on call, updated rows: {c2.rowcount}")
        print(f"[A] second count ({isolation}):", c2.rowcount)
        trans.commit()
        print("[ALICE] committed")
    except Exception as e:
        print("[ALICE] rolled back due to:", e)
        trans.rollback()
    finally:
        conn.close()


def tx_bob_for_update(isolation="REPEATABLE READ"):
    conn = engine.connect()
    trans = conn.begin()
    try:
        conn.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation}"))

        c1 = conn.execute(
            text("SELECT * FROM doctors WHERE on_call = TRUE FOR UPDATE")
        ).rowcount
        print(f"[BOB] first count ({isolation}):", c1)

        time.sleep(1)

        conn.execute(text("UPDATE doctors SET on_call = FALSE WHERE name = 'Bob'"))
        print("[BOB] sets Bob off-call")

        trans.commit()
        print("[BOB] committed")
    except Exception as e:
        print("[BOB] rolled back due to:", e)
        trans.rollback()
    finally:
        conn.close()


def remaining_doctors():
    with engine.begin() as conn:
        remaining = conn.execute(
            text("SELECT COUNT(*) FROM doctors WHERE on_call = TRUE")
        ).scalar_one()
        if remaining == 0:
            print("No doctors on_call remaining -> write skew!\n")
        else:
            print(f"NO WRITE SKEW, remaining doctors on_call: {remaining}\n")


def run_case(title, alice_fn, bob_fn, isolation):
    print(f"\n=== {title} ===")
    reset_doctors()

    t1 = threading.Thread(target=alice_fn, args=(isolation,))
    t2 = threading.Thread(target=bob_fn, args=(isolation,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    remaining_doctors()


def run_all():
    # 1) Write Skew — происходит на REPEATABLE READ
    run_case(
        title="WRITE SKEW under REPEATABLE READ",
        alice_fn=tx_alice,
        bob_fn=tx_bob,
        isolation="REPEATABLE READ",
    )

    # 2) SERIALIZABLE предотвращает — ожидаем rollback/serialization_failure
    run_case(
        title="WRITE SKEW under SERIALIZABLE (with rollback expected)",
        alice_fn=tx_alice,
        bob_fn=tx_bob,
        isolation="SERIALIZABLE",
    )

    # 3) FOR UPDATE на READ COMMITTED — не спасает (каждый блокирует свою строку)
    run_case(
        title="No lock protection with FOR UPDATE under READ COMMITTED",
        alice_fn=tx_alice_for_update,
        bob_fn=tx_bob_for_update,
        isolation="READ COMMITTED",
    )

    # 4) FOR UPDATE + REPEATABLE READ — предотвращает write skew
    run_case(
        title="NO WRITE SKEW with REPEATABLE READ + SELECT ... FOR UPDATE",
        alice_fn=tx_alice_for_update,
        bob_fn=tx_bob_for_update,
        isolation="REPEATABLE READ",
    )
