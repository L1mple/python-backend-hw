import uuid
import threading
from contextlib import contextmanager

import pytest
from sqlalchemy import Connection
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

pytestmark = pytest.mark.usefixtures("run_migrations")

def _unique_table() -> str:
    return f'isol_{uuid.uuid4().hex[:8]}'

def create_iso_table(conn: Connection, name: str):
    conn.exec_driver_sql(f'CREATE TABLE "{name}" (id SERIAL PRIMARY KEY, v INT NOT NULL)')
    conn.exec_driver_sql(f'INSERT INTO "{name}" (v) VALUES (100)')

def drop_table(engine: Engine, name: str):
    with engine.begin() as c:
        c.exec_driver_sql(f'DROP TABLE IF EXISTS "{name}" CASCADE')

def get_v(conn: Connection, tbl: str) -> int:
    return conn.exec_driver_sql(f'SELECT v FROM "{tbl}" WHERE id=1').scalar_one()

def set_v(conn: Connection, tbl: str, value: int):
    conn.exec_driver_sql(f'UPDATE "{tbl}" SET v={value} WHERE id=1')

def count_gt(conn: Connection, tbl: str, thr: int) -> int:
    return conn.exec_driver_sql(f'SELECT COUNT(*) FROM "{tbl}" WHERE v > {thr}').scalar_one()

def insert_row(conn: Connection, tbl: str, v: int):
    conn.exec_driver_sql(f'INSERT INTO "{tbl}" (v) VALUES ({v})')

def tx(engine: Engine, isolation: str, commit : bool = True):
    @contextmanager
    def _cm():
        with engine.connect().execution_options(isolation_level=isolation) as conn:
            t = conn.begin()
            try:
                yield conn
                if commit:
                    t.commit()
                else:
                    t.rollback()
            except Exception:
                t.rollback()
                raise
    return _cm()

def test_no_dirty_read_under_read_uncommitted(engine: Engine):
    # Postgres doesn't implement read uncommitted
    tbl = _unique_table()
    try:
        with engine.begin() as c:
            create_iso_table(c, tbl)
        with tx(engine, "READ UNCOMMITTED", commit=False) as t1:
            set_v(t1, tbl, 200)
            with tx(engine, "READ UNCOMMITTED") as t2:
                assert get_v(t2, tbl) == 100
        with tx(engine, "READ UNCOMMITTED") as c:
            assert get_v(c, tbl) == 100
    finally:
        drop_table(engine, tbl)

def test_non_repeatable_read_on_read_committed(engine: Engine):
    tbl = _unique_table()
    try:
        with engine.begin() as c:
            create_iso_table(c, tbl)
        with tx(engine, "READ COMMITTED") as t1:
            first = get_v(t1, tbl)
            with tx(engine, "READ COMMITTED") as t2:
                set_v(t2, tbl, 300)
            second = get_v(t1, tbl)
            assert first != second
    finally:
        drop_table(engine, tbl)

def test_phantom_on_read_committed(engine: Engine):
    tbl = _unique_table()
    try:
        with engine.begin() as c:
            create_iso_table(c, tbl)
        with tx(engine, "READ COMMITTED") as t1:
            c1 = count_gt(t1, tbl, 150)
            with tx(engine, "READ COMMITTED") as t2:
                insert_row(t2, tbl, 200)
            c2 = count_gt(t1, tbl, 150)
            assert c2 != c1
    finally:
        drop_table(engine, tbl)

def test_no_phantom_on_repeatable_read(engine: Engine):
    tbl = _unique_table()
    try:
        with engine.begin() as c:
            create_iso_table(c, tbl)
        with tx(engine, "REPEATABLE READ") as t1:
            c1 = count_gt(t1, tbl, 150)
            with tx(engine, "REPEATABLE READ") as t2:
                insert_row(t2, tbl, 200)
            c2 = count_gt(t1, tbl, 150)
            assert c2 == c1
    finally:
        drop_table(engine, tbl)

def test_write_skew_allowed_under_repeatable_read(engine: Engine):
    tbl = _unique_table()
    try:
        with engine.begin() as c:
            create_iso_table(c, tbl)


        def worker():
            with tx(engine, "REPEATABLE READ") as conn:
                cnt = count_gt(conn, tbl, 200)
                if cnt == 0:
                    insert_row(conn, tbl, 300)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start()
        t1.join(); t2.join()

        with engine.connect() as c:
            assert count_gt(c, tbl, 200) != 1
    finally:
        drop_table(engine, tbl)

def test_write_skew_disallowed_under_serialized(engine: Engine):
    tbl = _unique_table()
    try:
        with engine.begin() as c:
            create_iso_table(c, tbl)

        barrier = threading.Barrier(2)
        errors = []

        def worker():
            barrier.wait()
            try:
                with tx(engine, "SERIALIZABLE") as conn:
                    cnt = count_gt(conn, tbl, 200)
                    if cnt == 0:
                        insert_row(conn, tbl, 300)
            except OperationalError as e:
                if getattr(e.orig, "pgcode", None) == "40001":
                    errors.append(40001)
                else:
                    raise

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert len(errors) >= 1

        with engine.connect() as c:
            assert count_gt(c, tbl, 200) == 1

    finally:
        drop_table(engine, tbl)
