import os
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://app:app@db:5432/app")

def engine_with_echo(echo=False):
    return create_engine(DATABASE_URL, pool_pre_ping=True, future=True, echo=echo)

@contextmanager
def begin_tx(engine, iso: str) -> Connection:
    conn = engine.connect().execution_options(isolation_level=iso)
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()

def reset_demo_data():
    eng = engine_with_echo()
    with eng.begin() as c:
        c.execute(text("DELETE FROM items"))
        c.execute(text("INSERT INTO items (name, price) VALUES ('A1', 100), ('B1', 200)"))

def sleep(s):
    time.sleep(s)
