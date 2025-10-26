from sqlalchemy import Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from .database import Base


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    cart_items: Mapped[List["CartItemModel"]] = relationship("CartItemModel", back_populates="cart", cascade="all, delete-orphan")


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="cart_items")
    item: Mapped["ItemModel"] = relationship("ItemModel")


