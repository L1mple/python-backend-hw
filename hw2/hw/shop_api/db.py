# shop_api/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Берём URL из переменной окружения, в docker-compose он вида:
# postgresql+psycopg://shop:shop@postgres:5432/shop
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://shop:shop@localhost:5432/shop",  # fallback для локального запуска
)

# <<< ЭТИ ОБЪЕКТЫ ДОЛЖНЫ СУЩЕСТВОВАТЬ НА ВЕРХНЕМ УРОВНЕ МОДУЛЯ >>>
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

# Зависимость для FastAPI
def get_db():
    from sqlalchemy.orm import Session
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
