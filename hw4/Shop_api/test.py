# test_db_connection.py

from sqlalchemy import create_engine, text
import os

# Récupération de l'URL depuis l'environnement ou par défaut
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:1234@localhost:5432/shop_db"
)

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("✅ Connexion réussie ! Résultat :", result.scalar())
except Exception as e:
    print("❌ Erreur de connexion :", e)