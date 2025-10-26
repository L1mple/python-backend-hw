import os
import pathlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shop_api.main import app
from shop_api.db import Base, get_db
import shop_api.models

@pytest.fixture(scope="session")
def _tmp_db_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("db") / "test.db"
    return str(p)

@pytest.fixture(scope="session")
def _engine(_tmp_db_path):
    url = f"sqlite:///{_tmp_db_path}"
    os.environ["DATABASE_URL"] = url
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def db_session(_engine):
    TestingSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()