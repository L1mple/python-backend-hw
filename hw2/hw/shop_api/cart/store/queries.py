from logging import info
from typing import Iterable

from shop_api.item.store.models import ItemEntity
from shop_api.cart.store.models import CartEntity, CartInfo, CartItemInfo


_data: dict[int, CartInfo] = {}


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_id_generator = int_id_generator()


def create() -> CartEntity:
    _id = next(_id_generator)
    info = CartInfo(items=[], price=0.0)
    _data[_id] = info
    return CartEntity(id=_id, info=info)


def add(cart_id: int, item_entity: ItemEntity) -> CartEntity:
    cart_info = _data[cart_id]
    for ci in cart_info.items:
        if ci.id == item_entity.id:
            ci.quantity += 1
            ci.available = not item_entity.info.deleted
            break
    else:
        cart_info.items.append(
            CartItemInfo(
                id=item_entity.id,
                name=item_entity.info.name,
                quantity=1,
                available=not item_entity.info.deleted,
            )
        )
    cart_info.price += item_entity.info.price
    _data[cart_id] = cart_info

    return CartEntity(id=cart_id, info=cart_info)


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
    min_price: float = None,
    max_price: float = None,
    min_quantity: int = None,
    max_quantity: int = None,
) -> Iterable[CartEntity]:
    curr = 0
    for id, info in _data.items():
        if min_price is not None and min_price > info.price:
            continue
        if max_price is not None and max_price < info.price:
            continue

        sum_quantity = 0
        for item in info.items:
            sum_quantity += item.quantity

        if min_quantity is not None and min_quantity > sum_quantity:
            continue
        if max_quantity is not None and max_quantity < sum_quantity:
            continue

        if offset <= curr < offset + limit:
            yield CartEntity(id, info)

        curr += 1
