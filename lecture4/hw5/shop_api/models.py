from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from sqlalchemy import Boolean, Numeric, ForeignKey, UniqueConstraint

from .db import Base

class Item(Base):
    __tablename__="items"
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str]=mapped_column(String(255), nullable=False)
    price: Mapped[float]=mapped_column(Numeric(12,2), nullable=False)
    deleted: Mapped[bool]=mapped_column(Boolean, nullable=False, default=False)

class Cart(Base):
    __tablename__="carts"
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)

class CartItem(Base):
    __tablename__="cart_items"
    cart_id: Mapped[int]=mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    item_id: Mapped[int]=mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True)
    quantity: Mapped[int]=mapped_column(Integer, nullable=False, default=0)
    __table_args__=(UniqueConstraint("cart_id","item_id",name="uq_cart_item"),)