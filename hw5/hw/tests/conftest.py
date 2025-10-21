import sys
import os

sys.path.append('/app')
# Solution universelle - ajoute le chemin courant
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app

# Détection de l'environnement CI (GitHub Actions)
# Configuration base de données
IS_CI = os.getenv('GITHUB_ACTIONS') == 'true'
TEST_DATABASE_URL = os.getenv("DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/test_db" if IS_CI 
    else "sqlite:///./test.db"
)

# 🛠 Configuration de la base de données selon l'environnement
if IS_CI:
    # ✅ En CI : PostgreSQL (nom d’hôte = localhost)
    TEST_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/test_db"
    )
else:
    # ✅ En local : SQLite
    TEST_DATABASE_URL = "sqlite:///./test.db"

# Création du moteur SQLAlchemy
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Crée une session de base de données temporaire pour les tests"""
    # 🎯 CORRECTION AVANCÉE : Utiliser les transactions
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        # En local, on nettoie la base après chaque test
        if not IS_CI:
            Base.metadata.drop_all(bind=engine)

        transaction.rollback()  # Annule tous les changements
        connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Crée un client de test FastAPI en utilisant la session de test"""
    def override_get_db():
        yield db_session

        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client