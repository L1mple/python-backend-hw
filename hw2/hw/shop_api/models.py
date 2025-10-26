from dataclasses import dataclass
from typing import List, Optional

@dataclass(slots = True)
class CartItemInfo:
    name: str
    quantity: int
    available: bool
    
@dataclass(slots = True)
class CartItemEntity:
    id: int
    info: CartItemInfo

@dataclass(slots = True)
class CartInfo:
    items: List[CartItemEntity]
    price: float

@dataclass(slots = True)
class CartEntity:
    id: int
    info: CartInfo
    
@dataclass(slots = True)
class ItemInfo:
    name: str
    price: float
    deleted: bool

@dataclass(slots = True)
class ItemEntity:
    id: int
    info: ItemInfo

@dataclass(slots = True)
class Item:
    id: int
    name: str
    price: float
    deleted: bool = False

@dataclass(slots = True)
class ItemCreate:
    name: str
    price: float

@dataclass(slots = True)
class PatchItemInfo:
    name: Optional[str] = None
    price: Optional[float] = None

    