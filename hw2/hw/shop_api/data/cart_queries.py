from typing import Iterable

from .models import (
    CartInfo,
    CartItemInfo,
    CartEntity,
    PatchCartInfo,
)

from . import item_queries

_data = dict[int, CartInfo]()


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_id_generator = int_id_generator()


def add(info: CartInfo) -> CartEntity:
    _id = next(_id_generator)
    _data[_id] = info

    return CartEntity(_id, info)


def delete(id: int) -> None:
    if id in _data:
        del _data[id]


def get_one(id: int) -> CartEntity | None:
    if id not in _data:
        return None

    return CartEntity(id=id, info=_data[id])


def get_many(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> Iterable[CartEntity]:
    curr = 0
    yielded = 0

    for id, info in _data.items():
        if min_price is not None and info.price < min_price:
            continue
        if max_price is not None and info.price > max_price:
            continue

        total_quantity = sum(item.quantity for item in info.items)
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        if curr >= offset:
            yield CartEntity(id, info)
            yielded += 1
            if yielded >= limit:
                break

        curr += 1


def update(id: int, info: CartInfo) -> CartEntity | None:
    if id not in _data:
        return None

    _data[id] = info

    return CartEntity(id=id, info=info)


def upsert(id: int, info: CartInfo) -> CartEntity:
    _data[id] = info

    return CartEntity(id=id, info=info)


def patch(id: int, patch_info: PatchCartInfo) -> CartEntity | None:
    if id not in _data:
        return None

    if patch_info.items is not None:
        _data[id].items = patch_info.items

    return CartEntity(id=id, info=_data[id])


def _calculate_price(cart_info: CartInfo) -> float:
    total = 0.0
    for item in cart_info.items:
        product = item_queries.get_one(item.id)
        if product:
            total += product.info.price * item.quantity
    return total


def add_item_to_cart(cart_id: int, product_id: int, quantity: int) -> CartEntity | None:
    if cart_id not in _data:
        return None

    product = item_queries.get_one(product_id)

    if not product:
        return None

    for item in _data[cart_id].items:
        if item.id == product_id:
            item.quantity += quantity
            _data[cart_id].price = _calculate_price(_data[cart_id])
            return CartEntity(id=cart_id, info=_data[cart_id])

    cart_item = CartItemInfo(
        id=product.id,
        name=product.info.name,
        quantity=quantity,
        available=not product.info.deleted,
    )

    _data[cart_id].items.append(cart_item)
    _data[cart_id].price = _calculate_price(_data[cart_id])

    return CartEntity(id=cart_id, info=_data[cart_id])


def remove_item_from_cart(cart_id: int, product_id: int) -> CartEntity | None:
    if cart_id not in _data:
        return None

    for item in _data[cart_id].items:
        if item.id == product_id:
            _data[cart_id].items.remove(item)
            _data[cart_id].price = _calculate_price(_data[cart_id])
            return CartEntity(id=cart_id, info=_data[cart_id])

    return None
