import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://shop_user:shop_pass@localhost:5432/shop_db"
engine = create_async_engine(DATABASE_URL)


async def create_tables():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS carts (
                    id SERIAL PRIMARY KEY,
                    price FLOAT DEFAULT 0.0
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    price FLOAT NOT NULL,
                    deleted BOOLEAN DEFAULT FALSE
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cart_items (
                    id SERIAL PRIMARY KEY,
                    cart_id INTEGER REFERENCES carts(id) ON DELETE CASCADE,
                    item_id INTEGER REFERENCES items(id),
                    quantity INTEGER DEFAULT 1
                );
                """
            )
        )


async def seed_default():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO carts (price) VALUES (100.0)
                ON CONFLICT DO NOTHING;
                """
            )
        )

        await conn.execute(
            text(
                """
                INSERT INTO items (name, price, deleted)
                VALUES ('Item A', 10.0, FALSE),
                       ('Item B', 20.0, FALSE)
                ON CONFLICT DO NOTHING;
                """
            )
        )


async def prepare():
    await create_tables()
    await seed_default()


if __name__ == "__main__":
    asyncio.run(prepare())
    print("Done.")
