from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.config import settings



db_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    max_overflow=0,
)

async_session = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=db_engine
)
