from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# URL de connexion à PostgreSQL
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