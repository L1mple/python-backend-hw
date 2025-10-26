from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

DATABASE_CONNECTION = os.getenv("DATABASE_URL", 
    "postgresql://stepa_user:stepa_password@localhost:5433/stepa_shop_db")

db_engine = create_engine(DATABASE_CONNECTION)

Base.metadata.create_all(bind=db_engine)

DatabaseSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

def get_database_session():
    session = DatabaseSession()
    try:
        yield session
    finally:
        session.close()
