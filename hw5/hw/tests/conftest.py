import pytest
import sys
import os

# Solution universelle - ajoute le chemin courant
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base, get_db
from main import app

# Configuration base de données
IS_CI = os.getenv('GITHUB_ACTIONS') == 'true'
TEST_DATABASE_URL = os.getenv("DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/test_db" if IS_CI 
    else "sqlite:///./test.db"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # 🎯 CORRECTION AVANCÉE : Utiliser les transactions
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()  # Annule tous les changements
        connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()