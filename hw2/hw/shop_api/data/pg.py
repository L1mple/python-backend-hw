import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PG_DSN = os.getenv("PG_DSN")

engine = create_engine(PG_DSN, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
