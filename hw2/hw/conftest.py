import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from shop_api.main import app
from shop_api.database import get_db

# Get DATABASE_URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:admin@localhost:5432/shop_db"
)

# Create a test engine with NullPool to avoid connection reuse across event loops
test_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    poolclass=NullPool,  # Don't pool connections - create new ones each time
)

# Create test session factory
TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Override the default get_db dependency
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency to use NullPool for tests."""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Apply the override globally for all tests
app.dependency_overrides[get_db] = override_get_db
