
from __future__ import annotations
from typing import List, Iterable
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Item, Cart, CartItem
from .db import SessionLocal
from .db_models import ItemORM, CartORM, CartItemORM


def with_session(func):
    def wrapper(*args, **kwargs):
        session: Session | None = kwargs.get("session")
        created = False
        if session is None:
            session = SessionLocal()
            kwargs["session"] = session
            created = True
        try:
            result = func(*args, **kwargs)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            if created:
                session.close()
    return wrapper


@with_session
def get_item_or_404(item_id: int, *, session: Session | None = None) -> Item:
    orm = session.get(ItemORM, item_id)
    if not orm or orm.deleted:
        raise HTTPException(status_code=404, detail="item not found")
    return Item(id=orm.id, name=orm.name, price=float(orm.price), deleted=orm.deleted)


@with_session
def get_item_raw(item_id: int, *, session: Session | None = None) -> ItemORM | None:
    return session.get(ItemORM, item_id)


@with_session
def save_item(item: Item, *, session: Session | None = None) -> None:
    if item.id:
        orm = session.get(ItemORM, item.id)
        if not orm:
            orm = ItemORM(id=item.id, name=item.name, price=item.price,
                          deleted=getattr(item, "deleted", False))
            session.add(orm)
        else:
            orm.name = item.name
            orm.price = item.price
            orm.deleted = getattr(item, "deleted", orm.deleted)
    else:
        orm = ItemORM(name=item.name, price=item.price,
                      deleted=getattr(item, "deleted", False))
        session.add(orm)


@with_session
def all_items(show_deleted: bool, *, session: Session | None = None) -> List[Item]:
    stmt = select(ItemORM)
    if not show_deleted:
        stmt = stmt.where(ItemORM.deleted.is_(False))
    rows: Iterable[ItemORM] = session.scalars(stmt)
    return [Item(id=r.id, name=r.name, price=float(r.price), deleted=r.deleted) for r in rows]


@with_session
def create_cart(*, session: Session | None = None) -> int:
    cart = CartORM()
    session.add(cart)
    session.flush()
    return cart.id


def _ensure_cart_orm(cart_id: int, session: Session) -> CartORM:
    cart = session.get(CartORM, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="cart not found")
    return cart


@with_session
def ensure_cart(cart_id: int, *, session: Session | None = None) -> None:
    _ensure_cart_orm(cart_id, session)


@with_session
def add_to_cart(cart_id: int, item_id: int, count: int = 1, *, session: Session | None = None) -> None:
    cart = _ensure_cart_orm(cart_id, session)
    item = session.get(ItemORM, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    qty = max(1, int(count))

    stmt = select(CartItemORM).where(
        CartItemORM.cart_id == cart.id,
        CartItemORM.item_id == item.id,
    )
    rel = session.scalars(stmt).first()
    if rel:
        rel.quantity += qty
    else:
        rel = CartItemORM(cart_id=cart.id, item_id=item.id, quantity=qty)
        session.add(rel)


@with_session
def cart_view(cart_id: int, *, session: Session | None = None) -> Cart:
    cart = _ensure_cart_orm(cart_id, session)

    stmt = select(CartItemORM).where(CartItemORM.cart_id == cart.id)
    rels: list[CartItemORM] = list(session.scalars(stmt))

    items: list[CartItem] = []
    total = 0.0

    for rel in rels:
        item = session.get(ItemORM, rel.item_id)
        available = bool(item and not item.deleted)
        name = item.name if item else f"item#{rel.item_id}"
        price = float(item.price) if item else 0.0
        if available:
            total += price * rel.quantity
        items.append(CartItem(id=rel.item_id, name=name,
                     quantity=rel.quantity, available=available))

    return Cart(id=cart.id, items=items, price=total)


@with_session
def all_carts(*, session: Session | None = None) -> List[int]:
    rows = session.scalars(select(CartORM.id).order_by(CartORM.id))
    return list(rows)


@with_session
def create_item(name: str, price: float, *, session=None) -> Item:
    orm = ItemORM(name=name, price=price, deleted=False)
    session.add(orm)
    session.flush()  
    return Item(id=orm.id, name=orm.name, price=float(orm.price), deleted=orm.deleted)
