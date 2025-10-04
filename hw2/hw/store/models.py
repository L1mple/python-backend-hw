from dataclasses import dataclass
from typing import List



@dataclass(slots=True)
class Item:
    id: int
    name: str
    price: float
    deleted: bool


@dataclass(slots=True)
class CartItem:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class Cart:
    id: int
    items: List[CartItem]
    price: float = 0.0