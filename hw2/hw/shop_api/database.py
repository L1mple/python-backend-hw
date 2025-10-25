import os

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
    sessionmaker,
)

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://shop_user:shop_pass@localhost:5432/shop_db',
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    cart_items: Mapped[list['CartItem']] = relationship(
        back_populates='item', cascade='all, delete-orphan'
    )


class Cart(Base):
    __tablename__ = 'carts'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)

    items: Mapped[list['CartItem']] = relationship(
        back_populates='cart', cascade='all, delete-orphan'
    )


class CartItem(Base):
    __tablename__ = 'cart_items'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey('carts.id', ondelete='CASCADE'))
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id', ondelete='CASCADE'))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    cart: Mapped['Cart'] = relationship(back_populates='items')
    item: Mapped['Item'] = relationship(back_populates='cart_items')


Base.metadata.create_all(bind=engine)
