from typing import Optional, Iterable, Tuple

from .schemas import Item, CartItem, Cart
from .models import ItemOrm, CartItemOrm, CartOrm

def cart_aggregate(items : Iterable[CartItem]) -> Tuple[float, int]:
    quantity = 0
    price = 0
    for item in items:
        if item.available:
            quantity += item.quantity
            price += item.quantity*item.price
    return price, quantity

class ItemMapper:
    @staticmethod
    def to_domain(item_orm : ItemOrm) -> Item:
        return Item(
            id=item_orm.id,
            name=item_orm.name,
            price=float(item_orm.price),
            deleted=bool(item_orm.deleted)
        )

    @staticmethod
    def to_orm(item : Item, item_orm : Optional[ItemOrm] = None) -> ItemOrm:
        if item_orm is None:
            item_orm = ItemOrm()
        if item.id is not None:
            item_orm.id = item.id
        item_orm.name = item.name
        item_orm.price = item.price
        item_orm.deleted = item.deleted
        return item_orm

class CartItemMapper:
    @staticmethod
    def to_domain(cart_item_orm : CartItemOrm) -> CartItem:
        return CartItem(
            id=cart_item_orm.id,
            item_id=cart_item_orm.item.id,
            quantity=int(cart_item_orm.quantity),
            name=cart_item_orm.item.name,
            price=float(cart_item_orm.item.price),
            available=not cart_item_orm.item.deleted
        )

class CartMapper:
    @staticmethod
    def to_domain(cart_orm : CartOrm) -> Cart:
        items = [CartItemMapper.to_domain(cart_item) for cart_item in cart_orm.cart_items]
        price, quantity = cart_aggregate(items)
        return Cart(
            id=cart_orm.id,
            items=items,
            price=price,
            quantity=quantity
        )
