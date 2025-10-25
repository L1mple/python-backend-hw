from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class Item:
    id : Optional[int] = None
    name : str = ""
    price : float = 0
    deleted : bool = False

@dataclass(slots=True)
class PatchItem:
    name : Optional[str] = None
    price : Optional[float] = None

@dataclass(slots=True)
class CartItem:
    id : int
    quantity : int
    name : str
    price : float
    available : bool

@dataclass(slots=True)
class Cart:
    id : Optional[int] = None
    items : List[CartItem] = field(default_factory=list)
    price : float = 0.0
    quantity : int = 0
