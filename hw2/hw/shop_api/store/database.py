from __future__ import annotations

import os
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

def _database_url() -> str:
    return os.getenv("SHOP_DATABASE_URL", "sqlite:///./shop.sqlite3")


def _isolation_level() -> str:
    level = os.getenv("SHOP_DB_ISOLATION_LEVEL", "READ UNCOMMITTED")
    return level.upper()


class Base(DeclarativeBase):
    pass


DATABASE_URL = _database_url()
ISOLATION_LEVEL = _isolation_level()

_engine_kwargs: dict[str, object] = {}
if make_url(DATABASE_URL).get_backend_name().startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    future=True,
    isolation_level=ISOLATION_LEVEL,
    **_engine_kwargs,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db() -> None:
    from shop_api.store import db_models

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    session: Session = SessionLocal()
    try:
        session.begin()
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session
