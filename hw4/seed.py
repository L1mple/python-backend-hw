import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.sql import text
from faker import Faker
from shop_api.models import Base, Item, Cart, CartItem

DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/shop_db" 

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
faker = Faker()

async def seed_data():
    async with async_session() as session:
        # Очистка таблиц
        await session.execute(text("DELETE FROM cart_items;"))
        await session.execute(text("DELETE FROM carts;"))
        await session.execute(text("DELETE FROM items;"))
        await session.commit()

        # Создание тестовых товаров (50 шт.)
        items = [
            Item(name=faker.word().capitalize(), price=round(faker.random.uniform(10.0, 1000.0), 2))
            for _ in range(50)
        ]
        session.add_all(items)
        await session.commit()

        # Создание тестовых корзин (20 шт.)
        carts = [Cart() for _ in range(20)]
        session.add_all(carts)
        await session.commit()

        # Добавление товаров в корзины (100 связей)
        cart_items = [
            CartItem(
                cart_id=faker.random.choice(carts).id,
                item_id=faker.random.choice(items).id,
                quantity=faker.random.randint(1, 5)
            )
            for _ in range(100)
        ]
        session.add_all(cart_items)
        await session.commit()

        print(f"Данные успешно добавлены в БД: {len(items)} товаров, {len(carts)} корзин, {len(cart_items)} связей")

if __name__ == "__main__":
    asyncio.run(seed_data())
