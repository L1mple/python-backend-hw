from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Item:
    id: int
    name: str
    price: float
    deleted: bool = False

@dataclass
class CartItem:
    id: int
    quantity: int = 1

@dataclass
class Cart:
    id: int
    items: list[CartItem] = field(default_factory=list)

    def total_price(self, items_store: dict[int, Item]) -> float:
        total = 0.0
        for cart_item in self.items:
            item = items_store.get(cart_item.id)
            if item is not None and not item.deleted:
                total += item.price * cart_item.quantity
        return float(total)
