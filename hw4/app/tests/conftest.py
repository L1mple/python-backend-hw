import pytest
from fastapi.testclient import TestClient

from src.db import engine
from src.models import Base
from src.app import app as fastapi_app

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture()
def client():
    with TestClient(fastapi_app) as c:
        yield c
