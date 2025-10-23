# tests/conftest.py
import sys
import os
import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append('/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base 

from fastapi.testclient import TestClient
from main import app  # adapte selon ton projet
from shop_api.cart.routers import get_db as cart_get_db


TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@postgres:5432/test_shop_db"
)


engine = create_engine(TEST_DATABASE_URL, echo=False)  


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Fournit une session SQLAlchemy pour chaque test.
    Crée toutes les tables avant le test et les supprime après.
    """
    Base.metadata.create_all(bind=engine)  
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine) 

@pytest.fixture(scope="function")
def client(db_session):
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[cart_get_db] = _get_test_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}