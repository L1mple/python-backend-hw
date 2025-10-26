from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from shop_api.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    deleted = Column(Boolean, default=False, index=True)

    cart_items = relationship("CartItem", back_populates="item")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    @property
    def total_price(self):
        if not self.items:
            return 0.0
        return sum(
            ci.item.price * ci.quantity for ci in self.items if not ci.item.deleted
        )


class CartItem(Base):
    __tablename__ = "cart_items"

    cart_id = Column(Integer, ForeignKey("carts.id"), primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), primary_key=True)
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", back_populates="items")
    item = relationship("Item", back_populates="cart_items")
