"""
Базовая настройка подключения к БД и модели для демонстрации проблем транзакций
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Numeric, text
from sqlalchemy.orm import declarative_base

# Подключение к PostgreSQL через asyncpg
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db")

# Создаём async engine
engine = create_async_engine(DATABASE_URL, echo=False)

Base = declarative_base()


class Account(Base):
    """Модель банковского счета для демонстрации"""
    __tablename__ = "demo_accounts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    balance = Column(Numeric(10, 2), nullable=False, default=0)
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', balance={self.balance})>"


async def init_database():
    """Создание таблиц и начальных данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        accounts = [
            Account(id=1, name="Alice", balance=1000.00),
            Account(id=2, name="Bob", balance=500.00),
            Account(id=3, name="Charlie", balance=750.00),
        ]
        
        session.add_all(accounts)
        await session.commit()


def get_async_session(isolation_level=None):
    """Получить async сессию с заданным уровнем изоляции"""
    if isolation_level:
        return AsyncSession(
            engine,
            expire_on_commit=False,
        )
    return AsyncSession(engine, expire_on_commit=False)


async def set_isolation_level(session: AsyncSession, level: str):
    """Установить уровень изоляции для сессии"""
    # В PostgreSQL уровни изоляции:
    # READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE
    await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {level}"))


if __name__ == "__main__":
    asyncio.run(init_database())
