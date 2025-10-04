from dataclasses import (
    dataclass,
    field,
)


@dataclass(slots=True)
class CartItem:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class Cart:
    id: int
    price: float
    items: list[CartItem] = field(default_factory=list)


@dataclass(slots=True)
class Item:
    id: int
    name: str
    price: float
    deleted: bool


# “DB”
ITEMS: dict[int, Item] = {}
CARTS: dict[int, Cart] = {}
