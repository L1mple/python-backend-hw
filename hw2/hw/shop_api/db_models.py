from __future__ import annotations
from sqlalchemy import Boolean, ForeignKey, Integer, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ItemORM(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)


class CartORM(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    items: Mapped[list["CartItemORM"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItemORM(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "item_id", name="uq_cart_item"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    cart: Mapped["CartORM"] = relationship(back_populates="items")
