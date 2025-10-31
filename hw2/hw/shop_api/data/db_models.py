from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List

try:
    from ..database import Base
except ImportError:
    # Для Alembic миграций используем абсолютный импорт
    from database import Base


# Таблица связи many-to-many между корзинами и товарами
cart_items_table = Table(
    "cart_items",
    Base.metadata,
    Column(
        "cart_id", Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("quantity", Integer, nullable=False, default=1),
)


class ItemDB(Base):
    """Model of an item in the database"""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связь с корзинами (через промежуточную таблицу)
    carts: Mapped[List["CartDB"]] = relationship(
        "CartDB", secondary=cart_items_table, back_populates="items"
    )

    def __repr__(self):
        return f"<ItemDB(id={self.id}, name={self.name}, price={self.price}, deleted={self.deleted})>"


class CartDB(Base):
    """Model of a cart in the database"""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Связь с товарами (через промежуточную таблицу)
    items: Mapped[List["ItemDB"]] = relationship(
        "ItemDB", secondary=cart_items_table, back_populates="carts"
    )

    def __repr__(self):
        return f"<CartDB(id={self.id}, price={self.price})>"
