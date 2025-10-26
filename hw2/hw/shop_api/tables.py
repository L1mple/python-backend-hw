from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import JSON, Boolean, Column, Float, Integer, String

# Replace with your actual MySQL credentials
DATABASE_URL = "postgresql+asyncpg://admin:admin@db:5432/production"

engine = create_async_engine(DATABASE_URL)
Base = declarative_base()

AsyncSessionLocal = async_sessionmaker(engine)


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255))
    price = Column(Float)
    deleted = Column(Boolean, default=False)


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    items = Column(JSON)
