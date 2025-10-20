import pytest
import sys
import os

# AJOUTEZ CETTE LIGNE MANQUANTE
sys.path.append('/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base, get_db
from main import app

# Utilise SQLite en local, PostgreSQL sur GitHub
IS_CI = os.getenv('GITHUB_ACTIONS') == 'true'
TEST_DATABASE_URL = os.getenv("DATABASE_URL", 
    "postgresql://postgres:password@postgres:5432/test_db" if IS_CI 
    else "sqlite:///./test.db"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        if not IS_CI:  # Ne supprime les tables qu'en local
            Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()