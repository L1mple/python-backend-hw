from .models import (
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
    CartEntity,
    CartInfo,
    CartItemEntity,
)
from typing import Iterable

_data = {
    "items": dict[int, ItemInfo](),
    "carts": dict[int, CartInfo](),
}


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_id_generator = int_id_generator()


def add_item(info: ItemInfo) -> ItemEntity:
    _id = next(_id_generator)
    _data["items"][_id] = info
    return ItemEntity(_id, info)


def get_item(id: int) -> ItemEntity | None:
    if id not in _data["items"] or _data["items"][id].deleted:
        return None
    return ItemEntity(id, _data["items"][id])


def get_many_items(
    offset: int = 0, limit: int = 10, min_price: float = None, max_price: float = None
) -> Iterable[ItemEntity]:
    curr = 0
    for id, info in _data["items"].items():
        if offset <= curr < offset + limit:
            if min_price is not None and info.price < min_price:
                continue
            if max_price is not None and info.price > max_price:
                continue
            yield ItemEntity(id, info)
        curr += 1


def replace_item(id: int, info: ItemInfo) -> ItemEntity:
    if id not in _data["items"]:
        return None
    _data["items"][id] = info
    return ItemEntity(id, info)


def patch_item(id: int, patch_info: PatchItemInfo) -> ItemEntity:
    if id not in _data["items"] or _data["items"][id].deleted:
        return None

    curr_info = _data["items"][id]

    if patch_info.name is not None:
        curr_info.name = patch_info.name
    if patch_info.price is not None:
        curr_info.price = patch_info.price

    return ItemEntity(id, curr_info)


def delete_item(id: int) -> None:
    if id not in _data["items"]:
        return None
    _data["items"][id].deleted = True
    return ItemEntity(id, _data["items"][id])


def add_cart(info: CartInfo) -> CartEntity:
    _id = next(_id_generator)
    _data["carts"][_id] = info
    return CartEntity(_id, info)


def get_cart(id: int) -> CartEntity | None:
    if id not in _data["carts"]:
        return None
    return CartEntity(id, _data["carts"][id])


def get_many_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: float = None,
    max_price: float = None,
    min_quantity: int = None,
    max_quantity: int = None,
) -> Iterable[CartEntity]:
    curr = 0
    for id, info in _data["carts"].items():
        if offset <= curr < offset + limit:
            if min_price is not None and info.price < min_price:
                continue
            if max_price is not None and info.price > max_price:
                continue
            if min_quantity is not None and len(info.items) < min_quantity:
                continue
            if max_quantity is not None and len(info.items) > max_quantity:
                continue
            yield CartEntity(id, info)
        curr += 1


def add_item_to_cart(cart_id: int, item_id: int) -> CartItemEntity | None:
    if cart_id not in _data["carts"]:
        return None
    if item_id not in _data["items"]:
        return None

    cart_info = _data["carts"][cart_id]
    item_info = _data["items"][item_id]

    # Find if item already in cart
    for cart_item in cart_info.items:
        if cart_item.item_id == item_id:
            cart_item.quantity += 1
            return cart_item  # Return updated item

    # Not in cart, add it
    new_cart_item = CartItemEntity(
        item_id=item_id,
        item_name=item_info.name,
        quantity=1,
        available=not item_info.deleted,
    )
    cart_info.items.append(new_cart_item)
    return new_cart_item  # Return new item
