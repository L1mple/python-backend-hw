import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:pass@db:5432/shopdb"
)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)

DDL = """
CREATE TABLE IF NOT EXISTS test_items (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
"""


SELECT_ONE = "SELECT * FROM test_items WHERE id = 1;"
UPDATE_TO_PENCIL = "UPDATE test_items SET name = 'pencil' WHERE id = 1;"

async def setup():
    async with engine.begin() as conn:
        await conn.execute(text(DDL))
        await conn.execute(text("TRUNCATE test_items"))
        await conn.execute(
            text("INSERT INTO test_items (id, name) VALUES (:id, 'pen')"),
            {"id": 1},
        )
