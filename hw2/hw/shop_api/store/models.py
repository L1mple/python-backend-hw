from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class ItemInfo:
    name: str
    price: float
    deleted: bool


@dataclass(slots=True)
class ItemEntity:
    id: int
    info: ItemInfo


@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: float | None = None


@dataclass(slots=True)
class ItemCartInfo:
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartInfo:
    items: Dict[int, ItemCartInfo]
    price: float


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo


@dataclass(slots=True)
class AddItemInfo:
    item_id: int
