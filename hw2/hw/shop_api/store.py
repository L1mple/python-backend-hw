from typing import List, Iterable

from enum import Enum

from hw2.hw.shop_api.contracts import PutItemRequest
from .models import (
    CartEntity,
    CartInfo,
    CartItemEntity,
    CartItemInfo,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)

_carts = dict[int, CartInfo]()
_items = dict[int, ItemInfo]()

def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1

_cart_id_generator: Iterable[int] = int_id_generator()

_item_id_generator: Iterable[int] = int_id_generator()

def create_cart() -> int:
    id: int = next(_cart_id_generator)
    _carts[id] = CartInfo(items=[], price=0)
    return id

def add_item(info: ItemInfo) -> ItemEntity:
    _id = next(_item_id_generator)
    _items[_id] = info
    
    return ItemEntity(id = _id, info = info)

def delete_card(id: int) -> None:
    if id in _carts:
        del _carts[id]

def delete_item(id: int) -> None:
    if id in _items:
        del _items[id]

def get_cart(id: int) -> CartEntity | None:
    if id not in _carts:
        return None

    return CartEntity(id=id, info = _carts[id])

def get_all_carts() -> List[CartEntity]:
     return [CartEntity(id=id, info=info) for id, info in list(_carts.items())]

def get_item(id: int) -> ItemEntity | None:
    if id not in _items:
        return None

    return ItemEntity(id=id, info = _items[id])

def get_all_items() -> List[ItemEntity]:
     return [ItemEntity(id=id, info=info) for id, info in list(_items.items())]

def add_item_to_cart(cart_id: int, item: ItemEntity) -> bool:
    if cart_id not in _carts:
        return False
        
    cart = _carts[cart_id]
        
    if item.id in [item.id for item in cart.items]:
        for cart_item in cart.items:
            if cart_item.id == item.id:
                cart_item.info.quantity += 1
                break
        
    new_cart_item = CartItemEntity(
        id=item.id,
        info = CartItemInfo(
            name=item.info.name,
            quantity=1,
            available=not item.info.deleted
            )
        )
    cart.items.append(new_cart_item)
        
    cart.price = sum(cart_item.info.quantity * _items[cart_item.id].price 
        for cart_item in cart.items if cart_item.info.available)
        
    _carts[cart_id] = cart   
    
    return True

def update_item(item_id: int, item_data: ItemInfo) -> bool:
    if item_id not in _items:
        return False
    _items[item_id] = item_data
    return True

def put_item(item_id: int, request: PutItemRequest) -> ItemEntity | None:
    if item_id not in _items:
        return None
    existing = _items[item_id]
    if existing.deleted:
        return None
    existing.name = request.name
    existing.price = request.price
    return ItemEntity(item_id, existing)        

class PatchResult(Enum):
    NotFound = 0
    NotModified = 1
    Unprocessable = 2

def patch_item(item_id: int, patch_info: PatchItemInfo) -> ItemEntity | PatchResult:
    if item_id not in _items:
        return PatchResult.NotModified
    
    existing = _items[item_id]
    
    if existing.deleted:
        return PatchResult.NotModified
    
    if patch_info.name is not None:
        existing.name = patch_info.name
        
        
    if patch_info.price is not None and patch_info.price < 0:
        return PatchResult.Unprocessable
    elif patch_info.price is not None:
        existing.price = patch_info.price
        
    return ItemEntity(id=item_id, info = _items[item_id])
