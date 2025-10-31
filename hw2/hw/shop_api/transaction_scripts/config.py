import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC", "postgresql://admin:admin@localhost:5432/shop_db"
)

engine = create_engine(
    DATABASE_URL,
    echo=False,  # disable SQL output for cleaner demonstration
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
