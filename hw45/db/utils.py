from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.init import DATABASE_URL, DATABASE_URL_BASE, DB_NAME, Base


def create_database(db_url, db_name):
    default_engine = create_engine(
        f"{db_url}/postgres",
        isolation_level="AUTOCOMMIT",
    )

    with default_engine.connect() as conn:
        result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"))
        exists = result.scalar() is not None

        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            print(f"Database '{db_name}' created.")
        else:
            print(f"Database '{db_name}' already exists.")
            
            
# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    create_database(DATABASE_URL_BASE, DB_NAME)
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)