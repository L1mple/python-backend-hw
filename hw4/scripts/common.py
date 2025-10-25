from asyncio import run
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# для локального запуска (в docker нужно  изменить на @postgres)
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/shop_db"  

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)