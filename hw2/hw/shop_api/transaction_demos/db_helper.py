import os
import time
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://shop_user:shop_password@postgres:5432/shop_db"
)


def get_engine(isolation_level=None):
    if isolation_level:
        return create_engine(
            DATABASE_URL,
            isolation_level=isolation_level,
            echo=False
        )
    return create_engine(DATABASE_URL, echo=False)


@contextmanager
def get_session(isolation_level=None) -> Generator[Session, None, None]:
    engine = get_engine(isolation_level)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def setup_demo_table(session: Session):
    session.execute(text("DROP TABLE IF EXISTS demo_accounts CASCADE;"))
    session.execute(text("""
        CREATE TABLE demo_accounts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            balance DECIMAL(10, 2) NOT NULL DEFAULT 0
        );
    """))
    session.commit()


def cleanup_demo_table(session: Session):
    session.execute(text("DROP TABLE IF EXISTS demo_accounts CASCADE;"))
    session.commit()


def insert_test_data(session: Session):
    session.execute(text("""
        INSERT INTO demo_accounts (name, balance) 
        VALUES ('user1', 1000.00), ('user2', 500.00);
    """))
    session.commit()


def get_balance(session: Session, name: str) -> float:
    result = session.execute(
        text("SELECT balance FROM demo_accounts WHERE name = :name"),
        {"name": name}
    )
    return result.scalar()


def update_balance(session: Session, name: str, balance: float):
    session.execute(
        text("UPDATE demo_accounts SET balance = :balance WHERE name = :name"),
        {"name": name, "balance": balance}
    )


def insert_account(session: Session, name: str, balance: float):
    session.execute(
        text("INSERT INTO demo_accounts (name, balance) VALUES (:name, :balance)"),
        {"name": name, "balance": balance}
    )


def count_accounts(session: Session, min_balance: float = 0) -> int:
    result = session.execute(
        text("SELECT COUNT(*) FROM demo_accounts WHERE balance >= :min_balance"),
        {"min_balance": min_balance}
    )
    return result.scalar()
