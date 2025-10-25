from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Numeric, Boolean, DateTime, ForeignKey, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"), nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=text("now()"), nullable=False)

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

class CartItem(Base):
    __tablename__ = "cart_items"
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="cascade"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="restrict"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    cart: Mapped[Cart] = relationship(back_populates="items")
    item: Mapped[Item] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("cart_id", "item_id", name="uq_cart_item"),
    )
