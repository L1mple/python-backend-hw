from dataclasses import dataclass, field
from typing import List

from pydantic import BaseModel


class CartLineOut(BaseModel):
    id: int
    quantity: int


class CartOut(BaseModel):
    id: int
    items: List[CartLineOut]
    quantity: int
    price: float


@dataclass
class CartRecord:
    id: int
    items: dict[int, int] = field(default_factory=dict)

    def add_item(self, item_id: int, qty: int = 1) -> None:
        self.items[item_id] = self.items.get(item_id, 0) + qty

    def remove_item(self, item_id: int, qty: int = 1) -> None:
        if item_id not in self.items:
            return
        self.items[item_id] -= qty
        if self.items[item_id] <= 0:
            del self.items[item_id]

    def clear(self) -> None:
        self.items.clear()
