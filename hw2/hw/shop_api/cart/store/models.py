from dataclasses import dataclass


@dataclass(slots=True)
class CartItemInfo:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartInfo:
    items: list[CartItemInfo]
    price: float


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo
