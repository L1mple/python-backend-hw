from typing import Iterable

from shop_api.store.models import (
    ItemInfo,
    CartInfo,
    PatchItemInfo,
    ItemEntity,
    CartEntity,
    CartInfo,
    CartItemInfo
)


_carts_data = dict[int, CartInfo]()
_items_data = dict[int, ItemInfo]()


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_id_generator = int_id_generator()


def add_item(info: ItemInfo) -> ItemEntity:
    _id = next(_id_generator)
    _items_data[_id] = info

    return ItemEntity(_id, info)


def delete_item(id: int) -> None:
    if id in _items_data:
        del _items_data[id]


def get_item(id: int) -> ItemEntity | None:
    if id not in _items_data:
        return None

    return ItemEntity(id=id, info=_items_data[id])


def get_items(
        offset: int = 0, 
        limit: int = 10, 
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False
    ) -> Iterable[ItemEntity]:
    curr = 0
    for id, info in _items_data.items():
        if (offset <= curr < offset + limit) and \
            (min_price == None or info.price >= min_price) and \
            (max_price == None or info.price <= max_price) and \
            (not info.deleted or show_deleted):
            yield ItemEntity(id, info)

        curr += 1


def update_item(id: int, info: ItemInfo) -> ItemEntity | None:
    if id not in _items_data:
        return None

    _items_data[id] = info

    return ItemEntity(id=id, info=info)


def upsert_item(id: int, info: ItemInfo) -> ItemEntity:
    _items_data[id] = info

    return ItemEntity(id=id, info=info)


def patch_item(id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if id not in _items_data:
        return None

    if patch_info.name is not None:
        _items_data[id].name = patch_info.name

    if patch_info.price is not None:
        _items_data[id].price = patch_info.price

    return ItemEntity(id=id, info=_items_data[id])


def get_carts(
        offset: int = 0, 
        limit: int = 10, 
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None
    ) -> Iterable[CartEntity]:
    curr = 0
    # returned_carts_cnt = 0
    for id, info in _carts_data.items():
        cart_items_quantity = 0
        for cart_item in info.items:
            cart_items_quantity += cart_item.quantity
        if (offset <= curr < offset + limit) and \
            (min_price == None or info.price >= min_price) and \
            (max_price == None or info.price <= max_price) and \
            (min_quantity == None or cart_items_quantity >= min_quantity) and \
            (max_quantity == None or cart_items_quantity <= max_quantity):
            # returned_carts_cnt += 1
            yield CartEntity(id, info)

        curr += 1

    # if min_quantity != None and returned_carts_cnt < min_quantity:
    #     while returned_carts_cnt < min_quantity:
    #         returned_carts_cnt += 1
    #         yield CartEntity(0, CartInfo(items=[], price=0.0))


def get_cart(id: int) -> CartEntity | None:
    if id not in _carts_data:
        return None

    return CartEntity(id=id, info=_carts_data[id])


def add_cart() -> CartEntity:
    _id = next(_id_generator)
    info = CartInfo(items=[], price=0.0)
    _carts_data[_id] = info
    return CartEntity(_id, info)


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity:
    cart_entity = get_cart(cart_id)
    is_found_item = False
    for cart_item in cart_entity.info.items:
        if cart_item.id == item_id:
            cart_item.info.quantity += 1
            is_found_item = True
            break
    if not is_found_item:
        item_info = _items_data[item_id]
        cart_entity.info.items.append(CartItemInfo(id=item_id, name=item_info.name, quantity=1, available=not item_info.deleted))
        # _carts_data[cart_id].items.append(CartItemInfo(id=item_id, name=item_info.name, quantity=1, available=not item_info.deleted))

    _carts_data[cart_id] = cart_entity.info
    return cart_entity