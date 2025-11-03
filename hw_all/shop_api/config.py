import os


POSTGRES_USER = os.getenv("POSTGRES_USER", "shop_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "shop_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.getenv("POSTGRES_DB", "shop_db")


SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
