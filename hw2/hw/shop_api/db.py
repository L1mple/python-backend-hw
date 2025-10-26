from shop_api.orm_models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine("postgresql://postgres:password@localhost:5432/app")

SessionFactory = sessionmaker(engine)

Base.metadata.create_all(bind=engine, checkfirst=True)
def get_session() -> Session:
    with SessionFactory() as session:
        yield session
