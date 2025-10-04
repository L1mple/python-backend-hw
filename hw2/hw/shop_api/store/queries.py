from typing import Iterable, Optional

from .models import (
    ItemInfo,
    ItemEntity,
    PatchItemInfo,
    CartItemInfo,
    CartInfo,
    CartEntity
)

def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1

_items_data = dict[int, ItemInfo]()
_cart_data = dict[int, CartInfo]()

_items_id_generator = int_id_generator()
_cart_id_generator = int_id_generator()

# Items queries

def add_item(info : ItemInfo) -> ItemEntity:
    _id = next(_items_id_generator)
    print(_id)
    _items_data[_id] = info
    return ItemEntity(_id, info)

def delete_item(id : int) -> None:
    if id in _items_data:
        del _items_data[id]

def get_item(id : int) -> ItemEntity | None:
    if id not in _items_data:
        return None

    return ItemEntity(id, _items_data[id])

def get_items(offset : int = 0, limit : int = 10, min_price : Optional[float] = None, max_price : Optional[float] = None, show_deleted : bool = False) -> Iterable[ItemEntity]:
    cur = 0
    taken = 0
    for id, info in _items_data.items():
        if taken >= limit:
            break
        if min_price is not None and info.price < min_price:
            continue
        if max_price is not None and info.price > max_price:
            continue
        if info.deleted and not show_deleted:
            continue

        if offset <= cur:
            yield ItemEntity(id, info)
            taken += 1
        cur += 1


def update_item(id : int, info : ItemInfo) -> ItemEntity | None:
    if id not in _items_data:
        return None

    _items_data[id] = info
    return ItemEntity(id, info)

def patch_item(id : int, patch_info : PatchItemInfo) -> ItemEntity | None:
    if id not in _items_data:
        return None

    if patch_info.name is not None:
        _items_data[id].name = patch_info.name

    if patch_info.price is not None:
        _items_data[id].price = patch_info.price

    return ItemEntity(id, _items_data[id])

# Cart queries

def create_cart() -> CartEntity:
    _id = next(_cart_id_generator)
    _cart_data[_id] = CartInfo()
    return CartEntity(_id, _cart_data[_id])

def delete_cart(id : int) -> None:
    if id in _cart_data:
        del _cart_data[id]

def get_cart(id : int) -> CartEntity | None:
    if id not in _cart_data:
        return None

    cart = _cart_data[id]
    cart.price = 0

    for item_info in cart.items:
        item = _items_data[item_info.id]
        item_info.name = item.name
        item_info.price = item.price
        item_info.available = not item.deleted
        cart.price += item.price * item_info.quantity

    return CartEntity(id, _cart_data[id])

def get_carts(
    offset : int = 0, limit : int = 10,
    min_price : Optional[float] = None, max_price : Optional[float] = None,
    min_quantity : Optional[int] = None, max_quantity : Optional[int] = None
) -> Iterable[CartEntity]:
    cur = 0
    taken = 0
    for id in _cart_data.keys():
        if taken >= limit:
            break
        if offset > cur:
            continue
        cart = get_cart(id)
        if min_price is not None and cart.info.price < min_price:
            continue
        if max_price is not None and cart.info.price > max_price:
            continue
        if min_quantity is not None and cart.info.quantity < min_quantity:
            continue
        if max_quantity is not None and cart.info.quantity > max_quantity:
            continue

        yield cart
        cur += 1
        taken += 1


def add_to_cart(cart_id : int, item : ItemEntity) -> CartEntity | None:
    if cart_id not in _cart_data:
        return None

    for cart_item in _cart_data[cart_id].items:
        if cart_item.id == item.id:
            cart_item.quantity += 1
            break
    else:
        _cart_data[cart_id].items.append(CartItemInfo(
            item.id, 1, item.info.name, item.info.price, not item.info.deleted
        ))

    _cart_data[cart_id].price += item.info.price
    _cart_data[cart_id].quantity += 1

    return CartEntity(cart_id, _cart_data[cart_id])
