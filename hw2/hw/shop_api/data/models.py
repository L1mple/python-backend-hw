from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class ItemOrm(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

    cart_items = relationship(
        "CartItemOrm",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

class CartOrm(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)

    cart_items = relationship(
        "CartItemOrm",
        back_populates="cart",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )

class CartItemOrm(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)

    cart = relationship("CartOrm", back_populates="cart_items")
    item = relationship("ItemOrm", back_populates="cart_items", lazy="joined")

    __table_args__ = (
        UniqueConstraint("cart_id", "item_id", name="uq_cart_item"),
    )
