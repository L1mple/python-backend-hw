from __future__ import annotations
from threading import (
    RLock,
)  # стандартная библиотека Python: https://docs.python.org/3/library/threading.html
from typing import Optional
from fastapi import HTTPException, status
from .schemas import (
    ItemOut,
    CartItemView,
    CartView,
    ItemCreate,
    ItemPut,
    ItemPatch,
)

# -------------------------
# In-memory хранилище + блокировки
# -------------------------
_items_lock = RLock()
_carts_lock = RLock()

_items: dict[int, ItemOut] = {}
_next_item_id = 1

# cart_id -> { item_id -> quantity }
_carts: dict[int, dict[int, int]] = {}
_next_cart_id = 1


def new_item_id() -> int:
    global _next_item_id
    with _items_lock:
        nid = _next_item_id
        _next_item_id += 1
        return nid


def new_cart_id() -> int:
    global _next_cart_id
    with _carts_lock:
        nid = _next_cart_id
        _next_cart_id += 1
        return nid


def get_item_or_404(item_id: int) -> ItemOut:
    with _items_lock:
        item = _items.get(item_id)
        if item is None or item.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return item


def get_item_soft(item_id: int) -> Optional[ItemOut]:
    with _items_lock:
        return _items.get(item_id)


def cart_or_404(cart_id: int) -> dict[int, int]:
    with _carts_lock:
        cart = _carts.get(cart_id)
        if cart is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
            )
        return cart


def build_cart_view(cart_id: int) -> CartView:
    with _carts_lock:
        cart = _carts.get(cart_id, {})
        kv = list(cart.items())

    items = []
    total = 0.0
    for item_id, qty in kv:
        item = get_item_soft(item_id)
        name = item.name if item else f"item:{item_id}"
        available = bool(item and not item.deleted)
        items.append(
            CartItemView(id=item_id, name=name, quantity=qty, available=available)
        )
        if available:
            total += item.price * qty

    return CartView(id=cart_id, items=items, price=total)


def create_item(data: ItemCreate) -> ItemOut:
    item_id = new_item_id()
    item = ItemOut(id=item_id, name=data.name, price=data.price, deleted=False)
    with _items_lock:
        _items[item_id] = item
    return item


def put_item(item_id: int, data: ItemPut) -> ItemOut:
    with _items_lock:
        existing = _items.get(item_id)
        if existing is None or existing.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        existing.name = data.name
        existing.price = data.price
        return existing


def patch_item(item_id: int, data: ItemPatch) -> ItemOut:
    with _items_lock:
        existing = _items.get(item_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        if existing.deleted:
            # Пробрасываем семантику 304 на верхний уровень
            raise HTTPException(
                status_code=status.HTTP_304_NOT_MODIFIED, detail="Item deleted"
            )

        if data.name is not None:
            existing.name = data.name
        if data.price is not None:
            if data.price < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid price",
                )
            existing.price = data.price

        return existing


def delete_item(item_id: int) -> dict:
    with _items_lock:
        existing = _items.get(item_id)
        if existing is not None:
            existing.deleted = True
    return {"ok": True}
