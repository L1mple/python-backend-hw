from typing import List
from uuid import UUID as UUID_PY, uuid4
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[UUID_PY] = mapped_column(UUID_PG(as_uuid=True), primary_key=True, default=lambda: uuid4().hex)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float)
    deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[UUID_PY] = mapped_column(
        UUID_PG(as_uuid=True),
        primary_key=True,
        default=lambda: uuid4().hex
    )

    items: Mapped[List["CartItemModel"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class CartItemModel(Base):
    __tablename__ = "cart_items"

    cart_id: Mapped[UUID_PY] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"),
        primary_key=True
    )
    item_id: Mapped[UUID_PY] = mapped_column(
        ForeignKey("items.id"),
        primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cart: Mapped["CartModel"] = relationship(back_populates="items")
    item: Mapped["ItemModel"] = relationship(lazy="joined")
    available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )