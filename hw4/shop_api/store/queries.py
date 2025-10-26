from typing import List
from sqlalchemy.orm import Session, joinedload

import shop_api.store.models as db_models
from shop_api.api.item.contracts import ItemRequest, PatchItemRequest


def add_item(db: Session, info: ItemRequest) -> db_models.Item:
    db_item = db_models.Item(name=info.name, price=info.price, deleted=info.deleted)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: int) -> None:
    db_item = db.query(db_models.Item).filter(db_models.Item.id == item_id).first()
    if db_item:
        db_item.deleted = True
        db.commit()


def get_one_item(db: Session, item_id: int) -> db_models.Item | None:
    return db.query(db_models.Item).filter(
        db_models.Item.id == item_id,
        db_models.Item.deleted == False
    ).first()


def get_many_items(
        db: Session, offset: int, limit: int, min_price: float, max_price: float, show_deleted: bool
) -> List[db_models.Item]:
    query = db.query(db_models.Item)
    if not show_deleted:
        query = query.filter(db_models.Item.deleted == False)

    query = query.filter(db_models.Item.price >= min_price, db_models.Item.price <= max_price)

    return query.offset(offset).limit(limit).all()


def update_item(db: Session, item_id: int, info: ItemRequest) -> db_models.Item | None:
    db_item = db.query(db_models.Item).filter(db_models.Item.id == item_id).first()
    if db_item:
        db_item.name = info.name
        db_item.price = info.price
        db_item.deleted = info.deleted
        db.commit()
        db.refresh(db_item)
    return db_item


def patch_item(db: Session, item_id: int, patch_info: PatchItemRequest) -> db_models.Item | None:
    db_item = get_one_item(db, item_id)
    if db_item:
        if patch_info.name is not None:
            db_item.name = patch_info.name
        if patch_info.price is not None:
            db_item.price = patch_info.price
        db.commit()
        db.refresh(db_item)
    return db_item


def add_cart(db: Session) -> db_models.Cart:
    db_cart = db_models.Cart()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    return db_cart


def get_one_cart(db: Session, cart_id: int) -> db_models.Cart | None:
    return db.query(db_models.Cart).options(
        joinedload(db_models.Cart.items).joinedload(db_models.CartItem.item)
    ).filter(db_models.Cart.id == cart_id).first()


def get_many_carts(
        db: Session, offset: int, limit: int, min_price: float, max_price: float, min_quantity: int, max_quantity: int
) -> List[db_models.Cart]:
    all_carts = db.query(db_models.Cart).options(
        joinedload(db_models.Cart.items).joinedload(db_models.CartItem.item)
    ).offset(offset).limit(limit).all()

    filtered_carts = []
    for cart in all_carts:
        total_quantity = sum(ci.quantity for ci in cart.items if not ci.item.deleted)
        total_price = cart.total_price

        if (min_price <= total_price <= max_price and
                min_quantity <= total_quantity <= max_quantity):
            filtered_carts.append(cart)

    return filtered_carts


def add_item_to_cart(db: Session, cart_id: int, item_id: int) -> db_models.Cart | None:
    cart = get_one_cart(db, cart_id)
    item = get_one_item(db, item_id)

    if not cart or not item:
        return None

    cart_item = db.query(db_models.CartItem).filter(
        db_models.CartItem.cart_id == cart_id,
        db_models.CartItem.item_id == item_id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = db_models.CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(new_cart_item)

    db.commit()
    db.refresh(cart)
    return cart