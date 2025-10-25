from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


load_dotenv()


class Base(DeclarativeBase):
    pass


def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    return "sqlite:///./shop.db"


DATABASE_URL: str = _build_database_url()


def _make_engine():
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
        connect_args=connect_args,
    )


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


