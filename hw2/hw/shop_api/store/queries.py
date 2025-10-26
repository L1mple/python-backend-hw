from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from store.db_models import Cart as CartRecord, CartItem as CartItemRecord, Item as ItemRecord
from store.models import Cart, CartItem, Item


def create_cart_record(session: Session) -> Cart:
    cart_record = CartRecord()
    session.add(cart_record)
    session.flush()
    session.refresh(
        cart_record,
        attribute_names=["id"],
    )
    return _serialize_cart(cart_record)


def _cart_items_and_price(cart_record: CartRecord) -> tuple[list[CartItem], float]:
    items: list[CartItem] = []
    total_price = 0.0
    for cart_item in cart_record.items:
        if cart_item.item is None:
            continue
        serialized = CartItem(
            id=cart_item.item_id,
            name=cart_item.item.name,
            quantity=cart_item.quantity,
            available=not cart_item.item.deleted,
        )
        items.append(serialized)
        total_price += cart_item.quantity * cart_item.item.price
    return items, float(total_price)


def _serialize_cart(cart_record: CartRecord) -> Cart:
    items, price = _cart_items_and_price(cart_record)
    return Cart(id=cart_record.id, items=items, price=price)


def _cart_with_items_query():
    return select(CartRecord).options(
        selectinload(CartRecord.items).joinedload(CartItemRecord.item)
    )


def list_carts(
    session: Session,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> list[Cart]:
    stmt = (
        _cart_with_items_query()
        .order_by(CartRecord.id)
        .offset(offset)
        .limit(limit)
    )
    cart_records = session.scalars(stmt).all()

    results: list[Cart] = []
    for record in cart_records:
        items, price = _cart_items_and_price(record)
        item_count = len(record.items)
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        if min_quantity is not None and item_count < min_quantity:
            continue
        if max_quantity is not None and item_count > max_quantity:
            continue
        results.append(Cart(id=record.id, items=items, price=price))
    return results


def get_cart(session: Session, cart_id: int) -> Cart | None:
    cart_record = session.get(
        CartRecord,
        cart_id,
        options=[
            selectinload(CartRecord.items).joinedload(CartItemRecord.item),
        ],
    )
    if cart_record is None:
        return None
    return _serialize_cart(cart_record)


def list_items(
    session: Session,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> list[Item]:
    stmt = (
        select(ItemRecord)
        .order_by(ItemRecord.id)
        .offset(offset)
        .limit(limit)
    )
    if min_price is not None:
        stmt = stmt.where(ItemRecord.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(ItemRecord.price <= max_price)
    if not show_deleted:
        stmt = stmt.where(ItemRecord.deleted.is_(False))
    items = session.scalars(stmt).all()
    return [Item.model_validate(item) for item in items]


def get_item(
    session: Session,
    item_id: int,
    *,
    include_deleted: bool = False,
) -> Item | None:
    item_record = session.get(ItemRecord, item_id)
    if item_record is None:
        return None
    if item_record.deleted and not include_deleted:
        return None
    return Item.model_validate(item_record)


def create_item_record(session: Session, name: str, price: float) -> Item:
    item_record = ItemRecord(name=name, price=price, deleted=False)
    session.add(item_record)
    session.flush()
    return Item.model_validate(item_record)


def replace_item_record(session: Session, item_id: int, name: str, price: float) -> Item | None:
    item_record = session.get(ItemRecord, item_id)
    if item_record is None:
        return None
    item_record.name = name
    item_record.price = price
    item_record.deleted = False
    session.flush()
    return Item.model_validate(item_record)


def patch_item_record(
    session: Session,
    item_id: int,
    name: str | None,
    price: float | None,
) -> Item | None:
    item_record = session.get(ItemRecord, item_id)
    if item_record is None or item_record.deleted:
        return None
    if name is not None:
        item_record.name = name
    if price is not None:
        item_record.price = price
    session.flush()
    return Item.model_validate(item_record)


def delete_item(session: Session, item_id: int) -> None:
    item_record = session.get(ItemRecord, item_id)
    if item_record is not None:
        item_record.deleted = True
        session.flush()


def add_cart_item(session: Session, cart_id: int, item_id: int) -> Cart | None:
    cart_record = session.get(CartRecord, cart_id)
    if cart_record is None:
        return None

    item_record = session.get(ItemRecord, item_id)
    if item_record is None or item_record.deleted:
        return None

    cart_item = session.get(CartItemRecord, (cart_id, item_id))
    if cart_item is None:
        cart_item = CartItemRecord(cart_id=cart_id, item_id=item_id, quantity=1)
        session.add(cart_item)
    else:
        cart_item.quantity += 1
    session.flush()
    return get_cart(session, cart_id)


def compute_store_statistics(session: Session) -> dict[str, float]:
    cart_count = session.scalar(select(func.count(CartRecord.id))) or 0
    item_count = session.scalar(select(func.count(ItemRecord.id))) or 0
    deleted_items = session.scalar(
        select(func.count(ItemRecord.id)).where(ItemRecord.deleted.is_(True))
    ) or 0

    total_price = session.scalar(
        select(func.coalesce(func.sum(ItemRecord.price), 0.0))
    ) or 0.0
    total_active_price = session.scalar(
        select(func.coalesce(func.sum(ItemRecord.price), 0.0)).where(ItemRecord.deleted.is_(False))
    ) or 0.0
    active_items = item_count - deleted_items

    total_cart_items = session.scalar(
        select(func.count(CartItemRecord.cart_id))
    ) or 0

    return {
        "cart_count": float(cart_count),
        "item_count": float(item_count),
        "deleted_item_count": float(deleted_items),
        "average_item_price": float(total_price / item_count) if item_count else 0.0,
        "average_active_item_price": float(total_active_price / active_items) if active_items else 0.0,
        "average_items_per_cart": float(total_cart_items / cart_count) if cart_count else 0.0,
    }
