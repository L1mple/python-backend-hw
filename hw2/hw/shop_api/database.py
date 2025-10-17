import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator


# Получание URL БД из переменной окружения
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:admin@localhost:5432/shop_db"
)

# Создание async engine для подключения к БД
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # выводит SQL запросы в консоль
    future=True  # включает асинхронность
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # объекты остаются доступными после commit
)


# Базовый класс для всех моделей
class Base(DeclarativeBase):
    pass


# Dependency для получения сессии БД в роутах FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Создание всех таблиц
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Удаление всех таблиц
async def drop_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
