import pytest
import sys
import os

# Remonter d'un niveau depuis tests/ pour arriver à hw5/hw/
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Import avec chemin relatif
try:
    # Essayer d'importer depuis le répertoire parent
    import importlib.util
    spec = importlib.util.spec_from_file_location("database", os.path.join(project_root, "database.py"))
    database = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database)
    Base = database.Base
    get_db = database.get_db
    
    spec = importlib.util.spec_from_file_location("main", os.path.join(project_root, "main.py"))
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)
    app = main.app
    
except Exception as e:
    print(f"Import error: {e}")
    raise

# Le reste du code reste identique...
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/test_db")
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

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()