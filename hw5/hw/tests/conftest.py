import pytest
import sys
import os
import importlib.util

# Chemin absolu vers la racine du projet
current_file = os.path.abspath(__file__)
tests_dir = os.path.dirname(current_file)
project_root = os.path.dirname(tests_dir)

print(f"🔍 DEBUG INFO:")
print(f"Current file: {current_file}")
print(f"Tests dir: {tests_dir}") 
print(f"Project root: {project_root}")
print(f"Files in project root: {os.listdir(project_root)}")

# Ajouter explicitement au path
sys.path.insert(0, project_root)
print(f"Python path: {sys.path}")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# IMPORT FORCÉ - méthode robuste
def import_module(module_name, file_path):
    """Importe un module depuis un chemin absolu"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Importer database.py
database_path = os.path.join(project_root, "database.py")
print(f"Database path: {database_path}")
print(f"Database exists: {os.path.exists(database_path)}")

if os.path.exists(database_path):
    database = import_module("database", database_path)
    Base = database.Base
    get_db = database.get_db
    print("✅ Database imported successfully")
else:
    raise FileNotFoundError(f"database.py not found at {database_path}")

# Importer main.py
main_path = os.path.join(project_root, "main.py")
print(f"Main path: {main_path}")
print(f"Main exists: {os.path.exists(main_path)}")

if os.path.exists(main_path):
    main = import_module("main", main_path)
    app = main.app
    print("✅ Main imported successfully")
else:
    raise FileNotFoundError(f"main.py not found at {main_path}")

# Configuration de la base de données
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/test_db")
print(f"Using database: {TEST_DATABASE_URL}")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    print("🔄 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
        print("✅ Database session completed")
    finally:
        session.close()
        print("🔚 Database session closed")

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    print("🔚 Test client cleaned up")