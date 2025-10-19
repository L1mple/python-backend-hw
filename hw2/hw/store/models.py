from dataclasses import (
    dataclass,
    field,
)
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import Session, relationship, declarative_base


# === domain data ===

@dataclass(slots=True)
class CartItem:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class Cart:
    id: int
    price: float
    items: list[CartItem] = field(default_factory=list)


@dataclass(slots=True)
class Item:
    id: int
    name: str
    price: float
    deleted: bool


# === SQL Alchemy models ===

Base = declarative_base()


class CartOrm(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True)
    price = Column(Float, nullable=False)
    items = relationship("CartItemOrm", back_populates="cart", cascade="all, delete-orphan")


class CartItemOrm(Base):
    __tablename__ = 'cart_item'

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('cart.id'), nullable=False)
    item_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    available = Column(Boolean, nullable=False)

    cart = relationship("CartOrm", back_populates="items")


class ItemOrm(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, nullable=False)


# === Mappers ===

class CartMapper:
    @staticmethod
    def to_domain(orm_cart: CartOrm):
        if orm_cart is None:
            return None
        items: list[CartItem] = []
        for orm_item in getattr(orm_cart, "items", []) or []:
            items.append(CartItemMapper.to_domain(orm_item))
        return Cart(
            id=orm_cart.id,
            price=orm_cart.price,
            items=items,
        )

    @staticmethod
    def to_orm(
            domain_cart: Cart,
            orm_cart: CartOrm,
    ):
        if orm_cart is None:
            orm_cart = CartOrm()

        orm_cart.id = domain_cart.id
        orm_cart.price = domain_cart.price

        new_items: list[CartItemOrm] = []
        for domain_item in domain_cart.items:
            orm_item = CartItemMapper.to_orm(domain_item, None)
            orm_item.cart_id = domain_cart.id
            new_items.append(orm_item)
        orm_cart.items = new_items

        return orm_cart


class CartItemMapper:
    @staticmethod
    def to_domain(orm_cart_item: CartItemOrm) -> CartItem:
        return CartItem(
            id=getattr(orm_cart_item, "item_id", orm_cart_item.id),
            name=orm_cart_item.name,
            quantity=orm_cart_item.quantity,
            available=orm_cart_item.available,
        )

    @staticmethod
    def to_orm(
            domain_cart_item: CartItem,
            orm_cart_item: CartItemOrm,
    ) -> CartItemOrm:
        if orm_cart_item is None:
            orm_cart_item = CartItemOrm()

        # domain `item_id` is `id` in cart context
        orm_cart_item.item_id = domain_cart_item.id
        orm_cart_item.name = domain_cart_item.name
        orm_cart_item.quantity = domain_cart_item.quantity
        orm_cart_item.available = domain_cart_item.available

        return orm_cart_item


class ItemMapper:
    @staticmethod
    def to_domain(orm_item: ItemOrm) -> Item:
        return Item(
            id=orm_item.id,
            name=orm_item.name,
            price=orm_item.price,
            deleted=orm_item.deleted,
        )

    @staticmethod
    def to_orm(
            domain_item: Item,
            orm_item: ItemOrm,
    ) -> ItemOrm:
        if orm_item is None:
            orm_item = ItemOrm()

        orm_item.id = domain_item.id
        orm_item.name = domain_item.name
        orm_item.price = domain_item.price
        orm_item.deleted = domain_item.deleted

        return orm_item


class SqlAlchemyCartRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def post_cart(self) -> int:
        orm = CartOrm(price=0.0)
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return orm.id

    def _map_cart(self, orm_cart: CartOrm) -> Cart | None:
        if orm_cart is None:
            return None
        cart = CartMapper.to_domain(orm_cart)
        # sync availability from ItemOrm.deleted
        for ci in cart.items:
            item = self.session.get(ItemOrm, ci.id)
            if item is not None:
                ci.available = not item.deleted
        return cart

    def get_cart(self, cart_id: int) -> Cart | None:
        orm = self.session.get(CartOrm, cart_id)
        return self._map_cart(orm)

    def get_carts_list(
            self,
            offset: int = 0,
            limit: int = 10,
            min_price: float | None = None,
            max_price: float | None = None,
            min_quantity: int | None = None,
            max_quantity: int | None = None,
    ) -> list[Cart]:
        assert offset >= 0
        assert limit > 0

        q = self.session.query(CartOrm)
        if min_price is not None:
            q = q.filter(CartOrm.price >= min_price)
        if max_price is not None:
            q = q.filter(CartOrm.price <= max_price)

        carts = [self._map_cart(orm) for orm in q.all()]

        def quantity(c: Cart) -> int:
            return sum(i.quantity for i in c.items)

        if min_quantity is not None:
            carts = [c for c in carts if quantity(c) >= min_quantity]
        if max_quantity is not None:
            carts = [c for c in carts if quantity(c) <= max_quantity]

        return carts[offset: offset + limit]

class SqlAlchemyCartItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_item_to_cart(self, cart_id: int, item_id: int) -> None:
        cart = self.session.get(CartOrm, cart_id)
        item = self.session.get(ItemOrm, item_id)
        if cart is None or item is None:
            return

        link = (
            self.session.query(CartItemOrm)
            .filter(CartItemOrm.cart_id == cart_id, CartItemOrm.item_id == item_id)
            .one_or_none()
        )

        if link is None:
            link = CartItemOrm(
                cart_id=cart_id,
                item_id=item_id,
                name=item.name,
                quantity=1,
                available=not item.deleted,
            )
            self.session.add(link)
        else:
            link.quantity += 1

        cart.price += item.price
        self.session.commit()

class SqlAlchemyItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def post_item(self, name: str, price: float, deleted: bool = False) -> int:
        orm = ItemOrm(name=name, price=price, deleted=deleted)
        self.session.add(orm)
        self.session.commit()
        self.session.refresh(orm)
        return orm.id

    def get_item(self, item_id: int) -> Item | None:
        orm = self.session.get(ItemOrm, item_id)
        if orm is None or orm.deleted:
            return None
        return ItemMapper.to_domain(orm)

    def get_items_list(
            self,
            offset: int = 0,
            limit: int = 10,
            min_price: float | None = None,
            max_price: float | None = None,
            show_deleted: bool = False,
    ) -> list[Item]:
        assert offset >= 0
        assert limit > 0

        q = self.session.query(ItemOrm)
        if not show_deleted:
            q = q.filter(ItemOrm.deleted.is_(False))
        if min_price is not None:
            q = q.filter(ItemOrm.price >= min_price)
        if max_price is not None:
            q = q.filter(ItemOrm.price <= max_price)

        q = q.offset(offset).limit(limit)
        return [ItemMapper.to_domain(orm) for orm in q.all()]

    def put_item(self, item_id: int, name: str, price: float) -> Item | None:
        orm = self.session.get(ItemOrm, item_id)
        if orm is None or orm.deleted:
            return None
        orm.name = name
        orm.price = price
        self.session.commit()
        self.session.refresh(orm)
        return ItemMapper.to_domain(orm)

    def patch_item(self, item_id: int, name: str | None = None, price: float | None = None) -> Item | None:
        orm = self.session.get(ItemOrm, item_id)
        if orm is None or orm.deleted:
            return None
        if name is not None:
            orm.name = name
        if price is not None:
            orm.price = price
        self.session.commit()
        self.session.refresh(orm)
        return ItemMapper.to_domain(orm)

    def delete_item(self, item_id: int) -> None:
        orm = self.session.get(ItemOrm, item_id)
        if orm is None:
            return
        orm.deleted = True
        self.session.commit()
