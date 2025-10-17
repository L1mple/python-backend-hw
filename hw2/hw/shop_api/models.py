from typing import List

from pydantic import BaseModel


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool
