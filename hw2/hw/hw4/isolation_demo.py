import sqlite3
import threading
import time


def setup(db: str) -> None:
    with sqlite3.connect(db, isolation_level=None) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("DROP TABLE IF EXISTS t;")
        conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, value INTEGER);")
        conn.execute("INSERT INTO t(id, value) VALUES(1, 0);")


def read_uncommitted_demo(db: str) -> None:
    # SQLite does not support READ UNCOMMITTED for dirty reads by default; it still
    # prevents dirty reads because readers don't see uncommitted changes.
    # We demonstrate the behavior: reader won't see uncommitted writer value.
    conn_w = sqlite3.connect(db, isolation_level="DEFERRED")
    conn_r = sqlite3.connect(db, isolation_level="DEFERRED")
    try:
        cur_w = conn_w.cursor()
        cur_r = conn_r.cursor()
        cur_w.execute("BEGIN;")
        cur_w.execute("UPDATE t SET value = 100 WHERE id = 1;")

        # Reader starts after writer's uncommitted change
        cur_r.execute("BEGIN;")
        cur_r.execute("SELECT value FROM t WHERE id = 1;")
        print("READ_UNCOMMITTED_SIM value seen by reader (should be 0 in SQLite):", cur_r.fetchone()[0])

        conn_w.rollback()
        conn_r.rollback()
    finally:
        conn_w.close()
        conn_r.close()


def non_repeatable_read_demo(db: str) -> None:
    # Reader should see same snapshot in its transaction
    conn_r = sqlite3.connect(db, isolation_level="IMMEDIATE")
    try:
        c_r = conn_r.cursor()
        c_r.execute("BEGIN IMMEDIATE;")
        c_r.execute("SELECT value FROM t WHERE id = 1;")
        v1 = c_r.fetchone()[0]

        def writer():
            # Writer will block until reader commits/rollbacks due to IMMEDIATE lock
            try:
                with sqlite3.connect(db, isolation_level="IMMEDIATE") as conn_w:
                    c_w = conn_w.cursor()
                    c_w.execute("BEGIN IMMEDIATE;")
                    c_w.execute("UPDATE t SET value = value + 1 WHERE id = 1;")
                    conn_w.commit()
            except Exception as e:
                print("writer error:", e)

        t_w = threading.Thread(target=writer)
        t_w.start()
        time.sleep(0.2)
        # Second read within same txn returns same snapshot
        c_r.execute("SELECT value FROM t WHERE id = 1;")
        v2 = c_r.fetchone()[0]
        print("NON_REPEATABLE_READ_SIM v1 == v2 (SQLite snapshot):", v1 == v2)
        conn_r.commit()
        t_w.join()
    finally:
        conn_r.close()


def phantom_read_demo(db: str) -> None:
    # SQLite uses table-level locks that prevent concurrent writes during IMMEDIATE txn.
    # Reader won't see phantoms within the same transaction.
    conn_r = sqlite3.connect(db, isolation_level="IMMEDIATE")
    try:
        c_r = conn_r.cursor()
        c_r.execute("BEGIN IMMEDIATE;")
        c_r.execute("SELECT COUNT(*) FROM t;")
        n1 = c_r.fetchone()[0]

        def writer():
            try:
                with sqlite3.connect(db, isolation_level="IMMEDIATE") as conn_w:
                    c_w = conn_w.cursor()
                    c_w.execute("BEGIN IMMEDIATE;")
                    c_w.execute("INSERT INTO t(value) VALUES(10);")
                    conn_w.commit()
            except Exception as e:
                print("writer error:", e)

        t_w = threading.Thread(target=writer)
        t_w.start()
        time.sleep(0.2)
        c_r.execute("SELECT COUNT(*) FROM t;")
        n2 = c_r.fetchone()[0]
        print("PHANTOM_READ_SIM n1 == n2 (SQLite snapshot):", n1 == n2)
        conn_r.commit()
        t_w.join()
    finally:
        conn_r.close()


if __name__ == "__main__":
    db_file = "isolation_demo.db"
    setup(db_file)
    print("-- read uncommitted demo (SQLite prevents dirty read) --")
    read_uncommitted_demo(db_file)
    print("-- non-repeatable read demo (snapshot) --")
    non_repeatable_read_demo(db_file)
    print("-- phantom read demo (snapshot) --")
    phantom_read_demo(db_file)


