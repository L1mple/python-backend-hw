import os
import time
import threading
from typing import Tuple

from sqlalchemy import create_engine, select, text, delete
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.engine import Connection

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, future=True, autocommit=False, autoflush=False)
Base = declarative_base()


class Note(Base):
    __tablename__ = "tx_notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(64), nullable=False)
    value = Column(Integer, nullable=False, default=0)


def setup_demo_data() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE tx_notes"))
    with SessionLocal() as db:
        db.add_all([
            Note(category="demo", value=10),
            Note(category="demo", value=20),
            Note(category="other", value=5),
        ])
        db.commit()


def connect_with_isolation(level: str) -> Connection:
    conn = engine.connect().execution_options(isolation_level=level)
    return conn


# --- Dirty Read ---

def dirty_read(reader_isolation: str) -> Tuple[int, int]:
    setup_demo_data()
    with engine.begin() as conn:
        conn.execute(text("UPDATE tx_notes SET value = 10 WHERE id = 1"))

    writer = connect_with_isolation("READ COMMITTED")
    reader = connect_with_isolation(reader_isolation)
    try:
        wtx = writer.begin()
        writer.execute(text("UPDATE tx_notes SET value = 999 WHERE id = 1"))

        rtx = reader.begin()
        val_before = reader.execute(text("SELECT value FROM tx_notes WHERE id = 1")).scalar_one()

        wtx.rollback()
        rtx.commit()

        with engine.begin() as conn:
            val_after = conn.execute(text("SELECT value FROM tx_notes WHERE id = 1")).scalar_one()
        return int(val_before), int(val_after)
    finally:
        writer.close()
        reader.close()


# --- Non-Repeatable Read ---

def non_repeatable_read(tx_isolation: str) -> Tuple[int, int]:
    setup_demo_data()
    with engine.begin() as conn:
        conn.execute(text("UPDATE tx_notes SET value = 10 WHERE id = 1"))

    reader = connect_with_isolation(tx_isolation)
    writer = connect_with_isolation("READ COMMITTED")
    try:
        rtx = reader.begin()
        v1 = reader.execute(text("SELECT value FROM tx_notes WHERE id = 1")).scalar_one()

        with writer.begin():
            writer.execute(text("UPDATE tx_notes SET value = 777 WHERE id = 1"))

        v2 = reader.execute(text("SELECT value FROM tx_notes WHERE id = 1")).scalar_one()
        rtx.commit()
        return int(v1), int(v2)
    finally:
        reader.close()
        writer.close()


# --- Phantom Reads ---

def phantom_read(reader_isolation: str) -> Tuple[int, int]:
    setup_demo_data()

    reader = connect_with_isolation(reader_isolation)
    try:
        rtx = reader.begin()
        c1 = reader.execute(text("SELECT COUNT(*) FROM tx_notes WHERE category = 'demo'")) .scalar_one()

        w = connect_with_isolation("READ COMMITTED")
        try:
            with w.begin():
                if reader_isolation.upper() == "SERIALIZABLE":
                    w.execute(text("SET SESSION innodb_lock_wait_timeout = 1"))
                try:
                    w.execute(text("INSERT INTO tx_notes (category, value) VALUES ('demo', 30)"))
                except Exception:
                    pass
        finally:
            w.close()

        c2 = reader.execute(text("SELECT COUNT(*) FROM tx_notes WHERE category = 'demo'")) .scalar_one()
        rtx.commit()
        return int(c1), int(c2)
    finally:
        reader.close()


def run_all():
    print(f"Using DATABASE_URL={DATABASE_URL}")
    print("\n=== Dirty Read Demo ===")
    before, after = dirty_read("READ UNCOMMITTED")
    print(f"READ UNCOMMITTED: saw uncommitted value={before}, after rollback committed value={after}")
    before_rc, after_rc = dirty_read("READ COMMITTED")
    print(f"READ COMMITTED: saw committed value only={before_rc}, final value={after_rc}")

    print("\n=== Non-Repeatable Read Demo ===")
    v1_rc, v2_rc = non_repeatable_read("READ COMMITTED")
    print(f"READ COMMITTED: first={v1_rc}, second={v2_rc} (changed)")
    v1_rr, v2_rr = non_repeatable_read("REPEATABLE READ")
    print(f"REPEATABLE READ: first={v1_rr}, second={v2_rr} (stable)")

    print("\n=== Phantom Read Demo ===")
    c1_rc, c2_rc = phantom_read("READ COMMITTED")
    print(f"READ COMMITTED: count1={c1_rc}, count2={c2_rc} (phantom)")
    c1_ser, c2_ser = phantom_read("SERIALIZABLE")
    print(f"SERIALIZABLE: count1={c1_ser}, count2={c2_ser} (no phantom expected)")


if __name__ == "__main__":
    print(f"Using DATABASE_URL={DATABASE_URL}")
    run_all()