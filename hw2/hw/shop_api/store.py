from typing import Iterable

from .models import (
    CartEntity,
    CartItem,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)

_items = dict[int, ItemInfo]()
_carts = dict[int, CartEntity]()

_item_counter = 0
_cart_counter = 0


def _get_next_item_id() -> int:
    global _item_counter
    _item_counter += 1
    return _item_counter


def _get_next_cart_id() -> int:
    global _cart_counter
    _cart_counter += 1
    return _cart_counter


def add_item(info: ItemInfo) -> ItemEntity:
    item_id = _get_next_item_id()
    _items[item_id] = info
    return ItemEntity(item_id, info)


def get_item(item_id: int) -> ItemEntity | None:
    if item_id not in _items:
        return None
    return ItemEntity(id=item_id, info=_items[item_id])


def get_items_filtered(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> list[ItemEntity]:
    result = []
    curr = 0
    for item_id, info in _items.items():
        if not show_deleted and info.deleted:
            continue
            
        if min_price is not None and info.price < min_price:
            continue
        if max_price is not None and info.price > max_price:
            continue
            
        if offset <= curr < offset + limit:
            result.append(ItemEntity(item_id, info))
            
        curr += 1
    
    return result


def update_item(item_id: int, info: ItemInfo) -> ItemEntity | None:
    if item_id not in _items:
        return None
    
    _items[item_id] = info
    return ItemEntity(id=item_id, info=info)


def patch_item(item_id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if item_id not in _items:
        return None
    
    info = _items[item_id]
    
    if patch_info.name is not None:
        info.name = patch_info.name
    if patch_info.price is not None:
        info.price = patch_info.price
    if patch_info.deleted is not None:
        info.deleted = patch_info.deleted
    
    return ItemEntity(id=item_id, info=info)


def delete_item(item_id: int) -> bool:
    if item_id not in _items:
        return False
    
    _items[item_id].deleted = True
    return True


def add_cart() -> CartEntity:
    cart_id = _get_next_cart_id()
    cart = CartEntity(id=cart_id, items=[], price=0.0)
    _carts[cart_id] = cart
    return cart


def get_cart(cart_id: int) -> CartEntity | None:
    if cart_id not in _carts:
        return None
    return _carts[cart_id]


def get_carts_filtered(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> list[CartEntity]:
    result = []
    curr = 0
    for cart_id, cart in _carts.items():
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
            
        total_quantity = sum(item.quantity for item in cart.items)
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
            
        if offset <= curr < offset + limit:
            result.append(cart)
            
        curr += 1
    
    return result


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity | None:
    if cart_id not in _carts:
        return None
    
    item_entity = get_item(item_id)
    if not item_entity or item_entity.info.deleted:
        return None
    
    cart = _carts[cart_id]
    
    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            cart.price += item_entity.info.price
            return cart
    
    new_cart_item = CartItem(
        id=item_id,
        name=item_entity.info.name,
        quantity=1,
        available=True,
    )
    cart.items.append(new_cart_item)
    cart.price += item_entity.info.price
    
    return cart


def _recalculate_cart_price(cart: CartEntity) -> None:
    total_price = 0.0
    for cart_item in cart.items:
        item_entity = get_item(cart_item.id)
        if item_entity and not item_entity.info.deleted:
            total_price += item_entity.info.price * cart_item.quantity
            cart_item.available = True
        else:
            cart_item.available = False
    
    cart.price = total_price