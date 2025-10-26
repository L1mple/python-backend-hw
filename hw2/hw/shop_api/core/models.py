from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from shop_api.core.database import Base

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

    cart_items = relationship("CartItemDB", back_populates="item")

class CartDB(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True)

    items = relationship("CartItemDB", back_populates="cart", cascade="all, delete")

class CartItemDB(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"))
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"))
    quantity = Column(Integer, nullable=False, default=1)

    cart = relationship("CartDB", back_populates="items")
    item = relationship("ItemDB", back_populates="cart_items")