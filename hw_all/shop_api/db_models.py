from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

    cart_items = relationship("CartItem", back_populates="item")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )

    @property
    def price(self) -> float:
        return sum(cart_item.total_price for cart_item in self.items)


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    cart = relationship("Cart", back_populates="items")
    item = relationship("Item", back_populates="cart_items")

    @property
    def total_price(self) -> float:
        return self.item.price * self.quantity
