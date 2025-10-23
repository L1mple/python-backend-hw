# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

def get_database_url():
    if os.getenv("TESTING"):
        return "postgresql://postgres:password@postgres:5432/test_shop_db"
    else:
        return os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/shop_db")

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
