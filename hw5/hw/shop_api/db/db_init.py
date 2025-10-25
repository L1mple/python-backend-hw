from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import DATABASE_URL

# Create database engine
engine = create_engine(DATABASE_URL)

try:
    connection = engine.connect()
    connection.close()
    print("Connection to the database was successful.")
except Exception as e:
    print(f"Error connecting to the database: {e}")
# engine = create_engine(settings.DATABASE_URL, echo=True, future=True)

# Create database declarative base
Base = declarative_base()
Base.metadata.create_all(bind=engine)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()