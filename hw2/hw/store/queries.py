from typing import Iterable

from .models import (
    CartItem,
    Cart,
    Item,
    ITEMS,
    CARTS,
)


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_item_id_generator = int_id_generator()
_cart_id_generator = int_id_generator()


## Cart methods
def post_cart() -> int:
    cart_id = next(_cart_id_generator)
    CARTS[cart_id] = Cart(id=cart_id, price=0.0, items=[])
    return cart_id


def get_cart(id: int) -> Cart | None:
    if id not in CARTS:
        return None
    return CARTS[id]


def get_carts_list(
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None,
) -> list[Cart]:
    assert offset >= 0
    assert limit > 0

    carts: list[Cart] = list(CARTS.values())

    if min_price is not None:
        carts = [cart for cart in carts if cart.price >= min_price]
    if max_price is not None:
        carts = [cart for cart in carts if cart.price <= max_price]
    if min_quantity is not None:
        carts = [
            cart for cart in carts
            if _compute_cart_quantity(cart) >= min_quantity
        ]
    if max_quantity is not None:
        carts = [
            cart for cart in carts
            if _compute_cart_quantity(cart) <= max_quantity
        ]

    return carts[offset: offset + limit]


def add_item_to_cart(cart_id: int, item_id: int) -> None:
    cart = CARTS[cart_id]

    added = False
    for item in cart.items:
        if item.id == item_id:
            item.quantity += 1
            added = True
            cart.price += ITEMS[item_id].price

    if not added:
        item = ITEMS[item_id]
        cart.items.append(CartItem(
            id=item_id,
            name=item.name,
            quantity=1,
            available=not item.deleted
        ))
        cart.price += ITEMS[item_id].price


## Item methods
def post_item(name: str, price: float, deleted: bool = False) -> int:
    item_id = next(_item_id_generator)
    ITEMS[item_id] = Item(
        id=item_id,
        name=name,
        price=price,
        deleted=deleted,
    )
    return item_id


def get_item(item_id: int) -> Item | None:
    if item_id not in ITEMS:
        return None
    item = ITEMS[item_id]
    if item.deleted:
        return None
    return item


def get_items_list(
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False
) -> list[Item]:
    assert offset >= 0
    assert limit > 0

    items: list[Item] = list(ITEMS.values())

    if not show_deleted:
        items = [item for item in items if not item.deleted]

    if min_price is not None:
        items = [item for item in items if item.price >= min_price]
    if max_price is not None:
        items = [item for item in items if item.price <= max_price]

    return items[offset: offset + limit]


def put_item(item_id: int, name: str, price: float) -> Item | None:
    if item_id not in ITEMS:
        return None
    item = ITEMS[item_id]
    if item.deleted:
        return None
    item.name = name
    item.price = price
    return item


def patch_item(item_id: int, name: str | None = None, price: float | None = None) -> Item | None:
    if item_id not in ITEMS:
        return None
    item = ITEMS[item_id]
    if item.deleted:
        return None
    if name is not None:
        item.name = name
    if price is not None:
        item.price = price
    return item


def delete_item(item_id: int) -> None:
    item = ITEMS.get(item_id)
    if item is None:
        return None
    item.deleted = True


def _compute_cart_quantity(cart: Cart) -> int:
    return sum(cart_item.quantity for cart_item in cart.items)
