import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hw5.shop_api.main import app, Base, get_db

DATABASE_URL = "postgresql://postgres:password@postgres:5432/hw5_db"

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture()
def client():
    return TestClient(app)
