from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, Sequence,
                        String)
from sqlalchemy.orm import DeclarativeBase, relationship

id_generator_cart = Sequence('id_cart_seq', start=1, increment=1)
id_generator_item = Sequence('id_item_seq', start=1, increment=1)

class Base(DeclarativeBase):
    pass

class Carts(Base):
    __tablename__ = "carts"
    id = Column(Integer, autoincrement=True, primary_key=True)

    carts_items = relationship("CartsItems", back_populates="cart")

class Items(Base):
    __tablename__ = "items"
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    carts_items = relationship("CartsItems", back_populates="item")

class CartsItems(Base):
    __tablename__ = "carts_items"

    cart_id = Column(Integer, ForeignKey("carts.id"), primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)

    cart = relationship("Carts", back_populates="carts_items")
    item = relationship("Items", back_populates="carts_items")
