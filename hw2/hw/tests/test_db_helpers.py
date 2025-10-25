from __future__ import annotations

import importlib
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shop_api.orm import Base, Item
import shop_api.db as db_mod


def _mk_local_sessionmaker():
    """Локальный in-memory движок, общий для всех соединений."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def test_get_db_commit(monkeypatch):
    """Проверяем, что get_db делает commit, если ошибок нет."""
    TestingSessionLocal = _mk_local_sessionmaker()
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSessionLocal, raising=True)

    gen = db_mod.get_db()
    s = next(gen)  # получили сессию
    # вставим одну запись
    s.add(Item(name="X", price=1.0, deleted=False))
    # закрываем генератор "нормальным" способом, чтобы прошёл commit
    try:
        next(gen)  # StopIteration -> сработает finally ветка в get_db
    except StopIteration:
        pass

    # новая независимая сессия должна увидеть запись (commit прошёл)
    s2 = TestingSessionLocal()
    try:
        count = s2.execute(text("SELECT COUNT(*) FROM items")).scalar_one()
        assert count == 1
    finally:
        s2.close()


def test_get_db_rollback(monkeypatch):
    """Проверяем, что get_db делает rollback при исключении."""
    TestingSessionLocal = _mk_local_sessionmaker()
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSessionLocal, raising=True)

    gen = db_mod.get_db()
    s = next(gen)
    s.add(Item(name="Y", price=2.0, deleted=False))
    # Скормим исключение внутрь генератора -> должна сработать ветка rollback
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))

    s2 = TestingSessionLocal()
    try:
        count = s2.execute(text("SELECT COUNT(*) FROM items")).scalar_one()
        assert count == 0  # откатилось
    finally:
        s2.close()


def test_session_scope_commit_and_rollback(monkeypatch):
    """Покрываем обе ветки session_scope: commit и rollback."""
    TestingSessionLocal = _mk_local_sessionmaker()
    monkeypatch.setattr(db_mod, "SessionLocal", TestingSessionLocal, raising=True)

    # commit ветка
    with db_mod.session_scope() as s:
        s.add(Item(name="A", price=3.0, deleted=False))

    # rollback ветка
    with pytest.raises(ValueError):
        with db_mod.session_scope() as s:
            s.add(Item(name="B", price=4.0, deleted=False))
            raise ValueError("fail")

    # Проверим: только A закоммитился
    s2 = TestingSessionLocal()
    try:
        rows = s2.execute(text("SELECT name FROM items ORDER BY id")).scalars().all()
        assert rows == ["A"]
    finally:
        s2.close()


def test_settings_uses_database_url(monkeypatch):
    """Покрываем ветку config: если DATABASE_URL задан — используется он."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@h:5432/dbname")
    # Перезагружаем модуль настроек, чтобы он перечитал .env/окружение
    from shop_api import config as cfg
    importlib.reload(cfg)
    assert cfg.settings.sqlalchemy_url == "postgresql+psycopg2://u:p@h:5432/dbname"
