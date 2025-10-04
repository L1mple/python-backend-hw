from __future__ import annotations
from typing import Dict, List
from fastapi import HTTPException

from .models import Item, Cart, CartItem

_items: Dict[int, Item] = {}
_carts: Dict[int, Dict[int, int]] = {}

_item_id_seq = 1
_cart_id_seq = 1

def next_item_id() -> int:
    global _item_id_seq
    i = _item_id_seq
    _item_id_seq += 1
    return i

def next_cart_id() -> int:
    global _cart_id_seq
    i = _cart_id_seq
    _cart_id_seq += 1
    return i

def get_item_or_404(item_id: int) -> Item:
    item = _items.get(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="item not found")
    return item

def get_item_raw(item_id: int) -> Item | None:
    return _items.get(item_id)


def save_item(item: Item) -> None:
    _items[item.id] = item

def create_cart() -> int:
    cid = next_cart_id()
    _carts[cid] = {}
    return cid

def ensure_cart(cart_id: int) -> None:
    if cart_id not in _carts:
        raise HTTPException(status_code=404, detail="cart not found")


def add_to_cart(cart_id: int, item_id: int, count: int = 1) -> None:
    ensure_cart(cart_id)
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="item not found")
    q = _carts[cart_id].get(item_id, 0)
    _carts[cart_id][item_id] = q + max(1, int(count))


def cart_view(cart_id: int) -> Cart:
    ensure_cart(cart_id)
    quantities = _carts[cart_id]
    items: List[CartItem] = []
    total = 0.0
    for iid, qty in quantities.items():
        item = _items.get(iid)
        available = bool(item and not item.deleted)
        name = item.name if item else f"item#{iid}"
        price = item.price if item else 0.0
        if available:
            total += price * qty
        items.append(CartItem(id=iid, name=name, quantity=qty, available=available))
    return Cart(id=cart_id, items=items, price=total)


def all_carts() -> List[int]:
    return list(_carts.keys())


def all_items(show_deleted: bool) -> List[Item]:
    if show_deleted:
     return list(_items.values())
    return [i for i in _items.values() if not i.deleted]