from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql+psycopg2://shop_user:shop_password@localhost:5432/shop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    deleted = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', price={self.price})>"