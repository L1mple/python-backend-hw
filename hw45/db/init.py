from sqlalchemy.ext.declarative import declarative_base


DATABASE_URL_BASE = "postgresql://postgres:postgres@localhost:5432"
DB_NAME = "db"
DATABASE_URL = f"{DATABASE_URL_BASE}/{DB_NAME}"

Base = declarative_base()