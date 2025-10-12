from dataclasses import dataclass

@dataclass
class CardItem:
    id: int
    name: str
    quantity: int
    available: bool

@dataclass(slots=True)
class CartInfo:
    items: list[CardItem]
    price: float

@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo


