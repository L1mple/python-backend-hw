import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://test-user:test-pass@localhost:5542/test-db"
)
