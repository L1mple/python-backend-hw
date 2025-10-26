from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ItemDB(Base):
    """Database model for items"""
    __tablename__ = "items"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)


class CartDB(Base):
    """Database model for carts"""
    __tablename__ = "carts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=False)
    price = Column(Float, default=0.0)

    # Relationship to cart items
    cart_items = relationship("CartItemDB", back_populates="cart", cascade="all, delete-orphan")


class CartItemDB(Base):
    """Database model for items in cart (association table with extra data)"""
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cart_id = Column(BigInteger, ForeignKey('carts.id'), nullable=False)
    item_id = Column(BigInteger, ForeignKey('items.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    # Relationships
    cart = relationship("CartDB", back_populates="cart_items")
    item = relationship("ItemDB")


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
