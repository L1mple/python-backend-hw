import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./app.db")
engine=create_engine(DATABASE_URL, future=True)
class Base(DeclarativeBase): pass
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db():
    from . import models
    Base.metadata.create_all(bind=engine)