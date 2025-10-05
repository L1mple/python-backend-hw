from typing import Iterable

from hw2.hw.shop_api.store.cart_models import (
    PatchCartInfo,
    CartEntity,
    CartInfo,
    CartItemInfo,
)

from hw2.hw.shop_api.store.id_generator import id_generator
from hw2.hw.shop_api.store import item_queries

carts_data = dict[int, CartInfo]()


def add_empty() -> CartEntity:
    _id = next(id_generator)
    carts_data[_id] = CartInfo(items=[], price=0.0)
    return CartEntity(_id, carts_data[_id])


def delete(id: int) -> None:
    if id in carts_data:
        del carts_data[id]


def _recalculate_cart_info(info: CartInfo) -> CartInfo:
    total_price = 0.0
    recalculated_items: list[CartItemInfo] = []
    for item in info.items:
        entity = item_queries.get_one(item.id)
        available = entity is not None
        name = entity.info.name if entity is not None else item.name
        price = entity.info.price if entity is not None else 0.0
        if available:
            total_price += price * item.quantity
        recalculated_items.append(
            CartItemInfo(id=item.id, name=name, quantity=item.quantity, available=available)
        )
    return CartInfo(items=recalculated_items, price=total_price)


def get_one(id: int) -> CartEntity | None:
    if id not in carts_data:
        return None
    recalculated = _recalculate_cart_info(carts_data[id])
    return CartEntity(id=id, info=recalculated)


def get_many(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> Iterable[CartEntity]:
    curr = 0
    for id, info in carts_data.items():
        recalculated = _recalculate_cart_info(info)
        total_quantity = sum(i.quantity for i in recalculated.items)
        if min_price is not None and recalculated.price < min_price:
            continue
        if max_price is not None and recalculated.price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        if offset <= curr < offset + limit:
            yield CartEntity(id, recalculated)
        curr += 1


def update(id: int, info: CartInfo) -> CartEntity | None:
    if id not in carts_data:
        return None
    carts_data[id] = info
    return CartEntity(id=id, info=info)


def upsert(id: int, info: CartInfo) -> CartEntity:
    carts_data[id] = info
    return CartEntity(id=id, info=info)


def patch(id: int, patch_info: PatchCartInfo) -> CartEntity | None:
    if id not in carts_data:
        return None
    if patch_info.items is not None:
        carts_data[id].items = patch_info.items
    recalculated = _recalculate_cart_info(carts_data[id])
    carts_data[id] = recalculated
    return CartEntity(id=id, info=recalculated)


def add_item(cart_id: int, item_id: int) -> CartEntity | None:
    if cart_id not in carts_data:
        return None
    existing = carts_data[cart_id]
    item_entity = item_queries.get_one(item_id)
    name = item_entity.info.name if item_entity is not None else f"item-{item_id}"
    for it in existing.items:
        if it.id == item_id:
            it.quantity += 1
            break
    else:
        existing.items.append(
            CartItemInfo(id=item_id, name=name, quantity=1, available=item_entity is not None)
        )
    recalculated = _recalculate_cart_info(existing)
    carts_data[cart_id] = recalculated
    return CartEntity(id=cart_id, info=recalculated)
