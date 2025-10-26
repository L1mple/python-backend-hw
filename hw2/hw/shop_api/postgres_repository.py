import os
from typing import List, Optional

from sqlalchemy import create_engine, Engine, ForeignKey, select, String
from sqlalchemy.orm import DeclarativeBase, joinedload, Mapped, mapped_column, Session, relationship

from shop_api import models

class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    price: Mapped[float] = mapped_column(default=0)
    deleted: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, name={self.name!r}, price={self.price!r}, deleted={self.deleted!r})"
    

class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    item: Mapped["Item"] = relationship()
    quantity: Mapped[int]
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    cart: Mapped["Cart"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"CartItem(id={self.id!r}, item_id={self.item_id!r}, quantity={self.quantity!r})"
    

class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    items: Mapped[List["CartItem"]] = relationship(back_populates="cart")
    price: Mapped[float]

    def __repr__(self) -> str:
        return f"Cart(id={self.id!r}, items=[{', '.join([f'{item.id!r}' for item in self.items])}], quanpricetity={self.price!r})"


def ItemToModel(item: Item) -> models.Item:
    return models.Item(
        id=item.id,
        name=item.name,
        price=item.price,
        deleted=item.deleted
    )


def CartItemToModel(cart_item: CartItem) -> models.CartItem:
    return models.CartItem(
        id=cart_item.item.id,
        name=cart_item.item.name,
        quantity=cart_item.quantity,
        available=not cart_item.item.deleted
    )


def CartToModel(cart: Cart) -> models.Cart:
    return models.Cart(
        id=cart.id,
        items=[CartItemToModel(cart_item) for cart_item in cart.items],
        price=cart.price
    )


class Repository:
    engine: Engine

    def __init__(self):
        postgres_user = os.environ['POSTGRES_USER']
        postgres_password = os.environ['POSTGRES_PASSWORD']
        postgres_address = os.environ['POSTGRES_ADDRESS']
        postgres_port = os.environ['POSTGRES_PORT']
        self.engine = create_engine(f'postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_address}:{postgres_port}/shop_api')
        Base.metadata.create_all(self.engine)

    def create_cart(self) -> models.Cart:
        with Session(self.engine) as session:
            cart = Cart(items=[], price=0.0)
            session.add(cart)
            session.commit()

            return CartToModel(cart)
    
    def get_cart(self, cart_id: int) -> models.Cart:
        with Session(self.engine) as session:
            stmt = select(Cart).options(joinedload(Cart.items)).where(Cart.id == cart_id)
            cart = session.scalar(stmt)

            if cart is None:
                raise models.CartNotFoundException()
            return CartToModel(cart)
    
    def get_carts(self, offset: int, limit: int) -> List[models.Cart]:
        with Session(self.engine) as session:
            stmt = select(Cart).options(joinedload(Cart.items)).where(Cart.id > offset).limit(limit)
            carts = session.scalars(stmt).unique()

            return [CartToModel(cart) for cart in carts]
    
    def add_item_to_cart(self, cart_id: int, item_id: int):
        with Session(self.engine) as session:
            stmt = (
                select(CartItem).options(joinedload(CartItem.cart), joinedload(CartItem.item))
                    .where(CartItem.cart_id == cart_id)
                    .where(CartItem.item_id == item_id)
            )
            cart_item = session.scalar(stmt)
            if cart_item is not None:
                cart_item.quantity += 1
                cart_item.cart.price += cart_item.item.price
                session.commit()
                return

            stmt = select(Cart).where(Cart.id == cart_id)
            cart = session.scalar(stmt)
            if cart is None:
                raise models.CartNotFoundException()
            
            stmt = select(Item).where(Item.id == item_id)
            item = session.scalar(stmt)
            if item is None:
                raise models.ItemNotFoundException()
            
            cart.items.append(CartItem(item_id=item_id, quantity=1, cart_id=cart_id))
            cart.price += item.price
            session.commit()

    def create_item(self, name: str, price: float) -> models.Item:
        with Session(self.engine) as session:
            item = Item(name=name, price=price)
            session.add(item)
            session.commit()

            return ItemToModel(item)
        
    def _get_item(self, item_id: int, session: Session) -> Item:
        stmt = select(Item).where(Item.id == item_id)
        item = session.scalar(stmt)

        if item is None:
            raise models.ItemNotFoundException()
        return item
    
    def get_item(self, item_id: int) -> models.Item:
        with Session(self.engine) as session:
            item: Item = self._get_item(item_id, session)
            if item.deleted:
                raise models.ItemNotFoundException()
            return ItemToModel(item)

    def get_items(self, offset: int, limit: int) -> List[models.Item]:
        with Session(self.engine) as session:
            stmt = select(Item).where(Item.id > offset).where(not Item.deleted).limit(limit)
            items = session.scalars(stmt)

            return [ItemToModel(item) for item in items]
    
    def replace_item(self, item_id: int, name: str, price: float) -> models.Item:
        with Session(self.engine) as session:
            item: Item = self._get_item(item_id, session)
            
            item.name = name
            item.price = price
            item.deleted = False

            session.commit()
            return ItemToModel(item)

    
    def update_item(self, item_id: int, name: Optional[str], price: Optional[float]) -> Optional[Item]:
        with Session(self.engine) as session:
            item: Item = self._get_item(item_id, session)
            if item.deleted:
                return
            
            if name is not None:
                item.name = name
            if price is not None:
                item.price = price

            session.commit()
            return ItemToModel(item)
    
    def delete_item(self, item_id: int):
        with Session(self.engine) as session:
            item: Item = self._get_item(item_id, session)
            if not item.deleted:
                item.deleted = True
                session.commit()
