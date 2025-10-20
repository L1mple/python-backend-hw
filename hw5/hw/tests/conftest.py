import pytest
import sys
import os

# Chemin ABSOLU vers la racine du projet hw5/hw
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Files in root: {os.listdir(project_root)}")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Import depuis la racine
try:
    from database import Base, get_db
    from main import app
    print("✅ Successfully imported from root")
except ImportError as e:
    print(f"❌ Import error: {e}")
    # Liste tous les fichiers pour debug
    print("Files in directory:")
    for file in os.listdir(project_root):
        print(f"  - {file}")
    raise

# Utilise PostgreSQL en CI, SQLite en local
IS_CI = os.getenv('GITHUB_ACTIONS') == 'true'
TEST_DATABASE_URL = os.getenv("DATABASE_URL", 
    "postgresql://postgres:password@postgres:5432/test_db" if IS_CI 
    else "sqlite:///./test.db"
)

print(f"Database URL: {TEST_DATABASE_URL}")

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
        if not IS_CI:
            Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()