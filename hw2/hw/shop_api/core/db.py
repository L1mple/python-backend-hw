import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from shop_api.core.models import Base

# Convert DATABASE_URL to async version if needed
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get(
    "DATABASE_URL_LOCAL",
)

if not DATABASE_URL:
    # default to sqlite file for easy local runs/tests
    DATABASE_URL = "sqlite+aiosqlite:///./shop.db"
else:
    # Convert any PostgreSQL URL to use asyncpg
    # Remove any existing dialect (like +psycopg2) if present
    if DATABASE_URL.startswith('postgresql'):
        if '+' in DATABASE_URL:
            DATABASE_URL = DATABASE_URL.split('+')[0] + DATABASE_URL[DATABASE_URL.find('://'):]
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False, 
    autoflush=False
)

async def init_db() -> None:
    """Create database tables if they don't exist."""
    async with engine.begin() as conn:
        # Create tables without dropping existing ones
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
