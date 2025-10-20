from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base

import os

# URL de connexion à PostgreSQL
# Dans ton conftest.py ou database.py

if os.getenv("TESTING"):
    # Pour les tests - SQLite en mémoire (rapide et isolé)
    DATABASE_URL = "sqlite:///:memory:"
    # ou
    DATABASE_URL = "sqlite:///./test.db"
else:
    # Pour le développement - utilise ton URL normale
    DATABASE_URL = "postgresql://postgres:password@postgres:5432/shop_db"

# Moteur de connexion
engine = create_engine(DATABASE_URL)

# Session pour interagir avec la base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour tous nos modèles
Base = declarative_base()

# Fonction pour obtenir une session (utilisée dans les routes)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()