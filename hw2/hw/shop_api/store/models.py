from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class ItemInfo:
    name : str
    price : float
    deleted : bool = False

@dataclass(slots=True)
class ItemEntity:
    id : int
    info : ItemInfo

@dataclass(slots=True)
class PatchItemInfo:
    name : str | None = None
    price : float | None = None

@dataclass(slots=True)
class CartItemInfo:
    id : int
    quantity : int
    name : str
    price : float
    available : bool

@dataclass(slots=True)
class CartInfo:
    items : List[CartItemInfo] = field(default_factory=list)
    price : float = 0.0
    quantity : int = 0

@dataclass(slots=True)
class CartEntity:
    id : int
    info : CartInfo
