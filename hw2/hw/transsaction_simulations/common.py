import os
import time
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Integer,
    select,
    insert,
    text,
)
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://shop_user:shop_password@localhost:5432/shop_db",
)


def make_engine(isolation_level: str) -> Engine:
    return create_engine(
        DATABASE_URL,
        future=True,
        isolation_level=isolation_level,
        pool_pre_ping=True,
    )


metadata = MetaData()

products = Table(
    "tx_products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("price", Integer, nullable=False),
)

@contextmanager
def begin_conn(engine: Engine):
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    finally:
        conn.close()


def reset_demo_data():
    admin_engine = create_engine(DATABASE_URL, future=True)
    with admin_engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS tx_products")
        metadata.create_all(conn)

        conn.execute(
            insert(products),
            [
                {"name": "A", "price": 100},
                {"name": "B", "price": 200},
            ],
        )


def sleep(seconds: float):
    time.sleep(seconds)


