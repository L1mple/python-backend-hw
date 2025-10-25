from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class CartDB(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("CartItemDB", back_populates="cart")

class CartItemDB(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Integer, default=1)
    cart = relationship("CartDB", back_populates="items")
    item = relationship("ItemDB")

from dataclasses import dataclass

@dataclass(slots=True)
class CartItemInfo:
    id: int
    name: str
    quantity: int
    available: bool

@dataclass(slots=True)
class CartInfo:
    items: list[CartItemInfo]
    price: float

@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo