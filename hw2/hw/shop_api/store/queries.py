from typing import Iterable

from hw2.hw.shop_api.store.models import *


_data_items = dict[int, ItemInfo]()
_data_carts = dict[int, CartInfo]()



def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_id_generator = int_id_generator()


def add_item(info: ItemInfo) -> ItemEntity:
    _id = next(_id_generator)
    _data_items[_id] = info

    return ItemEntity(_id, info)


def delete_item(id: int) -> None:
    if id in _data_items:
        if _data_items[id].deleted:
            return
        _data_items[id].deleted = True
    else:
        return
    for cart_id, cart_info in _data_carts.items():
        if id in cart_info.items:
            cart_info.items[id].available = False
            cart_info.price -= _data_items[id].price * cart_info.items[id].quantity


def get_one_item(id: int) -> ItemEntity | None:
    if id not in _data_items or _data_items[id].deleted:
        return None

    return ItemEntity(id, _data_items[id])


def get_many_items(offset: int = 0,
                   limit: int = 10,
                   min_price: float = 0,
                   max_price: float = 1e10,
                   show_deleted: bool = False) -> Iterable[ItemEntity]:
    curr = 0
    for id, info in _data_items.items():
        if offset <= curr < offset + limit \
                and min_price <= info.price <= max_price \
                and (not info.deleted or show_deleted):
            yield ItemEntity(id, info)

        curr += 1


def update_item(id: int, info: ItemInfo) -> ItemEntity | None:
    if id not in _data_items:
        return None

    old_info = _data_items[id]
    _data_items[id] = info

    for cart_id, cart_info in _data_carts.items():
        if id in cart_info.items:
            cart_info.items[id].name = _data_items[id].name
            cart_info.price -= old_info.price * cart_info.items[id].quantity
            cart_info.price += _data_items[id].price * cart_info.items[id].quantity

    return ItemEntity(id, info)


def patch_item(id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if id not in _data_items or _data_items[id].deleted:
        return None
    old_price = _data_items[id].price
    if patch_info.name is not None:
        _data_items[id].name = patch_info.name
    if patch_info.price is not None:
        _data_items[id].price = patch_info.price
    for cart_id, cart_info in _data_carts.items():
        if id in cart_info.items:
            cart_info.items[id].name = _data_items[id].name
            cart_info.price -= old_price * cart_info.items[id].quantity
            cart_info.price += _data_items[id].price * cart_info.items[id].quantity
    return ItemEntity(id, _data_items[id])


def add_cart() -> CartEntity:
    _id = next(_id_generator)
    _data_carts[_id] = CartInfo({}, 0)

    return CartEntity(_id, _data_carts[_id])


def get_one_cart(id: int) -> CartEntity | None:
    if id not in _data_carts:
        return None

    return CartEntity(id, _data_carts[id])


def get_many_carts(offset: int = 0,
                   limit: int = 10,
                   min_price: float = 0,
                   max_price: float = 1e10,
                   min_quantity: int = 0,
                   max_quantity: int = 1e10) -> Iterable[CartEntity]:
    curr = 0
    for id, info in _data_carts.items():
        if offset <= curr < curr + limit \
                and min_price <= info.price <= max_price \
                and min_quantity <= sum([item.quantity for _, item in info.items.items() if item.available]) <= max_quantity:
            yield CartEntity(id, info)

        curr += 1


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity | None:
    if cart_id not in _data_carts:
        return None

    if item_id in _data_carts[cart_id].items:
        _data_carts[cart_id].items[item_id].quantity += 1
    else:
        _data_carts[cart_id].items[item_id] = ItemCartInfo(_data_items[item_id].name, 1, True)
    _data_carts[cart_id].price += _data_items[item_id].price
    return CartEntity(cart_id, _data_carts[cart_id])
