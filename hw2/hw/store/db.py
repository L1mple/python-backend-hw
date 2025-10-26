from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base


engine = create_engine("sqlite:///./shop.sqlite", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    # ensure clean schema for tests
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


init_db()
