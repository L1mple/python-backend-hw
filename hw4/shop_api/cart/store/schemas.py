from pydantic import BaseModel
from typing import List


class CartEntity(BaseModel):
    id: int
    price: float
    items: List["CartItemEntity"]


class CartItemEntity(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    class Config:
        from_attributes = True
