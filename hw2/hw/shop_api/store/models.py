from dataclasses import dataclass
from typing import Iterable, List


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
class CartItemInfo:
    id: int
    name: str
    quantity: int
    available: bool


# @dataclass(slots=True)
# class CartItemEntity:
#     id: int
#     info: CartItemInfo


@dataclass(slots=True)
class CartInfo:
    items: List[CartItemInfo]
    price: float


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo

