from __future__ import annotations
from itertools import count
from shop_api.core.models import Item, Cart

class Store:
    def __init__(self):
        self.items: dict[int, Item] = {}
        self.carts: dict[int, Cart] = {}
        self._item_seq = count(start=1)
        self._cart_seq = count(start=1)

    def next_item_id(self) -> int:
        return next(self._item_seq)

    def next_cart_id(self) -> int:
        return next(self._cart_seq)

    def get_item(self, item_id: int) -> Item | None:
        return self.items.get(item_id)

    def get_cart(self, cart_id: int) -> Cart | None:
        return self.carts.get(cart_id)

store = Store()
