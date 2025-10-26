import os
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test.db"
)

@pytest.fixture(scope="session")
def engine():
    """Create engine - works for both SQLite and PostgreSQL"""
    return create_async_engine(DATABASE_URL)

@pytest_asyncio.fixture(scope="session")
async def async_session_maker(engine: AsyncEngine):
    """Create session factory and initialize database"""
    from shop_api.core.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield async_session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(autouse=True)
async def clean_db(async_session_maker):
    """Clean database before each test"""
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM cart_items"))
        await session.execute(text("DELETE FROM carts"))
        await session.execute(text("DELETE FROM items"))
        await session.commit()

async def set_isolation_level(session: AsyncSession, level: str):
    """Set isolation level for current transaction"""
    if 'sqlite' in str(session.bind.url):
        if level in ('SERIALIZABLE', 'REPEATABLE READ', 'READ COMMITTED'):
            await session.execute(text("PRAGMA read_uncommitted = 0"))
        elif level == 'READ UNCOMMITTED':
            await session.execute(text("PRAGMA read_uncommitted = 1"))
    else:
        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {level}"))

@pytest.mark.asyncio
async def test_dirty_read(async_session_maker):
    """Test dirty read phenomenon
    
    1. Session 1 starts transaction and updates data
    2. Session 2 tries to read the same data
    3. Should NOT see uncommitted changes in READ COMMITTED (default)
    """
    async with async_session_maker() as session:
        await session.execute(
            text("INSERT INTO items (name, price, deleted) VALUES ('test_item', 100, false)")
        )
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        await session1.begin()
        # Set isolation level for session1 if using PostgreSQL
        if 'postgresql' in str(session1.bind.url):
            await set_isolation_level(session1, "READ UNCOMMITTED")

        await session1.execute(
            text("UPDATE items SET price = 200 WHERE name = 'test_item'")
        )

        result = await session2.execute(
            text("SELECT price FROM items WHERE name = 'test_item'")
        )
        price = result.scalar()

        assert price == 100, "Should not see uncommitted changes (dirty read)"

        await session1.rollback()

@pytest.mark.asyncio
async def test_non_repeatable_read(async_session_maker):
    """Test non-repeatable read phenomenon
    
    1. Session 1 reads data
    2. Session 2 modifies and commits the same data
    3. Session 1 reads again and sees different results in READ COMMITTED
    """
    async with async_session_maker() as session:
        await session.execute(
            text("INSERT INTO items (name, price, deleted) VALUES ('test_item', 100, false)")
        )
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        await session1.begin()
        if 'postgresql' in str(session1.bind.url):
            await set_isolation_level(session1, "READ COMMITTED")

        result = await session1.execute(
            text("SELECT price FROM items WHERE name = 'test_item'")
        )
        price1 = result.scalar()
        assert price1 == 100

        await session2.execute(
            text("UPDATE items SET price = 200 WHERE name = 'test_item'")
        )
        await session2.commit()

        result = await session1.execute(
            text("SELECT price FROM items WHERE name = 'test_item'")
        )
        price2 = result.scalar()

        assert price2 == 200, "Should see committed changes (non-repeatable read)"
        await session1.commit()

@pytest.mark.asyncio
async def test_repeatable_read(async_session_maker):
    """Test prevention of non-repeatable read in REPEATABLE READ
    
    1. Session 1 reads data in REPEATABLE READ
    2. Session 2 modifies and commits the same data
    3. Session 1 reads again and should see the same results
    """
    if 'sqlite' in str(async_session_maker.kw['bind'].url):
        pytest.skip("SQLite doesn't support REPEATABLE READ")

    async with async_session_maker() as session:
        await session.execute(
            text("INSERT INTO items (name, price, deleted) VALUES ('test_item', 100, false)")
        )
        await session.commit()

    async with async_session_maker() as session1, async_session_maker() as session2:
        await session1.begin()
        await set_isolation_level(session1, "REPEATABLE READ")

        result = await session1.execute(
            text("SELECT price FROM items WHERE name = 'test_item'")
        )
        price1 = result.scalar()
        assert price1 == 100

        await session2.execute(
            text("UPDATE items SET price = 200 WHERE name = 'test_item'")
        )
        await session2.commit()

        result = await session1.execute(
            text("SELECT price FROM items WHERE name = 'test_item'")
        )
        price2 = result.scalar()

        assert price2 == 100, "Should not see changes in REPEATABLE READ"
        await session1.commit()

@pytest.mark.asyncio
async def test_phantom_read(async_session_maker):
    """Test phantom read phenomenon
    
    1. Session 1 queries a range of records
    2. Session 2 inserts a new record in that range
    3. Session 1 queries again and sees the new record in READ COMMITTED
    """
    async with async_session_maker() as session1, async_session_maker() as session2:
        await session1.begin()
        if 'postgresql' in str(session1.bind.url):
            await set_isolation_level(session1, "READ COMMITTED")

        result = await session1.execute(
            text("SELECT COUNT(*) FROM items WHERE price BETWEEN 50 AND 150")
        )
        count1 = result.scalar()

        await session2.execute(
            text("INSERT INTO items (name, price, deleted) VALUES ('phantom', 100, false)")
        )
        await session2.commit()

        result = await session1.execute(
            text("SELECT COUNT(*) FROM items WHERE price BETWEEN 50 AND 150")
        )
        count2 = result.scalar()

        assert count2 == count1 + 1, "Should see phantom record in READ COMMITTED"
        await session1.commit()

@pytest.mark.asyncio
async def test_serializable(async_session_maker):
    """Test serializable isolation level prevents phantom reads
    
    1. Session 1 queries a range of records in SERIALIZABLE
    2. Session 2 tries to insert a new record in that range
    3. Session 1 queries again and should not see changes
    """
    if 'sqlite' in str(async_session_maker.kw['bind'].url):
        pytest.skip("SQLite SERIALIZABLE behavior differs from PostgreSQL")

    async with async_session_maker() as session1, async_session_maker() as session2:
        await session1.begin()
        await set_isolation_level(session1, "SERIALIZABLE")

        result = await session1.execute(
            text("SELECT COUNT(*) FROM items WHERE price BETWEEN 50 AND 150")
        )
        count1 = result.scalar()

        await session2.execute(
            text("INSERT INTO items (name, price, deleted) VALUES ('phantom', 100, false)")
        )
        await session2.commit()

        result = await session1.execute(
            text("SELECT COUNT(*) FROM items WHERE price BETWEEN 50 AND 150")
        )
        count2 = result.scalar()

        assert count2 == count1, "Should not see phantom record in SERIALIZABLE"
        await session1.commit()