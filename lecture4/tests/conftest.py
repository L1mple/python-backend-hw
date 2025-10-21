import os
import pathlib
import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from main import app
import database as db_mod  # your get_db uses SessionLocal bound to DATABASE_URL

# Тестовая БД и инициализация схемы
TEST_DSN_SQLA = os.environ.get("DATABASE_URL", "postgresql+psycopg://shop:shop@localhost:5432/shop_test")
TEST_DSN_PSQL = TEST_DSN_SQLA.replace("+psycopg", "")  # для psql команд

INIT_SQL = (pathlib.Path(__file__).resolve().parents[1] / "init.sql").read_text()

engine = create_engine(TEST_DSN_SQLA, pool_pre_ping=True, future=True)
SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def reset_schema():
    with psycopg.connect(TEST_DSN_PSQL, autocommit=True) as c, c.cursor() as cur:
        cur.execute("TRUNCATE cart_items, carts, items RESTART IDENTITY")
        # начальные данные и индекс
        cur.execute("""
        INSERT INTO items(name,price,deleted) VALUES ('A',100,false),('B',200,false);
        """)

@pytest.fixture(scope="session", autouse=True)
def _ensure_schema():
    # применяем init.sql один раз на тестовую БД
    with psycopg.connect(TEST_DSN_PSQL, autocommit=True) as c, c.cursor() as cur:
        cur.execute(INIT_SQL)

@pytest.fixture(autouse=True)
def _db_clean():
    reset_schema()
    yield
    reset_schema()

@pytest.fixture
def client(monkeypatch):
    # Подменяем зависимость get_db на тестовую сессию
    def _get_db_override():
        db = SessionTesting()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[db_mod.get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
