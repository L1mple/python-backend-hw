from __future__ import annotations

from typing import Dict

from .schemas import Item


# In-memory storage shared by REST and gRPC layers
items_by_id: Dict[int, Item] = {}
carts_items: Dict[int, Dict[int, int]] = {}
next_item_id: int = 1
next_cart_id: int = 1


def reset_storage() -> None:
    global items_by_id, carts_items, next_item_id, next_cart_id
    items_by_id = {}
    carts_items = {}
    next_item_id = 1
    next_cart_id = 1


