from __future__ import annotations

import contextlib
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool  # <-- важно

from shop_api.orm import Base
from shop_api.main import app as fastapi_app

# --- Тестовый SQLite (одна общая in-memory БД для всех соединений) ---
engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,        # <-- ключ: один пул/одно «соединение» для всех
    future=True,
)

# Включаем FK для SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()

TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Создаём схему один раз
Base.metadata.create_all(bind=engine)


@contextlib.contextmanager
def _session_scope() -> Generator[Session, None, None]:
    db: Session = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    # Чистим таблицы между тестами
    with _session_scope() as s:
        s.execute(text("DELETE FROM cart_items"))
        s.execute(text("DELETE FROM carts"))
        s.execute(text("DELETE FROM items"))
        yield s


@pytest.fixture()
def app(db_session: Session):
    # Переопределяем зависимость get_db на тестовую сессию
    from shop_api import db as prod_db

    def _get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    fastapi_app.dependency_overrides[prod_db.get_db] = _get_db
    return fastapi_app


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)
