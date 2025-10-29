from typing import Iterable

from .models import (
    CartEntity,
    CartItem,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)


# Хранилище данных в памяти
_items: dict[int, ItemEntity] = {}
_carts: dict[int, CartEntity] = {}


def _int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_item_id_generator = _int_id_generator()
_cart_id_generator = _int_id_generator()



def add_item(info: ItemInfo) -> ItemEntity:
    item_id = next(_item_id_generator)
    item = ItemEntity(
        id=item_id,
        name=info.name,
        price=info.price,
        deleted=info.deleted,
    )
    _items[item_id] = item
    return item


def get_item(item_id: int) -> ItemEntity | None:
    item = _items.get(item_id)
    if item and item.deleted:
        return None
    return item


def get_item_including_deleted(item_id: int) -> ItemEntity | None:
    return _items.get(item_id)


def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> list[ItemEntity]:
    result = []
    
    for item in _items.values():
        if not show_deleted and item.deleted:
            continue
            
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue
            
        result.append(item)
    
    return result[offset:offset + limit]


def update_item(item_id: int, info: ItemInfo) -> ItemEntity | None:
    if item_id not in _items:
        return None
    
    item = ItemEntity(
        id=item_id,
        name=info.name,
        price=info.price,
        deleted=_items[item_id].deleted,
    )
    _items[item_id] = item
    return item


def patch_item(item_id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    item = _items.get(item_id)
    if not item or item.deleted:
        return None
    
    if patch_info.name is not None:
        item.name = patch_info.name
    if patch_info.price is not None:
        item.price = patch_info.price
    
    return item


def delete_item(item_id: int) -> bool:
    if item_id in _items:
        _items[item_id].deleted = True
        return True
    return False


def create_cart() -> CartEntity:
    cart_id = next(_cart_id_generator)
    cart = CartEntity(id=cart_id, items=[], price=0.0)
    _carts[cart_id] = cart
    return cart


def get_cart(cart_id: int) -> CartEntity | None:
    return _carts.get(cart_id)


def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> list[CartEntity]:
    result = []
    
    for cart in _carts.values():
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        
        total_quantity = sum(item.quantity for item in cart.items)
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        result.append(cart)
    
    return result[offset:offset + limit]


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity | None:
    cart = _carts.get(cart_id)
    if not cart:
        return None
    
    item = get_item_including_deleted(item_id)
    if not item:
        return None
    
    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            break
    else:
        cart_item = CartItem(
            id=item.id,
            name=item.name,
            quantity=1,
            available=not item.deleted,
        )
        cart.items.append(cart_item)
    
    cart.price = sum(
        get_item_including_deleted(ci.id).price * ci.quantity
        for ci in cart.items
        if get_item_including_deleted(ci.id)
    )
    
    return cart
