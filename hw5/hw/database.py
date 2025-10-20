from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base

import os

if os.getenv("TESTING"):
    # Pour les tests - SQLite en mémoire (rapide et isolé)
    DATABASE_URL = "sqlite:///:memory:"
    # ou
    DATABASE_URL = "sqlite:///./test.db"
else:

    DATABASE_URL = "postgresql://postgres:password@postgres:5432/shop_db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()