from typing import Iterable

from .models import (
    CartEntity,
    CartInfo,
    CartItemInfo,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)

_items = dict[int, ItemInfo]()
_carts = dict[int, CartInfo]()


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_item_id_generator = int_id_generator()
_cart_id_generator = int_id_generator()


def add_item(info: ItemInfo) -> ItemEntity:
    _id = next(_item_id_generator)
    _items[_id] = info
    return ItemEntity(id=_id, info=info)


def get_item(item_id: int, include_deleted: bool = False) -> ItemEntity | None:
    if item_id not in _items:
        return None
    
    info = _items[item_id]
    if not include_deleted and info.deleted:
        return None
    
    return ItemEntity(id=item_id, info=info)


def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> list[ItemEntity]:
    result = []
    
    for item_id, info in _items.items():
        if not show_deleted and info.deleted:
            continue
        
        if min_price is not None and info.price < min_price:
            continue
        if max_price is not None and info.price > max_price:
            continue
        
        result.append(ItemEntity(id=item_id, info=info))
    
    return result[offset:offset + limit]


def update_item(item_id: int, info: ItemInfo) -> ItemEntity | None:
    if item_id not in _items:
        return None
    
    _items[item_id] = info
    return ItemEntity(id=item_id, info=info)


def patch_item(item_id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if item_id not in _items:
        return None
    
    info = _items[item_id]
    
    if info.deleted:
        return None
    
    if patch_info.name is not None:
        info.name = patch_info.name
    
    if patch_info.price is not None:
        info.price = patch_info.price
    
    return ItemEntity(id=item_id, info=info)


def delete_item(item_id: int) -> None:
    if item_id in _items:
        _items[item_id].deleted = True


def add_cart() -> CartEntity:
    _id = next(_cart_id_generator)
    info = CartInfo(items=[])
    _carts[_id] = info
    return CartEntity(id=_id, info=info)


def get_cart(cart_id: int) -> CartEntity | None:
    if cart_id not in _carts:
        return None
    
    return CartEntity(id=cart_id, info=_carts[cart_id])


def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> list[CartEntity]:
    result = []
    
    for cart_id, info in _carts.items():
        total_price = 0.0
        total_quantity = 0
        
        for cart_item in info.items:
            total_quantity += cart_item.quantity
            
            item_entity = get_item(cart_item.id, include_deleted=True)
            if item_entity and cart_item.available:
                total_price += item_entity.info.price * cart_item.quantity
        
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        result.append(CartEntity(id=cart_id, info=info))
    
    return result[offset:offset + limit]


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity | None:
    if cart_id not in _carts:
        return None
    
    cart_info = _carts[cart_id]
    
    item_entity = get_item(item_id, include_deleted=True)
    if not item_entity:
        return None
    
    for cart_item in cart_info.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            cart_item.available = not item_entity.info.deleted
            return CartEntity(id=cart_id, info=cart_info)
    
    cart_item = CartItemInfo(
        id=item_id,
        name=item_entity.info.name,
        quantity=1,
        available=not item_entity.info.deleted,
    )
    cart_info.items.append(cart_item)
    
    return CartEntity(id=cart_id, info=cart_info)
