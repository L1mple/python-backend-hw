from sqlalchemy import Column, Integer, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from shop_api.db import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    name = Column(String(255))
    quantity = Column(Integer, default=1)
    available = Column(Boolean, default=True)

    cart = relationship("Cart", back_populates="items")
    item = relationship("Item", back_populates="cart_items")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float, default=0.0)

    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )
