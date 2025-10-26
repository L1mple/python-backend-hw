from pydantic import BaseModel
from typing import List

class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float

    class Config:
        orm_mode = True
