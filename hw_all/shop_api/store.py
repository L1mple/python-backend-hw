from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from .db_models import Item, Cart, CartItem


def add_item(db: Session, orm_item: Item) -> Item:
    db.add(orm_item)
    db.commit()
    db.refresh(orm_item)
    return orm_item


def delete_item(db: Session, id: int) -> None:
    orm_item = get_item(db, id)
    if orm_item is not None:
        orm_item.deleted = True
        db.commit()


def get_item(db: Session, id: int) -> Item | None:
    return db.query(Item).filter(Item.id == id, Item.deleted.is_(False)).first()


def get_item_including_deleted(db: Session, id: int) -> Item | None:
    return db.query(Item).filter(Item.id == id).first()


def get_items(
    db: Session,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> Iterable[Item]:
    query = db.query(Item)
    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    if max_price is not None:
        query = query.filter(Item.price <= max_price)
    if not show_deleted:
        query = query.filter(Item.deleted.is_(False))
    return query.offset(offset).limit(limit).all()


def update_item(
    db: Session, id: int, name: str, price: float, deleted: bool
) -> Item | None:
    orm_item = get_item_including_deleted(db, id)
    if orm_item is None:
        return None
    orm_item.name = name
    orm_item.price = price
    orm_item.deleted = deleted
    db.commit()
    db.refresh(orm_item)
    return orm_item


def patch_item(
    db: Session, id: int, name: str | None, price: float | None
) -> Item | None:
    orm_item = get_item(db, id)
    if orm_item is None:
        return None
    if name is not None:
        orm_item.name = name
    if price is not None:
        orm_item.price = price
    db.commit()
    db.refresh(orm_item)
    return orm_item


def get_carts(
    db: Session,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> Iterable[Cart]:
    query = db.query(Cart)
    cart_stats_subquery = (
        db.query(
            CartItem.cart_id,
            func.sum(CartItem.quantity * Item.price).label("total_price"),
            func.sum(CartItem.quantity).label("total_quantity"),
        )
        .join(Item, CartItem.item_id == Item.id)
        .group_by(CartItem.cart_id)
        .subquery()
    )
    query = query.join(cart_stats_subquery, Cart.id == cart_stats_subquery.c.cart_id)
    if min_price is not None:
        query = query.filter(cart_stats_subquery.c.total_price >= min_price)
    if max_price is not None:
        query = query.filter(cart_stats_subquery.c.total_price <= max_price)
    if min_quantity is not None:
        query = query.filter(cart_stats_subquery.c.total_quantity >= min_quantity)
    if max_quantity is not None:
        query = query.filter(cart_stats_subquery.c.total_quantity <= max_quantity)
    carts = query.order_by(Cart.id).offset(offset).limit(limit).all()
    return carts


def get_cart(db: Session, id: int) -> Cart | None:
    return db.query(Cart).filter(Cart.id == id).first()


def add_cart(db: Session) -> Cart:
    orm_cart = Cart()
    db.add(orm_cart)
    db.commit()
    db.refresh(orm_cart)
    return orm_cart


def add_item_to_cart(db: Session, cart: Cart, item: Item) -> Cart:
    existing_cart_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.item_id == item.id)
        .first()
    )
    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        db.add(CartItem(cart_id=cart.id, item_id=item.id, quantity=1))
    db.commit()
    db.refresh(cart)
    return cart
