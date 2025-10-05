from dataclasses import dataclass


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
class CartItem:
    id: int
    quantity: int
    available: bool
    name: str


@dataclass(slots=True)
class CartEntity:
    id: int
    items: list[CartItem]
    price: float


@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: float | None = None
    deleted: bool | None = None
