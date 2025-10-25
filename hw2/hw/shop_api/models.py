from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from dao import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "deleted": bool(self.deleted),
        }


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True)

    def to_json(self):
        items = [ci.to_json() for ci in getattr(self, "cart_items", [])]
        price = sum((ci.get_total_price() if hasattr(ci, "get_total_price") else (ci.quantity * (ci.item.price or 0))) for ci in getattr(self, "cart_items", []))
        return {"id": self.id, "items": items, "price": price}


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", backref="cart_items")
    item = relationship("Item")

    def to_json(self):
        return {
            "id": self.id,
            "quantity": self.quantity,
            "item": self.item.to_json() if self.item is not None else None,
            "available": False if self.item is None else not bool(self.item.deleted),
            "price": None if self.item is None else self.item.price,
        }

    def get_total_price(self):
        return (self.item.price or 0) * (self.quantity or 0)
