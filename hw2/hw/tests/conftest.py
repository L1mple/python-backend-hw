import pytest
from fastapi.testclient import TestClient
from shop_api.main import app
from shop_api.core.database import Base, engine, SessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def client():
    return TestClient(app)

@pytest.fixture()
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()