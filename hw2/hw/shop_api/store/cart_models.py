from dataclasses import dataclass
from typing import List

@dataclass(slots=True)
class CartItemInfo:
    id: int 
    name: str 
    quantity: int 
    available: bool

@dataclass(slots=True)
class CartInfo:
    items: List[CartItemInfo]
    price: float


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo


@dataclass(slots=True)
class PatchCartInfo:
    items: List[CartItemInfo] | None = None
    price: float | None = None 
