from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, Boolean, Integer, ForeignKey
from typing import List

DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/hw4_db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    cart_items: Mapped[List["CartItemModel"]] = relationship(back_populates="item")

class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    cart_items: Mapped[List["CartItemModel"]] = relationship(back_populates="cart", cascade="all, delete-orphan")

class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    quantity: Mapped[int] = mapped_column(Integer)

    cart: Mapped["CartModel"] = relationship(back_populates="cart_items")
    item: Mapped["ItemModel"] = relationship(back_populates="cart_items")

async def get_session():
    async with async_session_maker() as session:
        yield session
