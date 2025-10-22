from typing import Iterable, Optional
from sqlalchemy.orm import Session

from shop_api.cart.store.schemas import CartEntity, CartItemEntity
from shop_api.item.store.schemas import ItemEntity
from shop_api.cart.store.models import Cart, CartItem


def create(db: Session) -> CartEntity:
    db_cart = Cart()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    return CartEntity(id=db_cart.id, price=db_cart.price, items=[])


def add(db: Session, cart_id: int, item_entity: ItemEntity) -> Optional[CartEntity]:
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        return None

    cart_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart_id, CartItem.item_id == item_entity.id)
        .first()
    )

    if cart_item:
        cart_item.quantity += 1
        cart_item.available = not item_entity.info.deleted
    else:
        cart_item = CartItem(
            cart_id=cart_id,
            item_id=item_entity.id,
            name=item_entity.info.name,
            quantity=1,
            available=not item_entity.info.deleted,
        )
        db.add(cart_item)

    cart.price += item_entity.info.price
    db.commit()
    db.refresh(cart)

    cart_items = [
        CartItemEntity(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            available=item.available
        )
        for item in cart.items
    ]
    return CartEntity(id=cart.id, price=cart.price, items=cart_items)


def delete(db: Session, id: int) -> bool:
    db_cart = db.query(Cart).filter(Cart.id == id).first()
    if db_cart:
        db.delete(db_cart)
        db.commit()
        return True
    return False


def get_one(db: Session, id: int) -> Optional[CartEntity]:
    db_cart = db.query(Cart).filter(Cart.id == id).first()
    if db_cart:
        cart_items = [
            CartItemEntity(
                id=item.id,
                name=item.name,
                quantity=item.quantity,
                available=item.available
            )
            for item in db_cart.items
        ]
        return CartEntity(id=db_cart.id, price=db_cart.price, items=cart_items)
    return None


def get_many(
    db: Session,
    offset: int = 0,
    limit: int = 10,
    min_price: float = None,
    max_price: float = None,
    min_quantity: int = None,
    max_quantity: int = None,
) -> Iterable[CartEntity]:
    query = db.query(Cart)
    if min_price is not None:
        query = query.filter(Cart.price >= min_price)
    if max_price is not None:
        query = query.filter(Cart.price <= max_price)

    carts = query.offset(offset).limit(limit).all()

    result = []
    for cart in carts:
        total_quantity = sum(item.quantity for item in cart.items)

        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        cart_items = [
            CartItemEntity(
                id=item.id,
                name=item.name,
                quantity=item.quantity,
                available=item.available
            )
            for item in cart.items
        ]
        result.append(CartEntity(id=cart.id, price=cart.price, items=cart_items))

    return result