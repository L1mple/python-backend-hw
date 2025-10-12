from typing import Iterable
from itertools import count

from shop_api.api.item.store import get_one as get_item
from .models import (
    CartEntity,
    CartInfo,
    CardItem,
)

_data: dict[int, CartInfo] = {}

_id_generator = count()


def create(info: CartInfo) -> CartEntity:
    _id = next(_id_generator)
    _data[_id] = info

    return CartEntity(_id, info)

def get_one(id: int) -> CartEntity | None:
    info = _data.get(id)
    return CartEntity(id=id, info=info) if info else None


def get_list(offset: int = 0, limit: int = 10, min_price: float | None = None, max_price: float | None = None, show_deleted: bool = False, min_quantity: int | None = None, max_quantity: int | None = None) -> Iterable[CartEntity]:
    def matches_filters(info: CartInfo) -> bool:
        if min_price is not None and info.price < min_price:
            return False
        if max_price is not None and info.price > max_price:
            return False
        
        sum_quantity = sum(item.quantity for item in info.items)
        if min_quantity is not None and sum_quantity < min_quantity:
            return False
        if max_quantity is not None and sum_quantity > max_quantity:
            return False
        
        return True
    
    filtered_items = [CartEntity(id, info) for id, info in _data.items() if matches_filters(info)]
    return filtered_items[offset:offset+limit]
    


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity | None:
    cart_info = _data.get(cart_id)
    item_entity = get_item(item_id)
    
    if not cart_info or not item_entity or item_entity.info.deleted:
        return None

    existing_item = next((item for item in cart_info.items if item.id == item_id), None)
    
    if existing_item:
        existing_item.quantity += 1
    else:
        cart_info.items.append(CardItem(
            id=item_id,
            name=item_entity.info.name,
            quantity=1,
            available=not item_entity.info.deleted
        ))

    cart_info.price += item_entity.info.price

    return CartEntity(id=cart_id, info=cart_info)

