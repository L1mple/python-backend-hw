from dataclasses import dataclass, field


@dataclass(slots=True)
class ItemInfo:
    name: str
    price: float
    deleted: bool = False


@dataclass(slots=True)
class ItemEntity:
    id: int
    name: str
    price: float
    deleted: bool = False


@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: float | None = None


@dataclass(slots=True)
class CartItem:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartEntity:
    id: int
    items: list[CartItem] = field(default_factory=list)
    price: float = 0.0
