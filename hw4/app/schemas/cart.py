from pydantic import BaseModel


class ItemCart(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: list[ItemCart] = []
    price: float = 0.0
