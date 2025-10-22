# tests/conftest.py
import sys
import os
import pytest

# Configuration silencieuse des imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append('/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base  # ton Base SQLAlchemy

from fastapi.testclient import TestClient
from main import app  # adapte selon ton projet
from shop_api.cart.routers import get_db as cart_get_db

# -------------------------
# Base de données de test
# -------------------------
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@postgres:5432/test_shop_db"
)

# Engine SQLAlchemy SILENCIEUX
engine = create_engine(TEST_DATABASE_URL, echo=False)  # echo=False pour supprimer les logs SQL

# Session factory pour les tests
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -------------------------
# Fixture : session DB
# -------------------------
@pytest.fixture(scope="function")
def db_session():
    """
    Fournit une session SQLAlchemy pour chaque test.
    Crée toutes les tables avant le test et les supprime après.
    """
    Base.metadata.create_all(bind=engine)  # crée les tables
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)  # supprime les tables après le test

# -------------------------
# Fixture : client FastAPI
# -------------------------
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