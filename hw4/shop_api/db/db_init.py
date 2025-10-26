from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .database import Base, ItemDB, CartDB, CartItemDB
import os


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/shop_db")


engine = create_engine(DATABASE_URL)


Base.metadata.create_all(bind=engine)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
